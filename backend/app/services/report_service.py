"""Report/analytics business logic."""

from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session
from sqlalchemy import func, extract, case

from app.models.transaction import Transaction


def monthly_summary(db: Session, user_id: str, year: int | None = None) -> list[dict]:
    """Monthly income/expense/savings summary."""
    y = year or date.today().year
    month_expr = func.to_char(Transaction.date, "YYYY-MM")
    rows = (
        db.query(
            month_expr.label("month"),
            func.sum(case((Transaction.type == "income", Transaction.amount), else_=0)).label("income"),
            func.sum(case((Transaction.type == "expense", func.abs(Transaction.amount)), else_=0)).label("expense"),
        )
        .filter(Transaction.user_id == user_id, extract("year", Transaction.date) == y)
        .group_by(month_expr)
        .order_by(month_expr)
        .all()
    )
    result = []
    for r in rows:
        income = float(r.income or 0)
        expense = float(r.expense or 0)
        savings = income - expense
        rate = (savings / income * 100) if income else 0
        result.append({
            "month": r.month,
            "income": round(income, 0),
            "expense": round(expense, 0),
            "savings": round(savings, 0),
            "savingsRate": round(rate, 1),
        })
    return result


def category_spending(db: Session, user_id: str, month: str | None = None) -> list[dict]:
    """Category-wise spending for a month."""
    m = month or date.today().strftime("%Y-%m")
    y, mon = int(m[:4]), int(m[5:7])
    rows = (
        db.query(Transaction.category, func.sum(func.abs(Transaction.amount)).label("total"))
        .filter(
            Transaction.user_id == user_id,
            Transaction.type == "expense",
            extract("year", Transaction.date) == y,
            extract("month", Transaction.date) == mon,
        )
        .group_by(Transaction.category)
        .all()
    )
    return [{"category": r.category, "amount": round(float(r.total), 0)} for r in rows]
