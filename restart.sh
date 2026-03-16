#!/usr/bin/env bash
set -euo pipefail

echo "[FinFlow] 서버 재시작을 시작합니다."

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

# stop.sh 실행
echo "1단계: 기존 서버 종료"
if [ -f "$PROJECT_ROOT/stop.sh" ]; then
  bash "$PROJECT_ROOT/stop.sh"
else
  echo "경고: stop.sh를 찾을 수 없습니다."
fi

echo
echo "2단계: 잠시 대기 중... (프로세스 완전 종료 대기)"
sleep 2

echo
echo "3단계: 서버 재시작"
if [ -f "$PROJECT_ROOT/start.sh" ]; then
  bash "$PROJECT_ROOT/start.sh"
else
  echo "오류: start.sh를 찾을 수 없습니다."
  exit 1
fi

echo
echo "[FinFlow] 재시작이 완료되었습니다."
exit 0
