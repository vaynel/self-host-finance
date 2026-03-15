"""Common response schemas."""

from typing import Any, Optional
from pydantic import BaseModel


def success_response(data: Any, meta: Optional[dict] = None) -> dict:
    """Build standard success response."""
    return {
        "success": True,
        "data": data,
        "error": None,
        "meta": meta,
    }


class MetaSchema(BaseModel):
    page: int = 1
    limit: int = 20
    total: int = 0
