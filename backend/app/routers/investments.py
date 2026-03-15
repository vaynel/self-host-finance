"""Investment routes."""

from fastapi import APIRouter, Depends, Query
from typing import Optional

from app.dependencies import get_current_user, DbSession
from app.models.user import User
from app.schemas.investment import TradeCreate
from app.schemas.common import success_response
from app.services.investment_service import get_holdings, list_trades, create_trade

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
    """Get price history - mock (no external API)."""
    # TODO: integrate external stock API
    return success_response({"ticker": ticker, "prices": []})


@router.post("/trades")
def create_trade_route(req: TradeCreate, current_user: User = Depends(get_current_user), db: DbSession = None):
    """Create buy/sell trade."""
    data = req.model_dump()
    t = create_trade(db, current_user.id, data)
    return success_response(t)
