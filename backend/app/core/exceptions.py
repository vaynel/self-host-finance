"""Custom exceptions and error response helpers."""

from fastapi import HTTPException


def error_response(status_code: int, message: str, details: list | None = None) -> dict:
    """Build standard error response body."""
    return {
        "success": False,
        "data": None,
        "error": {
            "code": status_code,
            "message": message,
            "details": details or [],
        },
        "meta": None,
    }


def raise_401(message: str = "인증에 실패했습니다."):
    """Raise 401 Unauthorized."""
    raise HTTPException(status_code=401, detail=error_response(401, message))


def raise_403(message: str = "권한이 없습니다."):
    """Raise 403 Forbidden."""
    raise HTTPException(status_code=403, detail=error_response(403, message))


def raise_404(message: str = "리소스를 찾을 수 없습니다."):
    """Raise 404 Not Found."""
    raise HTTPException(status_code=404, detail=error_response(404, message))


def raise_400(message: str = "잘못된 요청입니다.", details: list | None = None):
    """Raise 400 Bad Request."""
    raise HTTPException(status_code=400, detail=error_response(400, message, details))
