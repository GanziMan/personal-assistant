"""화면 글자 인식.

macOS Vision 프레임워크로 로컬에서 처리한다. 스크린샷을 외부로
보내지 않는다 — 에러 화면에는 보통 경로, 호스트명, 토큰 조각이
같이 찍혀 있다 (ADR-034).

에러 메시지를 읽는 용도라면 이미지를 모델에 통째로 넘기는 것보다
OCR 이 정확하다. 고정폭 글꼴의 스택 트레이스는 텍스트로 뽑는 편이
낫다.
"""

from __future__ import annotations

import sys
from pathlib import Path

if sys.platform != "darwin":  # pragma: no cover - macOS 전용
    raise ImportError("Vision 은 macOS 에서만 씁니다")

# 한국어와 영어를 함께 인식한다. 순서가 우선순위다.
LANGUAGES = ["ko-KR", "en-US"]


class OCRUnavailable(RuntimeError):
    """Vision 프레임워크를 쓸 수 없다."""


def recognize(path: Path) -> list[str]:
    """이미지에서 줄 단위로 글자를 뽑는다."""
    try:
        import Quartz
        import Vision
        from Foundation import NSURL
    except ImportError as exc:  # pragma: no cover
        raise OCRUnavailable(
            "Vision 프레임워크를 불러올 수 없습니다. "
            "pyobjc-framework-Vision 이 설치되었는지 확인하세요."
        ) from exc

    url = NSURL.fileURLWithPath_(str(path))
    source = Quartz.CGImageSourceCreateWithURL(url, None)
    if source is None:
        raise OCRUnavailable(f"이미지를 열 수 없습니다: {path.name}")

    image = Quartz.CGImageSourceCreateImageAtIndex(source, 0, None)
    if image is None:
        raise OCRUnavailable(f"이미지를 읽을 수 없습니다: {path.name}")

    request = Vision.VNRecognizeTextRequest.alloc().init()
    request.setRecognitionLevel_(Vision.VNRequestTextRecognitionLevelAccurate)
    request.setRecognitionLanguages_(LANGUAGES)
    request.setUsesLanguageCorrection_(True)

    handler = Vision.VNImageRequestHandler.alloc().initWithCGImage_options_(image, None)
    ok, error = handler.performRequests_error_([request], None)
    if not ok:
        raise OCRUnavailable(f"글자 인식 실패: {error}")

    lines: list[str] = []
    for observation in request.results() or []:
        candidates = observation.topCandidates_(1)
        if candidates and len(candidates):
            text = str(candidates[0].string()).strip()
            if text:
                lines.append(text)
    return lines
