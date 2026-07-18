# discord-codyssey-coach

디스코드 채널 안에서 Codyssey `AI/SW 기초` 과정을 관리하는 MVP 봇입니다.

## 기능

- `/내상태`: 현재 주차, 진행률, 남은 필수 미션, 위험도 확인
- `/미션현황`: 전체 미션의 완료(✅)/진행중(🔶)/미시작(⬜) 상태를 한눈에 확인
- `/레벨설정`: 현재 레벨 기록
- `/평가결과`: 미션 평가 결과 기록 (미완료 미션만 현재 Pass 횟수와 함께 자동완성으로 표시)
  - `pass`: Pass 카운트 +1 (한 번에 1~3회 기록 가능)
  - `3/3 pass`: 미션 완료
  - `fail`: Pass 카운트 0으로 초기화
  - 기록 후 전체 진행률 요약 표시
- `/기록수정`: 잘못 기록한 미션의 Pass 카운트를 직접 수정 (3이면 완료 처리, 0이면 초기화)
- `/청소`: 채널에 쌓인 봇 메시지를 한 번에 삭제 (봇에게 '메시지 관리' 권한 필요, 14일 이내 메시지만)

모든 명령의 응답은 기본적으로 **요청한 사람에게만 보입니다.** 채널에 공유하고 싶으면 명령 입력 시 `공개: True` 옵션을 선택하세요.
- `/주간보고`: 주간 완료 내용, 학습 시간, 막힌 점 저장
- `/다음주계획`: 다음 주 우선순위 추천
- `/위험도`: 기초 단계 종료일 기준 일정 위험도 확인

## 실행 준비

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

`.env` 또는 환경 변수에 `DISCORD_TOKEN`을 넣어주세요.

빠른 명령어 등록을 원하면 `DISCORD_GUILD_ID`에 서버 ID를 넣으면 됩니다.

## 디스코드 채널에 추가

1. Discord Developer Portal에서 새 Application을 만듭니다.
2. Bot 메뉴에서 Bot을 만들고 Token을 복사합니다.
3. `.env` 파일의 `DISCORD_TOKEN`에 복사한 토큰을 넣습니다.
4. OAuth2 URL Generator에서 `bot`, `applications.commands` scope를 선택합니다.
5. Bot Permissions에서 `Send Messages`, `Use Slash Commands`, `Read Message History`, `Manage Messages`(/청소 기능용)를 선택합니다.
6. 생성된 URL로 접속해서 원하는 서버에 봇을 초대합니다.
7. 빠른 슬래시 명령어 등록을 위해 서버 ID를 `.env`의 `DISCORD_GUILD_ID`에 넣습니다.
   - 여러 서버에서 쓰려면 쉼표로 구분해 넣으세요 (예: `DISCORD_GUILD_ID=123,456`)
   - 비워두면 전역 등록되어 모든 서버에서 쓸 수 있지만, 처음 반영에 최대 1시간 걸립니다.

## 실행

```bash
export PYTHONPATH=src
python3 -m codyssey_coach.bot
```

## 테스트

```bash
PYTHONPATH=src python3 -m pytest
```

## 24시간 클라우드 배포 (로컬 실행 불필요)

로컬 PC를 켜두지 않아도 봇이 돌아가도록 Render(무료) + Turso(무료 DB) 조합으로 배포합니다.

### 1. Turso DB 만들기 (데이터 유지용)

무료 인스턴스는 재배포하면 디스크가 초기화되므로, 진행 데이터를 Turso 클라우드 DB에 동기화합니다.

1. https://turso.tech 에서 가입 후 데이터베이스를 하나 만듭니다.
2. 데이터베이스 URL(`libsql://...`)과 auth token을 복사해 둡니다.

### 2. Render에 배포

1. https://render.com 에서 GitHub 계정으로 가입합니다.
2. New → Web Service → 이 저장소 선택 → Language는 **Docker**를 선택합니다.
3. Instance Type은 **Free**를 선택합니다.
4. Environment Variables에 아래를 추가합니다.
   - `DISCORD_TOKEN`: 디스코드 봇 토큰
   - `DISCORD_GUILD_ID`: 서버 ID (선택)
   - `TURSO_DATABASE_URL`: 1번에서 복사한 URL
   - `TURSO_AUTH_TOKEN`: 1번에서 복사한 토큰
5. Deploy 후 로그에 `Codyssey coach bot is ready`가 뜨면 성공. `https://앱이름.onrender.com` 공개 URL이 생깁니다.
   - 현재 배포 주소: https://discord-codyssey-coach.onrender.com
6. 환경 변수에 `KEEP_ALIVE_URL=https://앱이름.onrender.com/health`를 추가하고 저장하면 자동 재배포됩니다.
   - Render 무료 인스턴스는 15분 동안 외부 요청이 없으면 잠들기 때문에, 봇이 10분마다 스스로 핑을 보내 항상 깨어 있게 합니다.

이후에는 GitHub에 푸시할 때마다 Render가 자동으로 다시 배포합니다.

### 3. 배포 확인

1. 브라우저에서 `https://앱이름.onrender.com/health` 접속 → `ok`가 표시되면 헬스 서버 정상
2. 디스코드에서 `/내상태` 입력 → 응답이 오면 봇 정상
3. 로컬 PC를 꺼둔 상태에서도 명령어가 동작하면 24시간 가동 확인 완료

### 자주 발생하는 문제

- **`Deploy failed ... while building your code`**: 최신 커밋(Dockerfile 포함)이 GitHub에 푸시됐는지 `git status`로 확인하세요. pre-push 검사에 막혀 푸시가 안 된 경우가 많습니다.
- **`JWT error: InvalidToken`**: `TURSO_AUTH_TOKEN`이 잘못된 경우입니다. Turso 계정용 API Token이 아니라 **해당 DB의 Database Token**(Create Database Token 버튼, `eyJ`로 시작)을 써야 하고, `TURSO_DATABASE_URL`과 같은 DB의 것이어야 합니다. 붙여넣을 때 앞뒤 공백·따옴표가 없어야 합니다.
- **pre-push 훅에서 `pytest가 설치되어 있지 않습니다`**: `.venv/bin/pip install pytest` 실행 후 다시 푸시하세요.

## 푸시 전 자동 검증 (pre-push 훅)

토큰 유출·문법 오류·테스트 실패 상태로 푸시되는 것을 막습니다. 최초 1회만 설치하세요.

```bash
bash scripts/install-hooks.sh
```

설치 후에는 `git push` 할 때마다 자동으로 다음을 검사하고, 하나라도 실패하면 푸시가 취소됩니다.

1. 시크릿 검사: `.env`가 커밋됐는지, 디스코드 토큰 패턴이 커밋에 들어있는지
2. 문법 검사: `src/` 전체 파이썬 컴파일
3. 테스트: `pytest` 전체 실행

훅 없이 수동으로 검사만 하려면 `bash scripts/check.sh`를 실행하면 됩니다.

## 기준 규칙

- 과정 기간: `2026-05-07`부터 `2026-10-31`까지 총 26주
- 필수 미션: 초록색 미션
- 선택 미션: 금색 미션
- 미션 통과: 동료 평가 3회 Pass
- Fail 발생: Pass 카운트 초기화
- Level 5 이후 시험 응시 가능
- 시험 통과 후 B7-1, B7-2 추천 가능
