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
| Claude Code CLI | 구독(Pro/Max)으로 추론 — API 키 불필요 |

## 현재 상태

| 단계 | 내용 | 상태 |
|---|---|---|
| P0 | 뼈대·설계 문서 | 완료 |
| P1 | 코어 데몬·소켓·CLI | 완료 |
| P2 | MCP 도구층 (캘린더·시스템·파일·피드·개발·기억·문서검색·채용) | 완료 |
| P3 | 장기 기억 3계층 | 완료 |
| P4 | 스케줄러·선제 브리핑 | 완료 |
| P5 | SwiftUI 메뉴바 앱 | 완료 |
| P6 | 로컬 임베딩 문서 검색 | 완료 |
| P7 | 온보딩·백업·감사 뷰어 | 예정 |

테스트 276건. 로드맵 상세는 ARCHITECTURE.md §9.

## 설치

새 맥이라면 한 줄이면 된다.

```
git clone https://github.com/GanziMan/personal-assistant.git
cd personal-assistant && ./scripts/bootstrap.sh
```

Homebrew 의존성, Swift 툴체인, Claude Code 로그인, Ollama 모델, 데몬,
메뉴바 앱까지 확인하고 설치한다. 이미 있는 것은 건너뛴다.

수동으로 하려면:

```
brew install uv ollama node
npm install -g @anthropic-ai/claude-code
claude login
./scripts/install.sh
```

추론은 Claude Code 로그인(Pro/Max 구독)에서 사용량이 빠진다. 별도 API
과금이 없다 (ADR-007). API 키로 쓰려면 `~/.assistant/config.toml` 에
`[models] backend = "api"` 를 넣는다.

런타임(가상환경·기억 DB·로그)은 레포가 아니라 `~/.assistant` 에 만들어진다.
macOS TCC 가 `~/Documents` 를 보호해서 launchd 데몬이 그 안을 읽지 못하기
때문이다 (ADR-006). 코드를 고친 뒤에는 `install.sh` 를 다시 실행한다.

```
~/.assistant/venv/bin/assistant "오늘 일정 뭐야"
```

## 채용공고 (선택)

사람인 공식 API 로만 가져온다. 크롤링하지 않는다 (ADR-039).

1. [사람인 API 이용신청](https://oapi.saramin.co.kr/join) 에서 access-key 발급
2. 키체인에 저장

```
security add-generic-password -a "$USER" -s assistant-saramin -w
```

3. 검색 조건 등록 — 비서에게 말로 하면 된다

```
백엔드 서울 조건으로 채용 검색 등록해줘
```

평일 오전 9시·저녁 7시에 새 공고만 확인해 쪽지로 알린다. 이미 본
공고는 다시 보여주지 않는다.

## 코드를 고친 뒤

editable 설치가 아니므로 다시 깔아야 반영된다.

```
git pull
./scripts/install.sh      # 데몬
./scripts/build-app.sh    # 메뉴바 앱
```

앱만 고쳤으면 `build-app.sh` 만, 데몬만 고쳤으면 `install.sh` 만 돌리면
된다. 뭔가 이상하면 진단부터:

```
./scripts/doctor.sh
```

데몬·구독 백엔드·MCP 서버·Ollama·앱·폴더 권한과 이번 기동의 오류를
한 번에 보여준다.

## 여러 맥에서 쓰기

맥마다 독립적으로 설치한다. 새 맥에서 위 설치 과정을 그대로 반복하면
그 맥의 캘린더·파일·레포를 보는 비서가 따로 생긴다. Claude 구독이
같은 계정이면 `claude login` 한 번이면 된다.

기억과 문서 색인은 옮기지 않는다. 그 맥의 레포·파일 경로에 묶여 있고,
SQLite 를 파일 동기화로 나르면 WAL 때문에 깨진다 (ADR-033).

설정과 구독 피드만 옮긴다.

```
# 기존 맥에서
./scripts/profile.sh export ~/Desktop/assistant-profile.json

# 새 맥에서 (bootstrap.sh 를 먼저 실행한 뒤)
./scripts/profile.sh import ~/Desktop/assistant-profile.json
```

## 메뉴바 앱

```
./scripts/build-app.sh
```

화면 오른쪽에 세워두는 반투명 플로팅 패널. 말을 걸지 않을 때는 다음 일정
카운트다운·남은 할 일·아침 브리핑을 보여준다 (이 화면은 모델을 부르지
않는다, ADR-017).

SwiftPM 으로 빌드해 `~/Applications/Assistant.app` 을 만들고 로그인 시
자동 실행으로 등록한다. Xcode 프로젝트는 두지 않는다 — Command Line
Tools 만 있어도 빌드된다 (`xcrun swift` 로 부른다).

| 단축키 | 동작 |
|---|---|
| ⌥Space | 패널 열기/숨기기 |
| Esc | 숨기기 |
| ⌘J | 접기/펼치기 (다음 일정 한 줄만) |
| ⌘K | 대화 비우기 |
| ↑ / ↓ | 이전에 보낸 질문 되짚기 |
| ⌘V | 스크린샷 붙여넣기 (이미지면 OCR, 아니면 일반 붙여넣기) |

파일을 패널에 끌어다 놓으면 경로가 입력창에 들어간다. 이미지는 로컬
OCR 로 글자를 뽑는다 (ADR-034). 답변에 파일 경로가 나오면 눌러서
Finder 에서 열 수 있다.

번들 5MB 미만, 상주 메모리 30MB 수준. Swift 런타임은 macOS 에 내장돼
있어 앱에 딸려오지 않는다.
