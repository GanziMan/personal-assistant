"""검색 조건과 저장 위치.

조건을 코드에 박지 않는다. 직무와 지역은 사람마다 다르고, 바꿀
때마다 재설치하게 만들 이유가 없다.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path

HOME = Path(os.environ.get("ASSISTANT_HOME", Path.home() / ".assistant"))
CONFIG_PATH = HOME / "jobs.json"


@dataclass(slots=True)
class Search:
    """저장해둔 검색 하나."""

    name: str
    keywords: str = ""
    loc_mcd: str = ""        # 지역 대분류 (서울=101)
    job_mid_cd: str = ""     # 직무 대분류 (IT개발·데이터=2)
    experience_min: int = 0  # 이 경력 이하만 요구하는 공고
    exclude_agency: bool = True   # 헤드헌팅·파견 제외

    def to_params(self) -> dict[str, str]:
        params: dict[str, str] = {"sort": "pd", "count": "50"}
        if self.keywords:
            params["keywords"] = self.keywords
        if self.loc_mcd:
            params["loc_mcd"] = self.loc_mcd
        if self.job_mid_cd:
            params["job_mid_cd"] = self.job_mid_cd
        if self.exclude_agency:
            params["sr"] = "directhire"
        params["fields"] = "posting-date,expiration-date"
        return params


@dataclass(slots=True)
class CompanyEntry:
    """관심 회사 하나. ATS 직접 조회 대상."""

    slug: str
    ats: str
    label: str = ""
    keywords: list[str] = field(default_factory=list)


@dataclass(slots=True)
class JobsConfig:
    searches: list[Search] = field(default_factory=list)
    companies: list[CompanyEntry] = field(default_factory=list)

    @classmethod
    def load(cls, path: Path | None = None) -> JobsConfig:
        path = path or CONFIG_PATH
        if not path.exists():
            return cls()
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return cls()
        return cls(
            searches=[
                Search(**s) for s in raw.get("searches", []) if isinstance(s, dict)
            ],
            companies=[
                CompanyEntry(**c) for c in raw.get("companies", []) if isinstance(c, dict)
            ],
        )

    def save(self, path: Path | None = None) -> None:
        path = path or CONFIG_PATH
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "searches": [asdict(s) for s in self.searches],
                    "companies": [asdict(c) for c in self.companies],
                },
                ensure_ascii=False, indent=2,
            ),
            encoding="utf-8",
        )

    def find(self, name: str) -> Search | None:
        return next((s for s in self.searches if s.name == name), None)

    def find_company(self, slug: str) -> CompanyEntry | None:
        key = slug.strip().lower()
        return next(
            (c for c in self.companies if c.slug.lower() == key or c.label.lower() == key),
            None,
        )
