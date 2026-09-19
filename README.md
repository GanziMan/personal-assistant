# personal-assistant

macOS 상주형 개인 비서 AI.

메뉴바에 상주하면서 일정·파일·개발·리서치를 다루고, 장기 기억을 쌓고,
아침에 먼저 브리핑을 건네는 것을 목표로 한다.

- 설계: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- 결정 기록: [docs/DECISIONS.md](docs/DECISIONS.md)

## 구성

```
core/         에이전트 데몬 (Python) — 비서의 두뇌
mcp-servers/  macOS 각 영역에 손을 뻗는 MCP 어댑터
app/          SwiftUI 메뉴바 앱 — 상시 UI
scripts/      설치·기동·백업 스크립트
data/         SQLite 기억 저장소 (git 제외)
docs/         설계 문서
```

## 개발 환경 전제

| 도구 | 용도 |
|---|---|
| Python 3.12+ / uv | 코어 데몬 |
| Xcode 15+ | SwiftUI 메뉴바 앱 빌드 |
| Ollama | 로컬 임베딩·분류 모델 |
| Claude API 키 | 클라우드 추론 (키체인 보관) |

## 현재 상태

P0 — 뼈대와 설계 확정. 로드맵은 ARCHITECTURE.md §9 참조.
