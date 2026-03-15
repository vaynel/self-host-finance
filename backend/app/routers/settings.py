"""Settings routes."""

from fastapi import APIRouter, Depends

from app.dependencies import get_current_user, DbSession
from app.models.user import User
from app.schemas.settings import SettingsUpdate, SettingsResponse
from app.schemas.common import success_response
from app.services.settings_service import get_settings, update_settings

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("")
def get_user_settings(current_user: User = Depends(get_current_user), db: DbSession = None):
    """Get user settings."""
    data = get_settings(db, current_user.id)
    return success_response(data)


@router.put("")
def update_user_settings(req: SettingsUpdate, current_user: User = Depends(get_current_user), db: DbSession = None):
    """Update user settings."""
    data = {k: v for k, v in req.model_dump().items() if v is not None}
    if not data:
        s = get_settings(db, current_user.id)
        return success_response(s)
    s = update_settings(db, current_user.id, data)
    return success_response(s)
