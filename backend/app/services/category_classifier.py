"""Category classification service using keywords from database."""

from sqlalchemy.orm import Session
from app.models.category_keyword import CategoryKeyword


def get_category_keywords(db: Session, user_id: str) -> dict[str, list[str]]:
    """Get all category keywords for a user, grouped by category."""
    keywords = db.query(CategoryKeyword).filter(
        CategoryKeyword.user_id == user_id
    ).order_by(
        CategoryKeyword.priority.desc(),
        CategoryKeyword.keyword
    ).all()
    
    result: dict[str, list[str]] = {}
    for kw in keywords:
        if kw.category not in result:
            result[kw.category] = []
        result[kw.category].append(kw.keyword.lower())
    
    return result


def auto_classify_category(
    db: Session,
    user_id: str,
    description: str,
    amount: float = 0
) -> str:
    """Auto-classify category based on description and amount."""
    if not description:
        return "기타"
    
    # Get user's category keywords
    category_keywords = get_category_keywords(db, user_id)
    
    desc_lower = description.lower()
    
    # Check high priority keywords first
    high_priority_matches = []
    for category, keywords in category_keywords.items():
        for keyword in keywords:
            if keyword in desc_lower:
                # Check if this keyword has high priority
                kw_obj = db.query(CategoryKeyword).filter(
                    CategoryKeyword.user_id == user_id,
                    CategoryKeyword.category == category,
                    CategoryKeyword.keyword.ilike(f"%{keyword}%")
                ).first()
                if kw_obj and kw_obj.priority == "high":
                    high_priority_matches.append((category, keyword))
    
    if high_priority_matches:
        # Return the first high priority match
        return high_priority_matches[0][0]
    
    # Check all keywords
    for category, keywords in category_keywords.items():
        for keyword in keywords:
            if keyword in desc_lower:
                return category
    
    # Amount-based fallback
    if amount >= 500000:
        return "주거"  # Large amounts are likely housing expenses
    
    # Default
    return "기타"


def auto_detect_type(amount: float, description: str) -> str:
    """Auto-detect transaction type (income/expense) based on amount and description."""
    # 1. Amount sign based
    if amount < 0:
        return "expense"
    elif amount > 0:
        # Check description for income keywords
        income_keywords = ["급여", "월급", "배당", "이자", "환급", "보너스", "수입", "입금", "적립"]
        desc_lower = description.lower()
        if any(kw in desc_lower for kw in income_keywords):
            return "income"
        # Default to expense for positive amounts (most transactions are expenses)
        return "expense"
    
    # 2. Description keyword based (if amount is 0 or unclear)
    income_keywords = ["급여", "월급", "배당", "이자", "환급", "보너스", "수입"]
    expense_keywords = ["결제", "출금", "이체", "수수료", "지출", "승인"]
    
    desc_lower = description.lower()
    if any(kw in desc_lower for kw in income_keywords):
        return "income"
    elif any(kw in desc_lower for kw in expense_keywords):
        return "expense"
    
    # Default
    return "expense"
