"""시스템 MCP 서버."""

from __future__ import annotations

import subprocess
import sys

from mcp.server.mcpserver import MCPServer

from pathlib import Path

from .clipboard import ClipboardHistory, is_concealed, looks_secret
from .images import PASTED_DIR, is_image, prune
from .notify import send as send_notification

mcp = MCPServer("macos-system")

# 이력은 이 프로세스 메모리에만 산다. 디스크에 남기지 않는다.
_history = ClipboardHistory()


def _pbpaste() -> str:
    r = subprocess.run(["pbpaste"], capture_output=True, text=True, timeout=5, check=False)
    return r.stdout or ""


def _capture_current() -> None:
    """읽을 때마다 이력에 담는다. 별도 감시 프로세스를 두지 않는다."""
    if is_concealed():
        return
    _history.capture(_pbpaste())


@mcp.tool()
def send_alert(title: str, message: str, subtitle: str = "", sound: bool = False) -> str:
    """사용자에게 알림을 띄운다. 정말 지금 봐야 하는 것만."""
    return send_notification(title, message, subtitle=subtitle, sound=sound)


@mcp.tool()
def read_clipboard() -> str:
    """클립보드의 텍스트를 읽는다. 방금 복사한 것을 물을 때 쓴다."""
    if is_concealed():
        return "(비밀번호 관리자가 표시한 항목이라 읽지 않습니다)"

    text = _pbpaste()
    if not text.strip():
        return "(클립보드가 비어 있습니다)"
    if looks_secret(text):
        return "(비밀처럼 보이는 내용이라 읽지 않습니다)"

    _history.capture(text)
    return text


@mcp.tool()
def recent_clips(limit: int = 5) -> str:
    """최근 복사한 것들. 데몬이 사는 동안만 남는다."""
    _capture_current()
    clips = _history.recent(limit)
    if not clips:
        return "기록된 복사 내용이 없습니다."
    return "\n".join(c.describe() for c in clips)


@mcp.tool()
def search_clips(query: str, limit: int = 5) -> str:
    """복사했던 것 중에서 찾는다. \"아까 복사한 그 에러\" 같은 질문용."""
    _capture_current()
    clips = _history.find(query, limit)
    if not clips:
        return f"'{query}' 가 들어간 복사 기록이 없습니다."
    return "\n\n".join(f"{c.describe()}\n{c.text[:600]}" for c in clips)


@mcp.tool()
def forget_clips() -> str:
    """복사 이력을 지운다."""
    count = len(_history)
    _history.clear()
    return f"복사 기록 {count}건을 지웠습니다."


@mcp.tool()
def write_clipboard(text: str) -> str:
    """클립보드에 텍스트를 넣는다. 기존 내용은 사라진다."""
    subprocess.run(["pbcopy"], input=text, text=True, timeout=5, check=False)
    return f"클립보드에 {len(text)}자를 넣었습니다."


@mcp.tool()
def open_app(name: str) -> str:
    """앱을 연다."""
    r = subprocess.run(["open", "-a", name], capture_output=True, text=True, timeout=10, check=False)
    if r.returncode != 0:
        return f"'{name}' 을 열 수 없습니다: {r.stderr.strip()}"
    return f"{name} 을 열었습니다."


@mcp.tool()
def list_shortcuts() -> str:
    """사용자가 만들어 둔 단축어 목록."""
    r = subprocess.run(
        ["shortcuts", "list"], capture_output=True, text=True, timeout=15, check=False
    )
    if r.returncode != 0:
        return "단축어 목록을 읽을 수 없습니다."
    names = [n for n in r.stdout.splitlines() if n.strip()]
    return "\n".join(names) if names else "등록된 단축어가 없습니다."


@mcp.tool()
def send_shortcut(name: str, input_text: str = "") -> str:
    """단축어를 실행한다. 사용자가 만든 자동화에 비서가 올라타는 통로다."""
    cmd = ["shortcuts", "run", name]
    r = subprocess.run(
        cmd, input=input_text or None, capture_output=True, text=True, timeout=60, check=False
    )
    if r.returncode != 0:
        return f"단축어 '{name}' 실행 실패: {r.stderr.strip()}"
    return r.stdout.strip() or f"'{name}' 을 실행했습니다."


def _readable(raw: str) -> Path | str:
    """OCR 로 읽어도 되는 경로인가.

    파일 서버와 같은 허용 폴더, 또는 비서가 만든 붙여넣기 폴더만
    허용한다. 임의 경로의 이미지를 읽어주는 도구가 되면 파일 서버에
    세운 경계가 무의미해진다.
    """
    from macos_files.paths import Boundary, PathDenied, from_env

    path = Path(raw).expanduser().resolve(strict=False)

    if PASTED_DIR.resolve() in path.parents:
        return path
    try:
        return from_env().resolve(str(path))
    except PathDenied as exc:
        return f"거부됨: {exc}"
    except Exception:  # noqa: BLE001
        return Boundary().describe()


@mcp.tool()
def read_image_text(path: str) -> str:
    """이미지에서 글자를 읽는다 (로컬 OCR).

    스크린샷 속 에러 메시지나 문서 사진을 텍스트로 뽑을 때 쓴다.
    이미지는 맥을 벗어나지 않는다.
    """
    target = _readable(path)
    if isinstance(target, str):
        return target
    if not target.is_file():
        return f"파일이 없습니다: {path}"
    if not is_image(target):
        return f"이미지가 아닙니다: {target.suffix or '(확장자 없음)'}"

    try:
        from .ocr import OCRUnavailable, recognize
    except ImportError as exc:
        return f"글자 인식을 쓸 수 없습니다: {exc}"

    try:
        lines = recognize(target)
    except Exception as exc:  # OCRUnavailable 포함
        return f"글자 인식 실패: {exc}"

    if not lines:
        return "이미지에서 글자를 찾지 못했습니다."
    return "\n".join(lines)


@mcp.tool()
def clean_pasted_images() -> str:
    """붙여넣기 폴더의 오래된 이미지를 정리한다."""
    removed = prune()
    return f"오래된 이미지 {removed}개를 지웠습니다." if removed else "정리할 이미지가 없습니다."


def main() -> int:
    if sys.platform != "darwin":
        print("이 서버는 macOS 전용입니다.", file=sys.stderr)
        return 1
    mcp.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
