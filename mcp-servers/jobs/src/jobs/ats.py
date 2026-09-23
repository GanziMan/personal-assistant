"""회사 채용 시스템(ATS) 직접 조회.

Greenhouse·Lever·Ashby 는 회사별 채용공고를 인증 없이 공개 JSON 으로
제공한다. 회사가 스스로 공개하는 데이터라 승인도 키도 필요 없고,
공고가 빠짐없이 들어온다 — 중개 사이트를 거치지 않기 때문이다.

대신 회사를 먼저 알아야 한다. 시장 전체를 훑는 용도가 아니라
'관심 회사를 놓치지 않는' 용도다 (ADR-040).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from .model import Job

TIMEOUT = 15.0

# 회사 slug 하나로 세 곳을 찔러본다. 어디에 있는지는 해봐야 안다.
ENDPOINTS = {
    "greenhouse": "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs",
    "lever": "https://api.lever.co/v0/postings/{slug}?mode=json",
    "ashby": "https://api.ashbyhq.com/posting-api/job-board/{slug}",
}


@dataclass(slots=True)
class Company:
    slug: str
    ats: str
    label: str = ""

    @property
    def name(self) -> str:
        return self.label or self.slug


def _greenhouse(slug: str, payload: Any) -> list[Job]:
    jobs = payload.get("jobs") if isinstance(payload, dict) else None
    out = []
    for item in jobs or []:
        if not isinstance(item, dict) or not item.get("title"):
            continue
        out.append(
            Job(
                id=f"gh:{slug}:{item.get('id', '')}",
                url=str(item.get("absolute_url", "")),
                company=slug,
                title=str(item["title"]),
                location=str((item.get("location") or {}).get("name", "")),
            )
        )
    return out


def _lever(slug: str, payload: Any) -> list[Job]:
    out = []
    for item in payload if isinstance(payload, list) else []:
        if not isinstance(item, dict) or not item.get("text"):
            continue
        categories = item.get("categories") or {}
        out.append(
            Job(
                id=f"lv:{slug}:{item.get('id', '')}",
                url=str(item.get("hostedUrl", "")),
                company=slug,
                title=str(item["text"]),
                location=str(categories.get("location", "")),
                job_type=str(categories.get("commitment", "")),
            )
        )
    return out


def _ashby(slug: str, payload: Any) -> list[Job]:
    jobs = payload.get("jobs") if isinstance(payload, dict) else None
    out = []
    for item in jobs or []:
        if not isinstance(item, dict) or not item.get("title"):
            continue
        out.append(
            Job(
                id=f"ab:{slug}:{item.get('id', '')}",
                url=str(item.get("jobUrl", "")),
                company=slug,
                title=str(item["title"]),
                location=str(item.get("location", "")),
                job_type=str(item.get("employmentType", "")),
            )
        )
    return out


PARSERS = {"greenhouse": _greenhouse, "lever": _lever, "ashby": _ashby}


async def fetch(company: Company) -> list[Job]:
    """한 회사의 공고를 가져온다. 실패하면 빈 목록."""
    url = ENDPOINTS[company.ats].format(slug=company.slug)
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True) as client:
            response = await client.get(url)
            response.raise_for_status()
            payload = response.json()
    except (httpx.HTTPError, ValueError):
        return []

    jobs = PARSERS[company.ats](company.slug, payload)
    for job in jobs:
        job.company = company.name
    return jobs


async def detect(slug: str) -> list[str]:
    """이 slug 가 어느 ATS 에 있는지 찾는다.

    회사 이름만으로는 알 수 없어서 전부 찔러본다. 공고가 하나라도
    나오는 곳을 쓴다 — 페이지가 있어도 비어 있으면 잘못 찍은 것이다.
    """
    found: list[str] = []
    for ats in ENDPOINTS:
        if await fetch(Company(slug=slug, ats=ats)):
            found.append(ats)
    return found


def matches(job: Job, keywords: list[str]) -> bool:
    """키워드가 비면 전부 통과. 하나라도 걸리면 통과."""
    if not keywords:
        return True
    haystack = f"{job.title} {job.location}".lower()
    return any(k.lower() in haystack for k in keywords)
