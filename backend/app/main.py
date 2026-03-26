"""FinFlow API application."""

import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import get_settings
from app.routers import auth, transactions, accounts, investments, reports, upload, settings as settings_router, category_keywords, parsing_strategies
from app.services.investment_price_updater import start_investment_price_updater_if_needed
from app.services.order_status_scheduler import start_order_status_scheduler_if_needed
from app.services.auto_trade_evaluator import start_auto_trade_evaluator_if_needed
from app.services.kis_token_refresher import start_kis_token_refresher_if_needed

logger = logging.getLogger("finflow.debug")
logging.basicConfig(level=logging.INFO)
# SQLAlchemy가 개별 쿼리/파라미터를 로그로 출력하는 것을 줄이기 위해 레벨을 낮춥니다.
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy").setLevel(logging.WARNING)

_config = get_settings()

app = FastAPI(
    title="FinFlow API",
    description="개인 재무 관리 플랫폼 API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)


@app.on_event("startup")
def on_startup() -> None:
    # Background investment price updater (5~10분 주기) - 요청에 무관하게 시세를 갱신합니다.
    start_investment_price_updater_if_needed()
    # Background order status polling (1분 주기) - pending/partially_filled 주문의 체결/정산 반영
    start_order_status_scheduler_if_needed()
    # Background KIS token refresher (만료 시점 자동 재발급)
    start_kis_token_refresher_if_needed()
    # Background auto-trade evaluator (alert-only | auto-sell by rules)
    # If Celery is enabled, Celery beat/worker will handle sync+evaluation.
    if not _config.celery_enabled:
        start_auto_trade_evaluator_if_needed()
    else:
        logger.info("Celery enabled -> skip FastAPI auto-trade evaluator startup")

# Debug middleware (클래스 먼저 정의)
class DebugMiddleware(BaseHTTPMiddleware):
    """디버그용: 모든 요청/응답 로깅"""

    async def dispatch(self, request: Request, call_next):
        method = request.method
        path = request.url.path
        origin = request.headers.get("origin", "(none)")
        acrm = request.headers.get("access-control-request-method", "(none)")
        acrh = request.headers.get("access-control-request-headers", "(none)")
        logger.info(
            "[DEBUG REQ] %s %s | Origin: %s | AC-Request-Method: %s | AC-Request-Headers: %s",
            method, path, origin, acrm, acrh,
        )
        try:
            response = await call_next(request)
            logger.info("[DEBUG RES] %s %s -> %d", method, path, response.status_code)
            return response
        except Exception as e:
            logger.exception("[DEBUG EXC] %s %s -> %s", method, path, e)
            raise


# CORS
origins = [o.strip() for o in _config.cors_origin.split(",") if o.strip()]

# 개발 환경에서는 접속 IP(로컬/사설망)가 바뀌기 쉬워 CORS로 인해 화면이 비정상(무한 로딩/깜박임)처럼 보이는 케이스가 잦습니다.
# 토큰은 Authorization 헤더로 전달하므로(쿠키 기반 아님) dev에서는 credentials 없이 모든 Origin을 허용합니다.
if _config.env == "development":
    logger.info("CORS (dev) allow_origin_regex: .* (allow_credentials=False)")
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=".*",
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
    )
else:
    logger.info("CORS allow_origins: %s", origins)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
    )
app.add_middleware(DebugMiddleware)


def error_body(status_code: int, message: str, details: list | None = None) -> dict:
    return {
        "success": False,
        "data": None,
        "error": {"code": status_code, "message": message, "details": details or []},
        "meta": None,
    }


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    logger.warning("[DEBUG HTTP] %s %s -> %d %s", request.method, request.url.path, exc.status_code, exc.detail)
    body = exc.detail if isinstance(exc.detail, dict) else error_body(exc.status_code, str(exc.detail))
    return JSONResponse(status_code=exc.status_code, content=body)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    details = [f"{e['loc'][-1]}: {e['msg']}" for e in exc.errors()]
    logger.warning(
        "[DEBUG 400] RequestValidationError %s %s | details=%s",
        request.method, request.url.path, details,
    )
    return JSONResponse(
        status_code=400,
        content=error_body(400, "유효성 검증 실패", details),
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    if hasattr(exc, "status_code") and hasattr(exc, "detail"):
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.detail if isinstance(exc.detail, dict) else error_body(exc.status_code, str(exc.detail)),
        )
    return JSONResponse(status_code=500, content=error_body(500, "서버 내부 오류"))


# Routers under /v1
app.include_router(auth.router, prefix="/v1")
app.include_router(transactions.router, prefix="/v1")
app.include_router(accounts.router, prefix="/v1")
app.include_router(investments.router, prefix="/v1")
app.include_router(reports.router, prefix="/v1")
app.include_router(upload.router, prefix="/v1")
app.include_router(settings_router.router, prefix="/v1")
app.include_router(category_keywords.router, prefix="/v1")
app.include_router(parsing_strategies.router, prefix="/v1")


@app.get("/health")
def health():
    """Health check."""
    return {"status": "ok"}
