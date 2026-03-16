#!/usr/bin/env bash
set -euo pipefail

echo "[FinFlow] 설치를 시작합니다."

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

echo "0) backend/.env 자동 생성 (docker-compose.yml 기준, 없을 때만)"
if [ -d "backend" ]; then
  ENV_PATH="$PROJECT_ROOT/backend/.env"
  if [ -f "$ENV_PATH" ]; then
    echo " - backend/.env 이미 존재, 건너뜁니다."
  else
    POSTGRES_USER=""
    POSTGRES_PASSWORD=""
    POSTGRES_DB=""
    if [ -f "$PROJECT_ROOT/docker-compose.yml" ]; then
      POSTGRES_USER="$(awk -F': ' '/POSTGRES_USER:/ {print $2; exit}' "$PROJECT_ROOT/docker-compose.yml" | tr -d '"' | tr -d '\r')"
      POSTGRES_PASSWORD="$(awk -F': ' '/POSTGRES_PASSWORD:/ {print $2; exit}' "$PROJECT_ROOT/docker-compose.yml" | tr -d '"' | tr -d '\r')"
      POSTGRES_DB="$(awk -F': ' '/POSTGRES_DB:/ {print $2; exit}' "$PROJECT_ROOT/docker-compose.yml" | tr -d '"' | tr -d '\r')"
    fi

    : "${POSTGRES_USER:=my_fin}"
    : "${POSTGRES_PASSWORD:=password123!}"
    : "${POSTGRES_DB:=fin}"

    JWT_SECRET="change-me-please-set-32-chars-min"
    if command -v openssl >/dev/null 2>&1; then
      JWT_SECRET="$(openssl rand -hex 32)"
    fi

    echo " - backend/.env 생성: $ENV_PATH"
    cat >"$ENV_PATH" <<EOF
DATABASE_URL=postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@localhost:5432/${POSTGRES_DB}
JWT_SECRET=${JWT_SECRET}
CORS_ORIGIN=http://localhost:8000
PORT=8001
EOF
  fi
fi

echo "1) backend 가상환경 및 패키지 설치"
if [ ! -d "backend" ]; then
  echo "오류: backend 디렉터리를 찾을 수 없습니다."
  exit 1
fi

cd backend

pick_python() {
  for c in python3.12 python3.11 python3; do
    if command -v "$c" >/dev/null 2>&1; then
      "$c" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3,11) else 1)' >/dev/null 2>&1 || continue
      echo "$c"
      return 0
    fi
  done
  return 1
}

PYTHON_VENV_CREATOR="$(pick_python || true)"
if [ -z "${PYTHON_VENV_CREATOR}" ]; then
  echo "오류: Python 3.11 이상이 필요합니다. (현재 python3는 3.11 미만으로 보입니다)"
  echo " - 해결(예): 시스템에 python3.11 설치 후 다시 실행"
  echo "   RHEL/CentOS 계열 예시:"
  echo "     sudo dnf install -y python3.11 python3.11-pip python3.11-devel"
  exit 1
fi

if [ -d ".venv" ] && [ -x ".venv/bin/python" ]; then
  if ! .venv/bin/python -c 'import sys; raise SystemExit(0 if sys.version_info >= (3,11) else 1)' >/dev/null 2>&1; then
    echo " - 기존 .venv가 Python 3.11 미만입니다. 재생성합니다."
    rm -rf .venv
  else
    echo " - 기존 .venv 감지, 재사용합니다."
  fi
fi

if [ ! -d ".venv" ]; then
  echo " - Python 가상환경(.venv) 생성 ($PYTHON_VENV_CREATOR)"
  "$PYTHON_VENV_CREATOR" -m venv .venv
fi

VENV_PY="$(pwd)/.venv/bin/python"
if [ ! -x "$VENV_PY" ]; then
  echo "오류: 가상환경 Python을 찾을 수 없습니다: $VENV_PY"
  echo " - 해결: backend/.venv 삭제 후 재실행"
  exit 1
fi

PYTHON_BIN="$VENV_PY"

echo " - pip 사용 가능 여부 확인"
if ! "$PYTHON_BIN" -m pip --version >/dev/null 2>&1; then
  echo "   pip이 없어 ensurepip로 설치를 시도합니다."
  if "$PYTHON_BIN" -m ensurepip --upgrade >/dev/null 2>&1; then
    echo "   ensurepip 완료"
  else
    echo "오류: pip을 사용할 수 없습니다."
    echo " - 해결: OS 패키지로 python3-pip 설치 또는 venv 재생성 필요"
    exit 1
  fi
fi

if [ -f "requirements.txt" ]; then
  echo " - requirements.txt 기반 패키지 설치"
  "$PYTHON_BIN" -m pip install --upgrade pip
  "$PYTHON_BIN" -m pip install -r requirements.txt
else
  echo " - requirements.txt가 없어 pyproject.toml 기반 설치 시도"
  if [ -f "pyproject.toml" ]; then
    "$PYTHON_BIN" -m pip install --upgrade pip
    "$PYTHON_BIN" -m pip install .
  else
    echo "오류: requirements.txt 또는 pyproject.toml을 찾을 수 없습니다."
    exit 1
  fi
fi

echo
echo "2) 데이터베이스 컨테이너(docker-compose) 준비 (선택사항)"
cd "$PROJECT_ROOT"
if command -v docker >/dev/null 2>&1 && command -v docker-compose >/dev/null 2>&1; then
  if [ -f "docker-compose.yml" ]; then
    echo " - docker-compose.yml 발견, postgres 컨테이너를 백그라운드로 올립니다."
    docker-compose up -d
  else
    echo " - docker-compose.yml이 없어 DB 컨테이너는 건너뜁니다."
  fi
else
  echo " - docker 또는 docker-compose 명령을 찾을 수 없어 DB 컨테이너 설정을 건너뜁니다."
fi

echo
echo "3) frontend 의존성 설치"
if [ -f "$PROJECT_ROOT/frontend/package.json" ]; then
  cd "$PROJECT_ROOT/frontend"
  ver_ge() {
    # usage: ver_ge 20.19.0 20.18.1  -> true if 20.18.1 >= 20.19.0
    [ "$(printf '%s\n%s\n' "$1" "$2" | sort -V | head -n1)" = "$1" ]
  }

  NODE_OK=0
  if command -v node >/dev/null 2>&1; then
    NODE_VER="$(node -v | sed 's/^v//' || true)"
    if [ -n "$NODE_VER" ] && ver_ge "20.19.0" "$NODE_VER"; then
      NODE_OK=1
    fi
  fi

  if [ "$NODE_OK" -ne 1 ]; then
    echo " - Node.js 버전이 낮거나 미설치입니다. (필요: >= 20.19.0 또는 >= 22.12.0)"
    echo " - 현재: $(node -v 2>/dev/null || echo 'node 없음')"
    echo " - Node.js(22 LTS) 설치/업그레이드를 시도합니다."
    if command -v dnf >/dev/null 2>&1; then
      set +e
      # 1) AppStream 모듈로 시도 (환경에 따라 18만 제공될 수도 있음)
      dnf -y module reset nodejs >/dev/null 2>&1
      dnf -y module enable nodejs:22 >/dev/null 2>&1
      dnf -y install nodejs npm >/dev/null 2>&1
      DNF_RC=$?
      set -e
      if [ "$DNF_RC" -ne 0 ]; then
        echo "경고: dnf로 Node.js/npm 설치에 실패했습니다. (레포/권한/네트워크 확인 필요)"
      fi

      # 2) 아직도 버전이 낮으면 NodeSource로 시도 (best-effort)
      if command -v node >/dev/null 2>&1; then
        NODE_VER="$(node -v | sed 's/^v//' || true)"
        if [ -n "$NODE_VER" ] && ! ver_ge "20.19.0" "$NODE_VER"; then
          if command -v curl >/dev/null 2>&1; then
            echo " - AppStream Node 버전이 낮아 NodeSource로 업그레이드를 시도합니다."
            set +e
            curl -fsSL https://rpm.nodesource.com/setup_22.x | bash - >/dev/null 2>&1
            dnf -y install nodejs >/dev/null 2>&1
            NS_RC=$?
            set -e
            if [ "$NS_RC" -ne 0 ]; then
              echo "경고: NodeSource 설치에 실패했습니다."
            fi
          else
            echo "경고: curl이 없어 NodeSource 설치를 건너뜁니다."
          fi
        fi
      fi
    else
      echo "경고: dnf가 없어 자동 설치를 건너뜁니다."
    fi
  fi

  # 설치/업그레이드 후 최종 버전 재확인
  if command -v node >/dev/null 2>&1; then
    NODE_VER="$(node -v | sed 's/^v//' || true)"
    if [ -n "$NODE_VER" ] && ver_ge "20.19.0" "$NODE_VER"; then
      :
    else
      echo "경고: Node 버전이 요구사항을 만족하지 않습니다. (현재: v${NODE_VER:-unknown})"
      echo " - 권장: Node 22.12+ 또는 20.19+ 설치"
    fi
  fi

  if command -v bun >/dev/null 2>&1; then
    echo " - bun 감지: bun install"
    bun install
  elif command -v npm >/dev/null 2>&1; then
    if [ -f "package-lock.json" ]; then
      echo " - package-lock.json 감지: npm ci"
      npm ci
    else
      echo " - npm install"
      npm install
    fi

    echo " - npm audit fix (best-effort)"
    set +e
    npm audit fix >/dev/null 2>&1
    set -e
  elif command -v yarn >/dev/null 2>&1; then
    echo " - yarn 감지: yarn install"
    yarn install
  else
    echo "경고: bun/npm/yarn이 없어 frontend 설치를 건너뜁니다."
    echo " - 해결(예): Node.js 20+ 설치 후 npm 사용"
  fi
else
  echo " - frontend/package.json이 없어 frontend 설치를 건너뜁니다."
fi

echo
echo "[FinFlow] 설치가 완료되었습니다."
echo "이제 start.sh를 사용해 서버를 실행할 수 있습니다."

