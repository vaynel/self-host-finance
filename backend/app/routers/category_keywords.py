"""Category keywords management routes."""

from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
from pydantic import BaseModel

from app.dependencies import get_current_user, DbSession
from app.models.user import User
from app.models.category_keyword import CategoryKeyword
from app.schemas.common import success_response
from app.core.security import create_txn_id

router = APIRouter(prefix="/category-keywords", tags=["category-keywords"])


class CategoryKeywordCreate(BaseModel):
    category: str
    keyword: str
    priority: Optional[str] = "normal"  # high, normal, low


class CategoryKeywordUpdate(BaseModel):
    category: Optional[str] = None
    keyword: Optional[str] = None
    priority: Optional[str] = None


@router.get("")
def list_keywords(
    category: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: DbSession = None,
):
    """List all category keywords for the user."""
    query = db.query(CategoryKeyword).filter(CategoryKeyword.user_id == current_user.id)
    if category:
        query = query.filter(CategoryKeyword.category == category)
    
    keywords = query.order_by(
        CategoryKeyword.category,
        CategoryKeyword.priority.desc(),
        CategoryKeyword.keyword
    ).all()
    
    result = {}
    for kw in keywords:
        if kw.category not in result:
            result[kw.category] = []
        result[kw.category].append({
            "id": kw.id,
            "keyword": kw.keyword,
            "priority": kw.priority,
            "created_at": kw.created_at.isoformat() if kw.created_at else None,
        })
    
    return success_response(result)


@router.post("")
def create_keyword(
    data: CategoryKeywordCreate,
    current_user: User = Depends(get_current_user),
    db: DbSession = None,
):
    """Create a new category keyword."""
    # Check if keyword already exists for this user and category
    existing = db.query(CategoryKeyword).filter(
        CategoryKeyword.user_id == current_user.id,
        CategoryKeyword.category == data.category,
        CategoryKeyword.keyword.ilike(data.keyword)
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="이미 존재하는 키워드입니다.")
    
    keyword = CategoryKeyword(
        id=create_txn_id(),
        user_id=current_user.id,
        category=data.category,
        keyword=data.keyword,
        priority=data.priority or "normal",
    )
    db.add(keyword)
    db.commit()
    db.refresh(keyword)
    
    return success_response({
        "id": keyword.id,
        "category": keyword.category,
        "keyword": keyword.keyword,
        "priority": keyword.priority,
    })


@router.put("/{keyword_id}")
def update_keyword(
    keyword_id: str,
    data: CategoryKeywordUpdate,
    current_user: User = Depends(get_current_user),
    db: DbSession = None,
):
    """Update a category keyword."""
    keyword = db.query(CategoryKeyword).filter(
        CategoryKeyword.id == keyword_id,
        CategoryKeyword.user_id == current_user.id
    ).first()
    
    if not keyword:
        raise HTTPException(status_code=404, detail="키워드를 찾을 수 없습니다.")
    
    if data.category is not None:
        keyword.category = data.category
    if data.keyword is not None:
        keyword.keyword = data.keyword
    if data.priority is not None:
        keyword.priority = data.priority
    
    db.commit()
    db.refresh(keyword)
    
    return success_response({
        "id": keyword.id,
        "category": keyword.category,
        "keyword": keyword.keyword,
        "priority": keyword.priority,
    })


@router.delete("/{keyword_id}")
def delete_keyword(
    keyword_id: str,
    current_user: User = Depends(get_current_user),
    db: DbSession = None,
):
    """Delete a category keyword."""
    keyword = db.query(CategoryKeyword).filter(
        CategoryKeyword.id == keyword_id,
        CategoryKeyword.user_id == current_user.id
    ).first()
    
    if not keyword:
        raise HTTPException(status_code=404, detail="키워드를 찾을 수 없습니다.")
    
    db.delete(keyword)
    db.commit()
    
    return success_response({"message": "키워드가 삭제되었습니다."})


@router.get("/categories")
def list_categories(
    current_user: User = Depends(get_current_user),
    db: DbSession = None,
):
    """List all unique categories that have keywords."""
    categories = db.query(CategoryKeyword.category).filter(
        CategoryKeyword.user_id == current_user.id
    ).distinct().all()
    
    return success_response([cat[0] for cat in categories])
