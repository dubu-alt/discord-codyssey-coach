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

## 기준 규칙

- 과정 기간: `2026-05-07`부터 `2026-10-31`까지 총 26주
- 필수 미션: 초록색 미션
- 선택 미션: 금색 미션
- 미션 통과: 동료 평가 3회 Pass
- Fail 발생: Pass 카운트 초기화
- Level 5 이후 시험 응시 가능
- 시험 통과 후 B7-1, B7-2 추천 가능
