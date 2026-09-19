#!/usr/bin/env bash
# 맥 사이에 설정만 옮긴다.
#
#   ./scripts/profile.sh export ~/Desktop/assistant-profile.json
#   ./scripts/profile.sh import ~/Desktop/assistant-profile.json
#
# 옮기는 것: config.toml, 구독 피드
# 옮기지 않는 것: 기억 DB, 문서 색인, 감지 기록, 로그, 대화
#
# 기억과 색인은 그 맥의 레포·파일에 대한 것이라 다른 맥으로 옮기면
# 존재하지 않는 경로를 가리키게 된다. SQLite 를 파일 동기화로 나르면
# WAL 때문에 깨지기도 한다 (ADR-033).
set -euo pipefail

HOME_DIR="${ASSISTANT_HOME:-$HOME/.assistant}"
VENV_PY="$HOME_DIR/venv/bin/python"

die() { printf '\033[31m✗\033[0m %s\n' "$1" >&2; exit 1; }
[[ -x "$VENV_PY" ]] || die "비서가 설치되지 않았습니다. ./scripts/install.sh 를 먼저 실행하세요."

action="${1:-}"
target="${2:-}"
[[ -n "$action" && -n "$target" ]] || die "사용법: $0 export|import <파일>"

case "$action" in
  export)
    "$VENV_PY" - "$HOME_DIR" "$target" <<'PY'
import json, pathlib, sys

home, out = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
payload = {"version": 1}

config = home / "config.toml"
payload["config_toml"] = config.read_text(encoding="utf-8") if config.exists() else ""

feeds = home / "feeds.json"
payload["feeds"] = json.loads(feeds.read_text(encoding="utf-8")) if feeds.exists() else []

out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"내보냈습니다: {out}")
print(f"  설정 {'있음' if payload['config_toml'] else '없음(기본값)'}, 피드 {len(payload['feeds'])}개")
PY
    ;;

  import)
    [[ -f "$target" ]] || die "파일이 없습니다: $target"
    "$VENV_PY" - "$HOME_DIR" "$target" <<'PY'
import json, pathlib, shutil, sys, time

home, src = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
payload = json.loads(src.read_text(encoding="utf-8"))
home.mkdir(mode=0o700, parents=True, exist_ok=True)

def backup(path: pathlib.Path) -> None:
    """덮어쓰기 전에 남긴다. 되돌릴 수 없는 가져오기는 만들지 않는다."""
    if path.exists():
        shutil.copy2(path, path.with_suffix(path.suffix + f".bak.{int(time.time())}"))

if text := payload.get("config_toml"):
    target = home / "config.toml"
    backup(target)
    target.write_text(text, encoding="utf-8")
    print("설정을 가져왔습니다.")

feeds = payload.get("feeds") or []
if feeds:
    target = home / "feeds.json"
    backup(target)
    existing = json.loads(target.read_text(encoding="utf-8")) if target.exists() else []
    seen = {f.get("url") for f in existing}
    merged = existing + [f for f in feeds if f.get("url") not in seen]
    target.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"피드 {len(merged) - len(existing)}개를 추가했습니다 (전체 {len(merged)}개).")

print("\n데몬을 재시작하세요:")
print("  launchctl kickstart -k gui/$UID/com.assistant.daemon")
PY
    ;;

  *) die "사용법: $0 export|import <파일>" ;;
esac
