# discord-codyssey-coach

디스코드 채널 안에서 Codyssey `AI/SW 기초` 과정을 관리하는 MVP 봇입니다.

## 기능

- `/내상태`: 현재 주차, 진행률, 남은 필수 미션, 위험도 확인
- `/레벨설정`: 현재 레벨 기록
- `/평가결과`: 미션 평가 결과 기록
  - `pass`: Pass 카운트 +1
  - `3/3 pass`: 미션 완료
  - `fail`: Pass 카운트 0으로 초기화
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
5. Bot Permissions에서 `Send Messages`, `Use Slash Commands`, `Read Message History`를 선택합니다.
6. 생성된 URL로 접속해서 원하는 서버에 봇을 초대합니다.
7. 빠른 슬래시 명령어 등록을 위해 서버 ID를 `.env`의 `DISCORD_GUILD_ID`에 넣습니다.

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

로컬 PC를 켜두지 않아도 봇이 돌아가도록 Koyeb(무료) + Turso(무료 DB) 조합으로 배포합니다.

### 1. Turso DB 만들기 (데이터 유지용)

무료 인스턴스는 재배포하면 디스크가 초기화되므로, 진행 데이터를 Turso 클라우드 DB에 동기화합니다.

1. https://turso.tech 에서 가입 후 데이터베이스를 하나 만듭니다.
2. 데이터베이스 URL(`libsql://...`)과 auth token을 복사해 둡니다.

### 2. Koyeb에 배포

1. https://koyeb.com 에서 GitHub 계정으로 가입합니다.
2. Create Service → GitHub → 이 저장소 선택 → Builder는 `Dockerfile`을 선택합니다.
3. Instance는 **Free**를 선택합니다.
4. Environment variables에 아래를 추가합니다.
   - `DISCORD_TOKEN`: 디스코드 봇 토큰
   - `DISCORD_GUILD_ID`: 서버 ID (선택)
   - `TURSO_DATABASE_URL`: 1번에서 복사한 URL
   - `TURSO_AUTH_TOKEN`: 1번에서 복사한 토큰
5. 배포가 끝나면 `https://앱이름-계정.koyeb.app` 공개 URL이 생깁니다.
6. 환경 변수에 `KEEP_ALIVE_URL=https://앱이름-계정.koyeb.app/health`를 추가하고 재배포합니다.
   - Koyeb 무료 인스턴스는 1시간 동안 외부 요청이 없으면 잠들기 때문에, 봇이 10분마다 스스로 핑을 보내 항상 깨어 있게 합니다.

이후에는 GitHub에 푸시할 때마다 Koyeb가 자동으로 다시 배포합니다.

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
