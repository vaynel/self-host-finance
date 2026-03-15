"""User settings business logic."""

from sqlalchemy.orm import Session

from app.models.settings import UserSettings


def get_settings(db: Session, user_id: str) -> dict:
    """Get or create default settings."""
    s = db.query(UserSettings).filter(UserSettings.user_id == user_id).first()
    if not s:
        s = UserSettings(user_id=user_id)
        db.add(s)
        db.commit()
        db.refresh(s)
    return {
        "currency": s.currency,
        "language": s.language,
        "notifications": s.notifications,
    }


def update_settings(db: Session, user_id: str, data: dict) -> dict:
    """Update user settings."""
    s = db.query(UserSettings).filter(UserSettings.user_id == user_id).first()
    if not s:
        s = UserSettings(user_id=user_id)
        db.add(s)
        db.commit()
        db.refresh(s)
    for k, v in data.items():
        if v is not None:
            setattr(s, k, v)
    db.commit()
    db.refresh(s)
    return get_settings(db, user_id)
