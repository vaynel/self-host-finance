"""User settings business logic."""

from sqlalchemy.orm import Session

from app.core.exceptions import raise_400
from app.core.token_encryption import encrypt_token, decrypt_token
from app.models.settings import UserSettings


def _validate_discord_webhook_url(url: str) -> None:
    u = url.strip()
    path_after = None
    for p in (
        "https://discord.com/api/webhooks/",
        "https://discordapp.com/api/webhooks/",
    ):
        if u.startswith(p):
            path_after = u[len(p) :].split("?", 1)[0].strip("/")
            break
    if not path_after:
        raise_400(
            "Discord 웹훅 URL은 https://discord.com/api/webhooks/ 로 시작해야 합니다.",
        )
    parts = [x for x in path_after.split("/") if x]
    if len(parts) < 2 or not parts[0].isdigit() or not parts[1]:
        raise_400("Discord 웹훅 URL 형식이 올바르지 않습니다.")


def _mask_webhook_url(url: str) -> str:
    u = url.strip()
    if len(u) <= 24:
        return "(설정됨)"
    return u[:48] + "…" + u[-10:]


def get_settings(db: Session, user_id: str) -> dict:
    """Get or create default settings."""
    s = db.query(UserSettings).filter(UserSettings.user_id == user_id).first()
    if not s:
        s = UserSettings(user_id=user_id)
        db.add(s)
        db.commit()
        db.refresh(s)

    masked = None
    configured = bool(s.discord_webhook_encrypted)
    if s.discord_webhook_encrypted:
        try:
            raw = decrypt_token(s.discord_webhook_encrypted)
            masked = _mask_webhook_url(raw)
        except Exception:
            masked = "(저장값 복호화 실패)"

    return {
        "currency": s.currency,
        "language": s.language,
        "notifications": s.notifications,
        "discord_webhook_configured": configured,
        "discord_webhook_masked": masked,
    }


def update_settings(db: Session, user_id: str, data: dict) -> dict:
    """Update user settings."""
    s = db.query(UserSettings).filter(UserSettings.user_id == user_id).first()
    if not s:
        s = UserSettings(user_id=user_id)
        db.add(s)
        db.commit()
        db.refresh(s)

    payload = dict(data)
    if "discord_webhook_url" in payload:
        raw = payload.pop("discord_webhook_url")
        if raw is None:
            pass
        elif isinstance(raw, str) and not raw.strip():
            s.discord_webhook_encrypted = None
        else:
            url = str(raw).strip()
            _validate_discord_webhook_url(url)
            s.discord_webhook_encrypted = encrypt_token(url)

    for k, v in payload.items():
        if v is not None:
            setattr(s, k, v)
    db.commit()
    db.refresh(s)
    return get_settings(db, user_id)
