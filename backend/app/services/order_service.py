"""Investment order and execution service."""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.brokers.kis import KISAdapter
from app.core.exceptions import raise_400, raise_404
from app.core.security import create_trade_id, create_txn_id
from app.models.account import Account
from app.models.broker_account import BrokerAccount
from app.models.investment import InvestmentTrade
from app.models.investment_order import InvestmentExecution, InvestmentOrder, OrderStatus
from app.models.transaction import Transaction


def _to_order_dict(order: InvestmentOrder, executions: list[InvestmentExecution]) -> Dict[str, Any]:
    return {
        "id": order.id,
        "ticker": order.ticker,
        "side": order.side,
        "quantity": float(order.quantity),
        "price": float(order.price) if order.price else None,
        "order_type": order.order_type,
        "broker_order_id": order.broker_order_id,
        "status": order.status,
        "requested_at": order.requested_at.isoformat(),
        "filled_at": order.filled_at.isoformat() if order.filled_at else None,
        "executions": [
            {
                "id": e.id,
                "broker_execution_id": e.broker_execution_id,
                "executed_quantity": float(e.executed_quantity),
                "executed_price": float(e.executed_price),
                "fee": float(e.fee) if e.fee else None,
                "executed_at": e.executed_at.isoformat(),
                "settled": e.settled,
                "settled_at": e.settled_at.isoformat() if e.settled_at else None,
            }
            for e in executions
        ],
    }


def _settle_execution(db: Session, order: InvestmentOrder, execution: InvestmentExecution) -> bool:
    """Apply execution-based settlement exactly once.

    Idempotency rules:
    - if execution.settled == "yes", skip
    - executions are uniquely keyed by broker_execution_id
    """
    if execution.settled == "yes":
        return False

    account = db.query(Account).filter(Account.id == order.account_id, Account.user_id == order.user_id).first()
    if not account:
        execution.settled = "error"
        execution.updated_at = datetime.utcnow()
        return False

    qty = Decimal(str(execution.executed_quantity))
    price = Decimal(str(execution.executed_price))
    fee = Decimal(str(execution.fee or 0))

    if order.side == "buy":
        cash_delta = -(qty * price + fee)
        txn_type = "expense"
        action = "buy"
    else:
        cash_delta = qty * price - fee
        txn_type = "income"
        action = "sell"

    trade = InvestmentTrade(
        id=create_trade_id(),
        user_id=order.user_id,
        ticker=order.ticker,
        name=order.name,
        type="stock",
        action=action,
        date=execution.executed_at.date(),
        shares=qty,
        price=price,
        fee=fee,
    )
    db.add(trade)

    txn = Transaction(
        id=create_txn_id(),
        user_id=order.user_id,
        date=execution.executed_at.date(),
        description=f"{(order.name or order.ticker)} {action} 체결",
        amount=cash_delta,
        type=txn_type,
        category="투자",
        account=account.name,
        memo=f"order:{order.id} exec:{execution.id}",
    )
    db.add(txn)

    account.balance = account.balance + cash_delta
    execution.settled = "yes"
    execution.settled_at = datetime.utcnow()
    execution.updated_at = datetime.utcnow()
    return True


def create_order(
    db: Session,
    user_id: str,
    account_id: str,
    ticker: str,
    side: str,
    quantity: Decimal,
    price: Optional[Decimal] = None,
    order_type: str = "limit",
) -> Dict[str, Any]:
    """주문 생성 및 브로커 API 호출."""
    account = db.query(Account).filter(Account.id == account_id, Account.user_id == user_id).first()
    if not account:
        raise_404("계좌를 찾을 수 없습니다.")
    if account.type != "investment":
        raise_400("투자 계좌가 아닙니다.")

    broker_account = db.query(BrokerAccount).filter(BrokerAccount.account_id == account_id).first()
    if not broker_account:
        raise_400("브로커 연동이 설정되지 않은 계좌입니다.")
    if not broker_account.api_enabled or not broker_account.order_enabled:
        raise_400("주문이 활성화되지 않은 계좌입니다.")
    if order_type == "limit" and price is None:
        raise_400("지정가 주문은 가격이 필요합니다.")

    adapter = KISAdapter(db, broker_account)
    # Pre-check to reduce broker-side rejections (best effort)
    if side == "sell":
        try:
            sellable = adapter.get_sellable_quantity(ticker)
            if sellable <= 0:
                raise_400("매도가능수량이 없습니다.")
            if quantity > sellable:
                raise_400(f"매도가능수량을 초과했습니다. (요청={quantity}, 가능={sellable})")
        except Exception as e:
            # If the pre-check fails (API/parse), don't block the order attempt.
            # The broker_result error path will still report the failure.
            pass
    try:
        broker_result = adapter.place_order(
            ticker=ticker,
            side=side,
            quantity=quantity,
            price=price,
            order_type=order_type,
        )
    except Exception as e:
        raise_400(f"주문 실행 실패: {str(e)}")

    broker_order_id = (broker_result.get("order_id") if isinstance(broker_result, dict) else None) or ""
    broker_order_id = str(broker_order_id).strip()
    if not broker_order_id:
        # If we don't have a broker order id, we cannot refresh/settle later.
        # Do not create a pending local order that will block auto-trade as a "duplicate pending".
        raise_400("주문 실행 실패: 브로커 주문번호(order_id)를 받지 못했습니다.")

    order = InvestmentOrder(
        id=f"ord_{uuid.uuid4().hex[:12]}",
        user_id=user_id,
        account_id=account_id,
        broker_account_id=broker_account.id,
        ticker=ticker,
        side=side,
        quantity=quantity,
        price=price,
        order_type=order_type,
        broker_order_id=broker_order_id,
        status=OrderStatus.PENDING.value,
        requested_at=datetime.utcnow(),
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    return _to_order_dict(order, [])


def cancel_order(db: Session, user_id: str, order_id: str) -> Dict[str, Any]:
    """취소 요청: KIS 정정/취소 API로 잔량 전부 취소."""
    order = db.query(InvestmentOrder).filter(InvestmentOrder.id == order_id, InvestmentOrder.user_id == user_id).first()
    if not order:
        raise_404("주문을 찾을 수 없습니다.")
    if not order.broker_account_id or not order.broker_order_id:
        raise_400("브로커 주문번호가 없어 취소할 수 없습니다.")

    broker_account = db.query(BrokerAccount).filter(BrokerAccount.id == order.broker_account_id).first()
    if not broker_account or not broker_account.api_enabled:
        raise_400("브로커 연동이 비활성화되어 취소할 수 없습니다.")

    adapter = KISAdapter(db, broker_account)
    rows = adapter.list_psbl_rvsecncl()
    target = None
    oid = str(order.broker_order_id).strip()
    for r in rows:
        if str(r.get("odno", r.get("ODNO", "")) or "").strip() == oid:
            target = r
            break
    if not target:
        raise_400("정정/취소 가능 주문 목록에서 해당 주문을 찾지 못했습니다.")

    orgno = (target.get("krx_fwdg_ord_orgno") or target.get("KRX_FWDG_ORD_ORGNO") or "").strip()
    if not orgno:
        raise_400("취소에 필요한 KRX_FWDG_ORD_ORGNO를 찾지 못했습니다.")

    adapter.cancel_order(krx_fwdg_ord_orgno=orgno, orgn_odno=oid)
    order.status = OrderStatus.CANCELLED.value
    order.cancelled_at = datetime.utcnow()
    order.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(order)
    return _to_order_dict(order, [])


def list_orders(
    db: Session,
    user_id: str,
    account_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """주문 목록 조회."""
    q = db.query(InvestmentOrder).filter(InvestmentOrder.user_id == user_id)
    if account_id:
        q = q.filter(InvestmentOrder.account_id == account_id)
    if status:
        q = q.filter(InvestmentOrder.status == status)

    orders = q.order_by(InvestmentOrder.requested_at.desc()).limit(limit).all()
    return [
        {
            "id": o.id,
            "ticker": o.ticker,
            "side": o.side,
            "quantity": float(o.quantity),
            "price": float(o.price) if o.price else None,
            "order_type": o.order_type,
            "broker_order_id": o.broker_order_id,
            "status": o.status,
            "requested_at": o.requested_at.isoformat(),
            "filled_at": o.filled_at.isoformat() if o.filled_at else None,
        }
        for o in orders
    ]


def collect_executions(db: Session, user_id: str, order_id: str) -> List[Dict[str, Any]]:
    """브로커에서 체결 내역 조회 후 저장 + 정산 반영."""
    order = db.query(InvestmentOrder).filter(InvestmentOrder.id == order_id, InvestmentOrder.user_id == user_id).first()
    if not order:
        raise_404("주문을 찾을 수 없습니다.")
    if not order.broker_account_id or not order.broker_order_id:
        return []

    broker_account = db.query(BrokerAccount).filter(BrokerAccount.id == order.broker_account_id).first()
    if not broker_account or not broker_account.api_enabled:
        return []

    adapter = KISAdapter(db, broker_account)
    try:
        broker_status = adapter.get_order_status(order.broker_order_id)
    except Exception:
        return []

    order.status = broker_status.get("status", order.status)
    if order.status == OrderStatus.FILLED.value and not order.filled_at:
        order.filled_at = datetime.utcnow()
    order.updated_at = datetime.utcnow()

    executions_payload = broker_status.get("executions") or []

    # 브로커가 execution list를 주지 않는 경우, filled summary로 synthetic execution 1건 생성.
    if not executions_payload:
        filled_qty = Decimal(str(broker_status.get("filled_quantity", 0)))
        avg_price = Decimal(str(broker_status.get("average_price", 0)))
        if filled_qty > 0 and avg_price > 0:
            synthetic_id = f"{order.broker_order_id}:sum:{filled_qty}:{avg_price}"
            executions_payload = [
                {
                    "execution_id": synthetic_id,
                    "quantity": filled_qty,
                    "price": avg_price,
                    "executed_at": datetime.utcnow(),
                    "fee": Decimal("0"),
                }
            ]

    new_rows: list[InvestmentExecution] = []
    for item in executions_payload:
        broker_execution_id = item.get("execution_id")
        if not broker_execution_id:
            continue

        exists = (
            db.query(InvestmentExecution)
            .filter(InvestmentExecution.broker_execution_id == broker_execution_id)
            .first()
        )
        if exists:
            continue

        executed_at = item.get("executed_at") or datetime.utcnow()
        if isinstance(executed_at, str):
            try:
                executed_at = datetime.fromisoformat(executed_at)
            except Exception:
                executed_at = datetime.utcnow()

        row = InvestmentExecution(
            id=f"exe_{uuid.uuid4().hex[:12]}",
            order_id=order.id,
            user_id=user_id,
            broker_execution_id=broker_execution_id,
            executed_quantity=Decimal(str(item.get("quantity", 0))),
            executed_price=Decimal(str(item.get("price", 0))),
            fee=Decimal(str(item.get("fee", 0))) if item.get("fee") is not None else Decimal("0"),
            executed_at=executed_at,
            settled="no",
        )
        db.add(row)
        db.flush()

        _settle_execution(db, order, row)
        new_rows.append(row)

    db.commit()

    return [
        {
            "id": r.id,
            "broker_execution_id": r.broker_execution_id,
            "executed_quantity": float(r.executed_quantity),
            "executed_price": float(r.executed_price),
            "fee": float(r.fee) if r.fee else 0.0,
            "executed_at": r.executed_at.isoformat(),
            "settled": r.settled,
        }
        for r in new_rows
    ]


def get_order_status(db: Session, user_id: str, order_id: str) -> Dict[str, Any]:
    """주문 상태 조회. 조회 시 체결 동기화/정산도 같이 수행."""
    order = db.query(InvestmentOrder).filter(InvestmentOrder.id == order_id, InvestmentOrder.user_id == user_id).first()
    if not order:
        raise_404("주문을 찾을 수 없습니다.")

    # 최신 브로커 상태 반영 + 체결 수집/정산
    collect_executions(db, user_id, order_id)

    db.refresh(order)
    executions = (
        db.query(InvestmentExecution)
        .filter(InvestmentExecution.order_id == order_id)
        .order_by(InvestmentExecution.executed_at.asc())
        .all()
    )
    return _to_order_dict(order, executions)
