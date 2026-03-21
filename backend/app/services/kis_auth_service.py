"""KIS OpenAPI authentication service."""

import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
import requests
import threading

from app.config import get_settings
from app.models.broker_account import BrokerAccount
from app.models.broker_token import BrokerToken
from app.core.token_encryption import encrypt_token, decrypt_token

settings = get_settings()

_token_issue_locks: dict[str, threading.Lock] = {}


def _get_lock(broker_account_id: str) -> threading.Lock:
    # broker_account_id 기준으로 발급 경쟁을 막기 위한 동기화 락
    lock = _token_issue_locks.get(broker_account_id)
    if lock is None:
        lock = threading.Lock()
        _token_issue_locks[broker_account_id] = lock
    return lock


class KISAuthService:
    """한국투자증권 OpenAPI 인증 서비스."""

    @staticmethod
    def _get_base_url(is_mock: bool) -> str:
        """실전/모의투자 환경에 따른 base URL 반환."""
        return settings.kis_mock_base_url if is_mock else settings.kis_base_url

    @staticmethod
    def _get_token_url(is_mock: bool) -> str:
        """토큰 발급 URL."""
        base_url = KISAuthService._get_base_url(is_mock)
        return f"{base_url}/oauth2/tokenP"

    @staticmethod
    def issue_token(
        db: Session,
        broker_account: BrokerAccount,
        app_key: Optional[str] = None,
        app_secret: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        KIS OAuth 토큰 발급 및 저장.
        
        Args:
            db: 데이터베이스 세션
            broker_account: 브로커 계좌 정보
            app_key: KIS App Key (없으면 설정에서 가져옴)
            app_secret: KIS App Secret (없으면 설정에서 가져옴)
            
        Returns:
            {
                "access_token": str,
                "token_type": str,
                "expires_in": int,
                "refresh_token": str,
                "refresh_token_expires_in": int,
            }
        """
        app_key = app_key or settings.kis_app_key
        app_secret = app_secret or settings.kis_app_secret

        if not app_key or not app_secret:
            raise ValueError("KIS App Key와 App Secret이 설정되지 않았습니다.")

        # 토큰 발급 경쟁 및 불필요한 재발급 방지:
        # 이미 유효한 access token이 있으면 재발급하지 않습니다.
        existing = db.query(BrokerToken).filter(BrokerToken.broker_account_id == broker_account.id).first()
        now = datetime.utcnow()
        # KIS는 토큰을 24시간 정도 유지하므로, 만료 시점 전에는 재발급하지 않습니다.
        if existing and existing.expires_at and existing.expires_at > now:
            try:
                access_token = decrypt_token(existing.encrypted_access_token)
                return {
                    "access_token": access_token,
                    "token_type": existing.token_type,
                    "expires_in": int((existing.expires_at - now).total_seconds()),
                    "refresh_token": None,
                    "refresh_token_expires_in": None,
                }
            except Exception:
                # 암호화 키 변경 등으로 복호화 실패 시, 안전하게 재발급 진행
                pass

        # broker_account 단위로 토큰 발급이 중복되지 않게 락을 잡습니다.
        with _get_lock(broker_account.id):
            # 락 획득 후 다시 한번 체크(다른 요청이 이미 갱신했을 수 있음)
            existing = db.query(BrokerToken).filter(BrokerToken.broker_account_id == broker_account.id).first()
            if existing and existing.expires_at and existing.expires_at > now:
                access_token = decrypt_token(existing.encrypted_access_token)
                return {
                    "access_token": access_token,
                    "token_type": existing.token_type,
                    "expires_in": int((existing.expires_at - now).total_seconds()),
                    "refresh_token": None,
                    "refresh_token_expires_in": None,
                }

            base_url = KISAuthService._get_base_url(broker_account.is_mock)
            token_url = f"{base_url}/oauth2/tokenP"

            # KIS OAuth 토큰 발급 요청
            headers = {
                "content-type": "application/json",
            }
            data = {
                "grant_type": "client_credentials",
                "appkey": app_key,
                "appsecret": app_secret,
            }

            response = requests.post(token_url, json=data, headers=headers, timeout=10)
            response.raise_for_status()
            token_data = response.json()

            # 토큰 정보 추출
            access_token = token_data.get("access_token")
            token_type = token_data.get("token_type", "Bearer")
            expires_in = token_data.get("expires_in", 86400)  # 기본 24시간
            refresh_token = token_data.get("refresh_token")
            refresh_token_expires_in = token_data.get("refresh_token_expires_in", 0)

            # 만료 시각 계산
            expires_at = datetime.utcnow() + timedelta(seconds=float(expires_in))
            refresh_expires_at = None
            if refresh_token_expires_in and float(refresh_token_expires_in) > 0:
                refresh_expires_at = datetime.utcnow() + timedelta(seconds=float(refresh_token_expires_in))

            # 기존 토큰 조회 또는 생성
            broker_token = db.query(BrokerToken).filter(
                BrokerToken.broker_account_id == broker_account.id
            ).first()

            if broker_token:
                broker_token.encrypted_access_token = encrypt_token(access_token)
                if refresh_token:
                    broker_token.encrypted_refresh_token = encrypt_token(refresh_token)
                broker_token.token_type = token_type
                broker_token.expires_at = expires_at
                broker_token.refresh_expires_at = refresh_expires_at
                broker_token.updated_at = datetime.utcnow()
            else:
                broker_token = BrokerToken(
                    id=str(uuid.uuid4()),
                    broker_account_id=broker_account.id,
                    encrypted_access_token=encrypt_token(access_token),
                    encrypted_refresh_token=encrypt_token(refresh_token) if refresh_token else None,
                    token_type=token_type,
                    expires_at=expires_at,
                    refresh_expires_at=refresh_expires_at,
                )
                db.add(broker_token)

            db.commit()
            db.refresh(broker_token)

            return {
                "access_token": access_token,  # 메모리에서만 평문 사용
                "token_type": token_type,
                "expires_in": int(float(expires_in)),
                "refresh_token": refresh_token,
                "refresh_token_expires_in": int(float(refresh_token_expires_in or 0)),
            }

        # 아래는 이론상 도달하지 않습니다(락 내부에서 return).
        raise RuntimeError("KIS token issue flow failed unexpectedly.")

    @staticmethod
    def refresh_token(
        db: Session,
        broker_account: BrokerAccount,
    ) -> Dict[str, Any]:
        """
        Refresh token을 사용하여 새로운 access token 발급.
        
        Args:
            db: 데이터베이스 세션
            broker_account: 브로커 계좌 정보
            
        Returns:
            토큰 정보 딕셔너리
        """
        broker_token = db.query(BrokerToken).filter(
            BrokerToken.broker_account_id == broker_account.id
        ).first()

        if not broker_token or not broker_token.encrypted_refresh_token:
            raise ValueError("Refresh token이 없습니다. issue_token을 먼저 호출하세요.")

        # Refresh token이 만료되었는지 확인
        if broker_token.refresh_expires_at and broker_token.refresh_expires_at < datetime.utcnow():
            raise ValueError("Refresh token이 만료되었습니다. issue_token을 다시 호출하세요.")

        # 기존 토큰 발급 로직 재사용 (KIS는 refresh token으로 재발급하는 API가 별도일 수 있음)
        # 여기서는 간단히 재발급으로 처리
        return KISAuthService.issue_token(db, broker_account)

    @staticmethod
    def get_access_token(db: Session, broker_account: BrokerAccount) -> str:
        """
        저장된 access token을 반환. 만료되었으면 자동 갱신.
        
        Args:
            db: 데이터베이스 세션
            broker_account: 브로커 계좌 정보
            
        Returns:
            Access token (평문)
        """
        broker_token = db.query(BrokerToken).filter(BrokerToken.broker_account_id == broker_account.id).first()

        if not broker_token:
            raise ValueError("토큰이 발급되지 않았습니다. issue_token을 먼저 호출하세요.")

        now = datetime.utcnow()

        # 토큰은 24시간 유지이므로, 만료 전에는 절대 재발급하지 않습니다.
        if broker_token.expires_at and broker_token.expires_at > now:
            return decrypt_token(broker_token.encrypted_access_token)

        # expires_at이 없거나 만료된 경우에만 issue_token으로 재발급합니다.
        KISAuthService.issue_token(db, broker_account)
        broker_token = db.query(BrokerToken).filter(BrokerToken.broker_account_id == broker_account.id).first()

        return decrypt_token(broker_token.encrypted_access_token)
