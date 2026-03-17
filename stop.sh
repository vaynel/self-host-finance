#!/usr/bin/env bash
set -euo pipefail

echo "[FinFlow] 서버 종료를 시작합니다."

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

BACKEND_PID_FILE="$PROJECT_ROOT/logs/backend.pid"
FRONTEND_PID_FILE="$PROJECT_ROOT/logs/frontend.pid"

kill_pid_gracefully() {
  local pid="$1"
  local name="$2"
  if [ -z "${pid:-}" ]; then
    return 1
  fi
  if ! kill -0 "$pid" >/dev/null 2>&1; then
    return 1
  fi
  echo " - ${name} 프로세스 종료 중... (PID: $pid)"
  kill "$pid" 2>/dev/null || true
  sleep 1
  if kill -0 "$pid" >/dev/null 2>&1; then
    echo " - ${name} 강제 종료 중... (PID: $pid)"
    kill -9 "$pid" 2>/dev/null || true
  fi
  return 0
}

find_pid_by_port() {
  local port="$1"
  if command -v ss >/dev/null 2>&1; then
    # ss 출력에서 pid=1234 추출
    ss -tlnp 2>/dev/null | grep -E ":${port}\\b" | sed -n 's/.*pid=\\([0-9]\\+\\).*/\\1/p' | head -n 1
  else
    echo ""
  fi
}

kill_uvicorn_backend() {
  # 1) PID 파일
  if [ -f "$BACKEND_PID_FILE" ]; then
    local pid
    pid="$(cat "$BACKEND_PID_FILE" 2>/dev/null || echo "")"
    if kill_pid_gracefully "$pid" "backend(uvicorn)"; then
      rm -f "$BACKEND_PID_FILE"
      echo " - backend 종료 완료 (PID 파일 삭제)"
      return 0
    fi
    # stale PID 파일
    rm -f "$BACKEND_PID_FILE"
  fi

  # 2) 포트 기반(8001)
  local port_pid
  port_pid="$(find_pid_by_port 8001 || true)"
  if [ -n "${port_pid:-}" ] && kill_pid_gracefully "$port_pid" "backend(uvicorn)"; then
    echo " - backend 종료 완료 (포트 8001 기반)"
    return 0
  fi

  # 3) 커맨드 기반 fallback
  if command -v pkill >/dev/null 2>&1; then
    if pkill -f "uvicorn app.main:app" >/dev/null 2>&1; then
      echo " - backend 종료 완료 (pkill -f \"uvicorn app.main:app\")"
      return 0
    fi
  fi

  echo " - backend(uvicorn) 프로세스를 찾지 못했습니다."
  return 1
}

echo
echo "1) Frontend 서버 종료"
if [ -f "$FRONTEND_PID_FILE" ]; then
  FRONTEND_PID="$(cat "$FRONTEND_PID_FILE" 2>/dev/null || echo "")"
  if [ -n "$FRONTEND_PID" ] && kill -0 "$FRONTEND_PID" >/dev/null 2>&1; then
    kill_pid_gracefully "$FRONTEND_PID" "frontend"
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
kill_uvicorn_backend || true

echo
echo "2.5) Frontend(vite) 잔여 프로세스 정리 (포트 기반)"
# start.sh PID 파일이 stale이거나 vite가 다른 포트(8081 등)로 떠버리는 케이스가 있어 포트 기반으로 한 번 더 정리합니다.
for p in 8080 8081; do
  pid="$(find_pid_by_port "$p" || true)"
  if [ -n "${pid:-}" ]; then
    kill_pid_gracefully "$pid" "frontend(vite:${p})" || true
  fi
done

# 포트에 안 걸려도 남아있는 vite 프로세스가 있을 수 있어 커맨드 기반으로 한 번 더 정리
if command -v pkill >/dev/null 2>&1; then
  pkill -f "/frontend/node_modules/.bin/vite" >/dev/null 2>&1 || true
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
