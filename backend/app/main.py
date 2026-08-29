"""影海拾光 FastAPI 入口。"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from loguru import logger

from app.api.routes import auth, capsules, extractions, graph
from app.core.config import get_settings
from app.core.database import SessionLocal
from app.schemas.response import BizError, ok
from app.workers.extraction_runner import recover_stale_tasks


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 种子账号（dev），供 H5 登录联调；生产改掉 YHSG_BOOTSTRAP_PASSWORD
    from app.api.routes.auth import ensure_bootstrap_user
    from app.core.database import SessionLocal as _S

    try:
        with _S() as db:
            ensure_bootstrap_user(db)
    except Exception as exc:  # noqa: BLE001 —— DB 未就绪不阻塞启动
        logger.error("bootstrap user skipped: {}", exc)

    # 启动自愈：上次进程中断留下的中间态任务置 failed（DATABASE.md §4）
    try:
        n = recover_stale_tasks(SessionLocal)
        if n:
            logger.warning("recovered {} stale tasks", n)
    except Exception as exc:  # noqa: BLE001 —— DB 未就绪不阻塞启动
        logger.error("stale task recovery skipped: {}", exc)
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)

    app.include_router(extractions.router, prefix="/api/v1")
    app.include_router(capsules.router, prefix="/api/v1")
    app.include_router(graph.router, prefix="/api/v1")
    app.include_router(auth.router, prefix="/api/v1")

    @app.get("/health", tags=["meta"])
    def health():
        return ok({"status": "up", "app": settings.app_name})

    @app.exception_handler(BizError)
    def biz_handler(_: Request, exc: BizError):
        return JSONResponse(
            status_code=exc.status_code,
            content={"code": exc.biz_code, "message": exc.detail, "data": None},
        )

    @app.exception_handler(RequestValidationError)
    def validation_handler(_: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=422,
            content={"code": 1001, "message": "invalid parameter", "data": exc.errors()},
        )

    return app


app = create_app()
