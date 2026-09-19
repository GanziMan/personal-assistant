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

| 단계 | 내용 | 상태 |
|---|---|---|
| P0 | 뼈대·설계 문서 | 완료 |
| P1 | 코어 데몬·소켓·CLI | 완료 |
| P2 | MCP 도구층 (캘린더·시스템) | 완료 |
| P3 | 장기 기억 3계층 | 완료 |
| P4 | 스케줄러·선제 브리핑 | 완료 |
| P5 | SwiftUI 메뉴바 앱 | 예정 |
| P6 | 로컬 모델 라우팅 실측 | 예정 |
| P7 | 온보딩·백업·감사 뷰어 | 예정 |

테스트 76건. 로드맵 상세는 ARCHITECTURE.md §9.

## 설치

```
brew install uv ollama
./scripts/install.sh
```

런타임(가상환경·기억 DB·로그)은 레포가 아니라 `~/.assistant` 에 만들어진다.
macOS TCC 가 `~/Documents` 를 보호해서 launchd 데몬이 그 안을 읽지 못하기
때문이다 (ADR-006). 코드를 고친 뒤에는 `install.sh` 를 다시 실행한다.

```
~/.assistant/venv/bin/assistant "오늘 일정 뭐야"
```
