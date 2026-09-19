"""시스템 MCP 서버."""

from __future__ import annotations

import subprocess
import sys

from mcp.server.fastmcp import FastMCP

from .notify import send as send_notification

mcp = FastMCP("macos-system")


@mcp.tool()
def send_alert(title: str, message: str, subtitle: str = "", sound: bool = False) -> str:
    """사용자에게 알림을 띄운다. 정말 지금 봐야 하는 것만."""
    return send_notification(title, message, subtitle=subtitle, sound=sound)


@mcp.tool()
def read_clipboard() -> str:
    """클립보드의 텍스트를 읽는다."""
    r = subprocess.run(["pbpaste"], capture_output=True, text=True, timeout=5, check=False)
    return r.stdout or "(클립보드가 비어 있습니다)"


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


def main() -> int:
    if sys.platform != "darwin":
        print("이 서버는 macOS 전용입니다.", file=sys.stderr)
        return 1
    mcp.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
