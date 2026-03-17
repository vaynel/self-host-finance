#!/usr/bin/env bash
set -euo pipefail

echo "[FinFlow] 서버 실행을 시작합니다. (nohup 백그라운드)"

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

mkdir -p "$PROJECT_ROOT/logs"
BACKEND_LOG="$PROJECT_ROOT/logs/backend.log"
FRONTEND_LOG="$PROJECT_ROOT/logs/frontend.log"
BACKEND_PID_FILE="$PROJECT_ROOT/logs/backend.pid"
FRONTEND_PID_FILE="$PROJECT_ROOT/logs/frontend.pid"

echo "[FinFlow] backend 로그: $BACKEND_LOG"
echo "[FinFlow] frontend 로그: $FRONTEND_LOG"

echo "1) PostgreSQL 컨테이너 상태 확인 (docker-compose 사용 시)"
if command -v docker >/dev/null 2>&1 && command -v docker-compose >/dev/null 2>&1 && [ -f "docker-compose.yml" ]; then
  echo " - docker-compose.yml 감지, postgres 컨테이너를 백그라운드로 실행합니다."
  docker-compose up -d
else
  echo " - docker/docker-compose 또는 docker-compose.yml을 찾지 못해 DB 컨테이너 실행을 건너뜁니다."
  echo "   로컬에 PostgreSQL가 이미 실행 중이어야 합니다."
fi

echo
echo "2) Backend 서버 실행 (nohup)"
if [ ! -d "backend" ]; then
  echo "오류: backend 디렉터리를 찾을 수 없습니다."
  exit 1
fi

cd backend

if [ -d ".venv" ]; then
  echo " - .venv 활성화"
  PYTHON_BIN="$(pwd)/.venv/bin/python"
else
  echo "경고: .venv를 찾을 수 없습니다. 현재 시스템 Python으로 실행합니다."
  PYTHON_BIN="python3"
fi

if ! "$PYTHON_BIN" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3,11) else 1)' >/dev/null 2>&1; then
  echo "오류: Backend는 Python 3.11 이상이 필요합니다."
  echo " - 현재: $("$PYTHON_BIN" -V 2>&1 || true)"
  echo " - 해결: ./install.sh 실행 시 Python 3.11 가상환경이 만들어지도록 python3.11 설치 후 재설치"
  exit 1
fi

if [ ! -f ".env" ]; then
  echo "경고: backend/.env 파일이 없습니다."
  echo " - 해결: ./.install.sh 를 먼저 실행해 자동 생성하거나, docs/실행가이드.md 예시대로 생성해 주세요."
fi

echo " - alembic 마이그레이션 적용"
if "$PYTHON_BIN" -m alembic --help >/dev/null 2>&1; then
  if ! "$PYTHON_BIN" -m alembic upgrade head; then
    echo "경고: 마이그레이션이 실패했습니다. (DB 연결/환경변수 설정을 확인해 주세요)"
    echo " - DATABASE_URL 예시: postgresql://user:pass@localhost:5432/finflow"
  fi
else
  echo "경고: alembic을 실행할 수 없습니다. (가상환경 패키지 설치를 확인해 주세요)"
fi

echo " - uvicorn 개발 서버 백그라운드 실행 (포트 8001)"
cd "$PROJECT_ROOT/backend"
find_pid_by_port() {
  local port="$1"
  if command -v ss >/dev/null 2>&1; then
    ss -tlnp 2>/dev/null | grep -E ":${port}\\b" | sed -n 's/.*pid=\\([0-9]\\+\\).*/\\1/p' | head -n 1
  else
    echo ""
  fi
}

existing_backend_pid=""
if [ -f "$BACKEND_PID_FILE" ]; then
  existing_backend_pid="$(cat "$BACKEND_PID_FILE" 2>/dev/null || echo "")"
fi

# 1) PID 파일이 살아있으면 그대로
if [ -n "${existing_backend_pid:-}" ] && kill -0 "$existing_backend_pid" >/dev/null 2>&1; then
  echo " - backend 이미 실행 중입니다. (PID: $existing_backend_pid)"
else
  # stale PID 파일 제거
  rm -f "$BACKEND_PID_FILE" || true

  # 2) 포트 8001 점유 여부 확인 (PID 파일이 없거나 죽었을 때)
  port_pid="$(find_pid_by_port 8001 || true)"
  if [ -n "${port_pid:-}" ] && kill -0 "$port_pid" >/dev/null 2>&1; then
    echo " - backend 이미 실행 중입니다. (포트 8001, PID: $port_pid)"
    echo "$port_pid" >"$BACKEND_PID_FILE"
  else
    nohup "$PYTHON_BIN" -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8001 >>"$BACKEND_LOG" 2>&1 &
    BACKEND_PID=$!
    echo "$BACKEND_PID" >"$BACKEND_PID_FILE"
    echo " - backend PID: $BACKEND_PID (저장: $BACKEND_PID_FILE)"
  fi
fi

echo
echo "3) Frontend 서버 실행 (nohup)"
if [ -f "$PROJECT_ROOT/frontend/package.json" ]; then
  cd "$PROJECT_ROOT/frontend"
  if [ -f "$FRONTEND_PID_FILE" ] && kill -0 "$(cat "$FRONTEND_PID_FILE" 2>/dev/null)" >/dev/null 2>&1; then
    echo " - frontend 이미 실행 중입니다. (PID: $(cat "$FRONTEND_PID_FILE"))"
  else
    # 8080 포트를 점유 중인 프로세스가 있으면(이전 vite 잔여 등) 정리 후 시작
    FRONT_PORT_PID="$(find_pid_by_port 8080 || true)"
    if [ -n "${FRONT_PORT_PID:-}" ] && kill -0 "$FRONT_PORT_PID" >/dev/null 2>&1; then
      echo " - 경고: 8080 포트가 사용 중입니다. (PID: $FRONT_PORT_PID) 기존 프로세스를 종료합니다."
      kill "$FRONT_PORT_PID" 2>/dev/null || true
      sleep 1
    fi

    if command -v bun >/dev/null 2>&1; then
      nohup bun run dev -- --host 0.0.0.0 --port 8080 >>"$FRONTEND_LOG" 2>&1 &
    elif command -v npm >/dev/null 2>&1; then
      nohup npm run dev -- --host 0.0.0.0 --port 8080 >>"$FRONTEND_LOG" 2>&1 &
    elif command -v yarn >/dev/null 2>&1; then
      nohup yarn dev --host 0.0.0.0 --port 8080 >>"$FRONTEND_LOG" 2>&1 &
    else
      echo "경고: bun/npm/yarn이 없어 frontend 실행을 건너뜁니다."
      echo " - 해결(예): Node.js 18+ 설치 후 npm 사용"
      FRONTEND_PID=""
    fi
    if [ -n "${FRONTEND_PID:-}" ]; then
      :
    else
      if jobs -p >/dev/null 2>&1; then
        FRONTEND_PID="$(jobs -p | tail -n 1)"
      fi
    fi
    if [ -n "${FRONTEND_PID:-}" ]; then
      echo "$FRONTEND_PID" >"$FRONTEND_PID_FILE"
      echo " - frontend PID: $FRONTEND_PID (저장: $FRONTEND_PID_FILE)"
    fi
  fi
else
  echo "경고: frontend/package.json이 없어 frontend 실행을 건너뜁니다. (현재 frontend 디렉터리가 비어있습니다)"
fi

echo
echo "[FinFlow] 백그라운드로 실행했습니다."
echo " - backend 로그: $BACKEND_LOG"
echo " - frontend 로그: $FRONTEND_LOG"
echo "종료하려면: kill \$(cat logs/backend.pid) ; kill \$(cat logs/frontend.pid) (frontend가 실행된 경우)"
exit 0

