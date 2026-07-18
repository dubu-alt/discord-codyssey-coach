#!/usr/bin/env bash
# 최초 1회 실행: pre-push 훅을 설치합니다.
set -e
cd "$(git rev-parse --show-toplevel)"
chmod +x scripts/check.sh scripts/githooks/pre-push
git config core.hooksPath scripts/githooks
echo "✅ pre-push 훅 설치 완료. 이제 git push 때마다 자동으로 검증합니다."
