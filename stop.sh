#!/usr/bin/env bash
set -euo pipefail

echo "[FinFlow] 서버 종료를 시작합니다."

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

BACKEND_PID_FILE="$PROJECT_ROOT/logs/backend.pid"
FRONTEND_PID_FILE="$PROJECT_ROOT/logs/frontend.pid"

echo
echo "1) Frontend 서버 종료"
if [ -f "$FRONTEND_PID_FILE" ]; then
  FRONTEND_PID="$(cat "$FRONTEND_PID_FILE" 2>/dev/null || echo "")"
  if [ -n "$FRONTEND_PID" ] && kill -0 "$FRONTEND_PID" >/dev/null 2>&1; then
    echo " - frontend 프로세스 종료 중... (PID: $FRONTEND_PID)"
    kill "$FRONTEND_PID" 2>/dev/null || true
    sleep 1
    if kill -0 "$FRONTEND_PID" >/dev/null 2>&1; then
      echo " - 강제 종료 중... (PID: $FRONTEND_PID)"
      kill -9 "$FRONTEND_PID" 2>/dev/null || true
    fi
    rm -f "$FRONTEND_PID_FILE"
    echo " - frontend 종료 완료"
  else
    echo " - frontend 프로세스가 실행 중이 아닙니다."
    rm -f "$FRONTEND_PID_FILE"
  fi
else
  echo " - frontend PID 파일을 찾을 수 없습니다. (이미 종료되었거나 실행되지 않았습니다)"
fi

echo
echo "2) Backend 서버 종료"
if [ -f "$BACKEND_PID_FILE" ]; then
  BACKEND_PID="$(cat "$BACKEND_PID_FILE" 2>/dev/null || echo "")"
  if [ -n "$BACKEND_PID" ] && kill -0 "$BACKEND_PID" >/dev/null 2>&1; then
    echo " - backend 프로세스 종료 중... (PID: $BACKEND_PID)"
    kill "$BACKEND_PID" 2>/dev/null || true
    sleep 1
    if kill -0 "$BACKEND_PID" >/dev/null 2>&1; then
      echo " - 강제 종료 중... (PID: $BACKEND_PID)"
      kill -9 "$BACKEND_PID" 2>/dev/null || true
    fi
    rm -f "$BACKEND_PID_FILE"
    echo " - backend 종료 완료"
  else
    echo " - backend 프로세스가 실행 중이 아닙니다."
    rm -f "$BACKEND_PID_FILE"
  fi
else
  echo " - backend PID 파일을 찾을 수 없습니다. (이미 종료되었거나 실행되지 않았습니다)"
fi

echo
echo "3) PostgreSQL 컨테이너 종료 (docker-compose 사용 시)"
if command -v docker >/dev/null 2>&1 && command -v docker-compose >/dev/null 2>&1 && [ -f "docker-compose.yml" ]; then
  echo " - docker-compose.yml 감지, postgres 컨테이너를 종료합니다."
  docker-compose down
  echo " - PostgreSQL 컨테이너 종료 완료"
else
  echo " - docker/docker-compose 또는 docker-compose.yml을 찾지 못해 DB 컨테이너 종료를 건너뜁니다."
  echo "   로컬 PostgreSQL이 실행 중이라면 수동으로 종료해 주세요."
fi

echo
echo "[FinFlow] 모든 서버가 종료되었습니다."
exit 0
