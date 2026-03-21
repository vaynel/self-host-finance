"""KIS account connect service (minimal)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict

from sqlalchemy.orm import Session

import logging

from app.core.exceptions import raise_400, raise_404
from app.models.account import Account
from app.models.broker_account import BrokerAccount
from app.models.broker_token import BrokerToken
from app.services.kis_auth_service import KISAuthService
from app.schemas.investment import KISConnectRequest
from app.brokers.kis import discover_kis_acnt_prdt_cd, normalize_kis_account_input


logger = logging.getLogger("finflow.kis_account_service")


def connect_kis_account(db: Session, user_id: str, account_id: str, req: KISConnectRequest) -> Dict[str, Any]:
    """Create/update broker account detail + issue tokens + resolve ACNT_PRDT_CD + enable sync."""

    account = db.query(Account).filter(Account.id == account_id, Account.user_id == user_id).first()
    if not account:
        raise_404("계좌를 찾을 수 없습니다.")
    if account.type != "investment":
        raise_400("투자 계좌에서만 KIS 연동을 할 수 있습니다.")

    try:
        cano, hint = normalize_kis_account_input(req.broker_account_no)
    except ValueError as e:
        raise_400(str(e))

    manual_pc = req.product_code
    broker_account = (
        db.query(BrokerAccount)
        .filter(BrokerAccount.account_id == account_id, BrokerAccount.broker_type == "KIS")
        .first()
    )

    if not broker_account:
        broker_account = BrokerAccount(
            id=f"brk_{uuid.uuid4().hex[:12]}",
            account_id=account_id,
            broker_type="KIS",
            broker_account_no_masked=cano,
            product_code=manual_pc or "01",
            is_mock=req.is_mock,
            api_enabled=False,
            order_enabled=False,
            auto_trade_enabled=False,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(broker_account)
        db.commit()
        db.refresh(broker_account)
    else:
        broker_account.broker_account_no_masked = cano
        broker_account.is_mock = req.is_mock
        broker_account.api_enabled = False
        broker_account.order_enabled = False
        broker_account.product_code = manual_pc or "01"
        broker_account.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(broker_account)

    # 1) KIS OAuth 토큰 발급 (계좌 상품코드와 무관)
    try:
        KISAuthService.issue_token(db, broker_account)
    except ValueError as e:
        db.rollback()
        raise_400(str(e))
    except Exception as e:
        db.rollback()
        logger.exception("KIS token issue failed: account_id=%s broker_account_id=%s", account_id, broker_account.id)
        raise_400(
            "KIS 토큰 발급에 실패했습니다. App Key/Secret 및 네트워크 상태를 확인하세요.",
            details=[str(e)],
        )

    # 2) 상품코드: 직접 지정 없으면 잔고조회 API로 자동 탐색
    if manual_pc:
        resolved_pc = manual_pc
    else:
        try:
            resolved_pc = discover_kis_acnt_prdt_cd(db, broker_account, cano, hint=hint)
        except ValueError as e:
            raise_400(str(e))

    broker_account.product_code = resolved_pc
    broker_account.broker_account_no_masked = cano
    broker_account.api_enabled = True
    broker_account.order_enabled = True
    broker_account.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(broker_account)

    token = db.query(BrokerToken).filter(BrokerToken.broker_account_id == broker_account.id).first()

    return {
        "account_id": account_id,
        "broker_account_id": broker_account.id,
        "broker_type": broker_account.broker_type,
        "api_enabled": broker_account.api_enabled,
        "order_enabled": broker_account.order_enabled,
        "is_mock": broker_account.is_mock,
        "token_expires_at": token.expires_at.isoformat() if token and token.expires_at else None,
        "cano": cano,
        "resolved_product_code": resolved_pc,
        "product_code_auto": manual_pc is None,
    }

