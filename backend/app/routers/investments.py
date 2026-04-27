"""Investment routes."""

from fastapi import APIRouter, Depends, Query
from typing import Optional

from app.dependencies import get_current_user, DbSession
from app.models.user import User
from app.schemas.investment import TradeCreate, OrderCreate, AutoTradeRuleCreate, AutoTradeRuleUpdate, KISConnectRequest
from app.schemas.auto_trade_global import AutoTradeGlobalRuleCreate, AutoTradeGlobalRuleUpdate
from app.schemas.common import success_response
from app.services.investment_service import (
    get_holdings,
    list_trades,
    create_trade,
    list_price_history,
    sync_holdings_snapshot,
)
from app.services.order_service import create_order, get_order_status, list_orders, collect_executions, cancel_order
from app.services.auto_trade_service import (
    list_rules,
    create_rule,
    update_rule,
    delete_rule,
    list_global_rules,
    create_global_rule,
    update_global_rule,
    delete_global_rule,
    set_auto_trade_enabled,
    list_global_logs,
)
from app.models.auto_trade import AutoTradeRunLog
from app.services.investment_price_updater import refresh_prices_once
from app.services.kis_account_service import connect_kis_account
from app.services.auto_trade_query import list_current_triggers
from decimal import Decimal

router = APIRouter(prefix="/investments", tags=["investments"])


@router.get("/holdings")
def holdings(current_user: User = Depends(get_current_user), db: DbSession = None):
    """Get portfolio holdings."""
    items = get_holdings(db, current_user.id)
    return success_response(items)


@router.get("/trades")
def trades(
    current_user: User = Depends(get_current_user),
    db: DbSession = None,
    ticker: Optional[str] = None,
    action: Optional[str] = None,
    startDate: Optional[str] = None,
    endDate: Optional[str] = None,
):
    """List investment trades."""
    items = list_trades(db, current_user.id, ticker=ticker, action=action, start_date=startDate, end_date=endDate)
    return success_response(items)


@router.get("/prices/{ticker}")
def prices(ticker: str, period: Optional[str] = Query(None), current_user: User = Depends(get_current_user), db: DbSession = None):
    """Get daily price history (from stored daily closes)."""
    items = list_price_history(db, current_user.id, ticker, period=period)
    return success_response(items)


@router.post("/trades")
def create_trade_route(req: TradeCreate, current_user: User = Depends(get_current_user), db: DbSession = None):
    """Create buy/sell trade."""
    data = req.model_dump()
    t = create_trade(db, current_user.id, data)
    return success_response(t)


@router.post("/prices/refresh")
async def refresh_prices_route(
    ticker: Optional[str] = None,
    current_user: User = Depends(get_current_user),
):
    """Manually refresh price for a ticker (or all tickers tracked by the user)."""
    if ticker:
        await refresh_prices_once(tickers=[(current_user.id, ticker)])
    else:
        await refresh_prices_once()
    return success_response({"message": "가격 갱신을 시도했습니다."})


@router.post("/accounts/{account_id}/sync")
def sync_account_snapshot_route(
    account_id: str,
    current_user: User = Depends(get_current_user),
    db: DbSession = None,
):
    """Sync holdings/cash snapshot from broker for one investment account."""
    data = sync_holdings_snapshot(db, current_user.id, account_id)
    return success_response(data)


# ==================== KIS 연동(최소) ====================

@router.post("/accounts/{account_id}/kis/connect")
def kis_connect_route(
    account_id: str,
    req: KISConnectRequest,
    current_user: User = Depends(get_current_user),
    db: DbSession = None,
):
    """Connect KIS: create broker account detail + issue OAuth token + enable api."""
    data = connect_kis_account(db, current_user.id, account_id, req)
    return success_response(data)


# ==================== 주문/체결 API ====================

@router.post("/orders")
def create_order_route(
    req: OrderCreate,
    current_user: User = Depends(get_current_user),
    db: DbSession = None,
):
    """Create investment order (buy/sell)."""
    order = create_order(
        db=db,
        user_id=current_user.id,
        account_id=req.account_id,
        ticker=req.ticker,
        side=req.side,
        quantity=Decimal(str(req.quantity)),
        price=Decimal(str(req.price)) if req.price else None,
        order_type=req.order_type,
    )
    return success_response(order)


@router.get("/orders")
def list_orders_route(
    current_user: User = Depends(get_current_user),
    db: DbSession = None,
    account_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = Query(50, ge=1, le=100),
):
    """List investment orders."""
    orders = list_orders(
        db=db,
        user_id=current_user.id,
        account_id=account_id,
        status=status,
        limit=limit,
    )
    return success_response(orders)


@router.get("/orders/{order_id}")
def get_order_route(
    order_id: str,
    current_user: User = Depends(get_current_user),
    db: DbSession = None,
):
    """Get order status and executions."""
    order = get_order_status(db, current_user.id, order_id)
    return success_response(order)


@router.post("/orders/{order_id}/refresh")
def refresh_order_route(
    order_id: str,
    current_user: User = Depends(get_current_user),
    db: DbSession = None,
):
    """Refresh order status and collect executions from broker."""
    new_executions = collect_executions(db, current_user.id, order_id)
    order = get_order_status(db, current_user.id, order_id)
    return success_response({
        "order": order,
        "new_executions": new_executions,
    })


@router.post("/orders/{order_id}/cancel")
def cancel_order_route(
    order_id: str,
    current_user: User = Depends(get_current_user),
    db: DbSession = None,
):
    """Cancel an existing order (best-effort)."""
    order = cancel_order(db, current_user.id, order_id)
    return success_response(order)


# ==================== 자동매매 규칙 API ====================

@router.get("/rules")
def list_rules_route(
    current_user: User = Depends(get_current_user),
    db: DbSession = None,
):
    items = list_rules(db, current_user.id)
    return success_response(items)


@router.post("/rules")
def create_rule_route(
    req: AutoTradeRuleCreate,
    current_user: User = Depends(get_current_user),
    db: DbSession = None,
):
    item = create_rule(db, current_user.id, req.model_dump())
    return success_response(item)


@router.put("/rules/{rule_id}")
def update_rule_route(
    rule_id: str,
    req: AutoTradeRuleUpdate,
    current_user: User = Depends(get_current_user),
    db: DbSession = None,
):
    item = update_rule(db, current_user.id, rule_id, req.model_dump(exclude_unset=True))
    return success_response(item)


@router.delete("/rules/{rule_id}")
def delete_rule_route(
    rule_id: str,
    current_user: User = Depends(get_current_user),
    db: DbSession = None,
):
    delete_rule(db, current_user.id, rule_id)
    return success_response({"deleted": True})


@router.post("/accounts/{account_id}/auto-trade/enable")
def enable_auto_trade_route(
    account_id: str,
    current_user: User = Depends(get_current_user),
    db: DbSession = None,
):
    data = set_auto_trade_enabled(db, current_user.id, account_id, True)
    return success_response(data)


@router.post("/accounts/{account_id}/auto-trade/disable")
def disable_auto_trade_route(
    account_id: str,
    current_user: User = Depends(get_current_user),
    db: DbSession = None,
):
    data = set_auto_trade_enabled(db, current_user.id, account_id, False)
    return success_response(data)


@router.get("/rules/logs")
def list_rule_logs_route(
    current_user: User = Depends(get_current_user),
    db: DbSession = None,
    limit: int = Query(50, ge=1, le=200),
):
    ticker_logs = [
        {
            "id": r.id,
            "rule_id": r.rule_id,
            "account_id": r.account_id,
            "ticker": r.ticker,
            "status": r.status,
            "reason": r.reason,
            "order_id": r.order_id,
            "created_at": r.created_at.isoformat(),
        }
        for r in (
            db.query(AutoTradeRunLog)
            .filter(AutoTradeRunLog.user_id == current_user.id)
            .order_by(AutoTradeRunLog.created_at.desc())
            .limit(limit)
            .all()
        )
    ]

    global_logs = list_global_logs(db, current_user.id, limit=limit)

    # ISO 문자열 기준 정렬(간단 구현)
    merged = sorted(ticker_logs + global_logs, key=lambda x: x["created_at"], reverse=True)[:limit]
    return success_response(merged)


@router.get("/rules/triggers")
def list_rule_triggers_route(
    current_user: User = Depends(get_current_user),
    db: DbSession = None,
):
    items = list_current_triggers(db, current_user.id)
    return success_response(items)


# ==================== 글로벌 룰(전 종목) API ====================


@router.get("/rules/global")
def list_global_rules_route(
    current_user: User = Depends(get_current_user),
    db: DbSession = None,
):
    items = list_global_rules(db, current_user.id)
    return success_response(items)


@router.post("/rules/global")
def create_global_rule_route(
    req: AutoTradeGlobalRuleCreate,
    current_user: User = Depends(get_current_user),
    db: DbSession = None,
):
    item = create_global_rule(db, current_user.id, req.model_dump())
    return success_response(item)


@router.put("/rules/global/{rule_id}")
def update_global_rule_route(
    rule_id: str,
    req: AutoTradeGlobalRuleUpdate,
    current_user: User = Depends(get_current_user),
    db: DbSession = None,
):
    item = update_global_rule(db, current_user.id, rule_id, req.model_dump(exclude_unset=True))
    return success_response(item)


@router.delete("/rules/global/{rule_id}")
def delete_global_rule_route(
    rule_id: str,
    current_user: User = Depends(get_current_user),
    db: DbSession = None,
):
    delete_global_rule(db, current_user.id, rule_id)
    return success_response({"deleted": True})
