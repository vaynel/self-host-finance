"""Report routes."""

from fastapi import APIRouter, Depends, Query
from typing import Optional

from app.dependencies import get_current_user, DbSession
from app.models.user import User
from app.schemas.common import success_response
from app.services.report_service import monthly_summary, category_spending

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/monthly-summary")
def monthly(year: Optional[int] = Query(None), current_user: User = Depends(get_current_user), db: DbSession = None):
    """Monthly income/expense/savings summary."""
    items = monthly_summary(db, current_user.id, year=year)
    return success_response(items)


@router.get("/category-spending")
def category(month: Optional[str] = Query(None), current_user: User = Depends(get_current_user), db: DbSession = None):
    """Category-wise spending for month (YYYY-MM)."""
    items = category_spending(db, current_user.id, month=month)
    return success_response(items)
