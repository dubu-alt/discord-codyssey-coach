#!/usr/bin/env bash
# 푸시 전 검증 스크립트. 직접 실행하거나 pre-push 훅이 자동 실행합니다.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

if [ -f .venv/bin/activate ]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

fail() {
  echo ""
  echo "❌ $1"
  echo "푸시가 중단되었습니다. 문제를 고친 뒤 다시 푸시하세요."
  exit 1
}

echo "== 1/3 시크릿 검사 =="
if git ls-files --error-unmatch .env >/dev/null 2>&1; then
  fail ".env 파일이 git에 추적되고 있습니다. 'git rm --cached .env' 실행 후 커밋하세요."
fi
TOKEN_PATTERN='[A-Za-z0-9_-]{23,28}\.[A-Za-z0-9_-]{6,7}\.[A-Za-z0-9_-]{27,}'
if git grep -InE "$TOKEN_PATTERN" HEAD -- ':!*.sqlite3' >/dev/null 2>&1; then
  git grep -InE "$TOKEN_PATTERN" HEAD -- ':!*.sqlite3' || true
  fail "디스코드 토큰으로 보이는 문자열이 커밋에 포함되어 있습니다. 해당 커밋을 수정하고 토큰을 재발급하세요."
fi
echo "통과"

echo "== 2/3 문법 검사 =="
python3 -m compileall -q src || fail "파이썬 문법 오류가 있습니다."
echo "통과"

echo "== 3/3 테스트 =="
python3 -m pytest --version >/dev/null 2>&1 || fail "pytest가 설치되어 있지 않습니다. 'pip install pytest' 후 다시 시도하세요."
PYTHONPATH=src python3 -m pytest -q || fail "테스트가 실패했습니다."
echo "통과"

echo ""
echo "✅ 모든 검사 통과 — 푸시를 진행합니다."
