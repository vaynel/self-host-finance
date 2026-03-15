#!/usr/bin/env python3
"""
데이터베이스 생성 스크립트
"""
import sys
import os
import getpass
from urllib.parse import urlparse, urlunparse
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# DATABASE_URL 환경변수에서 읽거나 기본값 사용
database_url = os.getenv("DATABASE_URL", "postgresql://localhost:5435/finflow")

# URL 파싱
parsed = urlparse(database_url)
db_name = parsed.path.lstrip("/")  # finflow

# 기본 데이터베이스(postgres)에 연결하기 위한 URL 생성
# 사용자명과 비밀번호가 없으면 환경변수 또는 기본값 사용
username = parsed.username or "postgres"
# Docker 컨테이너의 비밀번호 확인: POSTGRES_PASSWORD 환경변수 또는 기본값 "mandu"
password = parsed.password or os.getenv("POSTGRES_PASSWORD") or os.getenv("POSTGRES_PASSWORD", "mandu")

# 기본 데이터베이스 URL 구성
if password:
    base_url = f"{parsed.scheme}://{username}:{password}@{parsed.hostname}:{parsed.port}/postgres"
else:
    base_url = f"{parsed.scheme}://{username}@{parsed.hostname}:{parsed.port}/postgres"

print(f"데이터베이스 '{db_name}' 생성 중...")
print(f"연결: {parsed.hostname}:{parsed.port}")

try:
    # postgres 데이터베이스에 연결하여 새 데이터베이스 생성
    admin_engine = create_engine(base_url, isolation_level="AUTOCOMMIT")
    
    with admin_engine.connect() as conn:
        # 기존 데이터베이스가 있으면 삭제
        conn.execute(text(f"DROP DATABASE IF EXISTS {db_name}"))
        print(f"✓ 기존 데이터베이스 '{db_name}' 삭제됨 (있었다면)")
        
        # 새 데이터베이스 생성
        conn.execute(text(f"CREATE DATABASE {db_name}"))
        print(f"✓ 데이터베이스 '{db_name}' 생성 완료!")
        
except OperationalError as e:
    error_msg = str(e)
    print(f"❌ 오류 발생: {e}")
    
    if "password authentication failed" in error_msg.lower():
        print("\n비밀번호 인증 실패!")
        print("\n다음 방법 중 하나를 시도해보세요:")
        print("1. .env 파일에 DATABASE_URL을 설정하세요:")
        print("   DATABASE_URL=postgresql://사용자명:비밀번호@localhost:5435/finflow")
        print("\n2. 또는 Docker 컨테이너에 직접 접속:")
        print("   docker exec -it mandu_postgres psql -U postgres -c 'CREATE DATABASE finflow;'")
        print("\n3. 환경변수로 비밀번호 설정:")
        print("   export POSTGRES_PASSWORD=your_password")
        print("   python create_db.py")
    else:
        print("\n다음 사항을 확인해주세요:")
        print("1. PostgreSQL이 실행 중인지 확인")
        print("2. 데이터베이스 연결 정보가 올바른지 확인")
        print("3. 필요한 권한이 있는지 확인")
    sys.exit(1)
except Exception as e:
    print(f"❌ 예상치 못한 오류: {e}")
    sys.exit(1)
