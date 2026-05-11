from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.config import settings
from app.core.audit_middleware import audit_writes_middleware
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging
from app.core.redis import close_redis
from app.integrations.crm.worker import get_worker
from app.modules.leads.sla_worker import get_sla_worker


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging(debug=settings.app_debug)

    crm_worker = get_worker()
    crm_worker.start()

    sla_worker = get_sla_worker()
    sla_worker.start()

    try:
        yield
    finally:
        await crm_worker.stop()
        await sla_worker.stop()
        await close_redis()


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.app_debug,
        docs_url=f"{settings.api_v1_prefix}/docs",
        redoc_url=f"{settings.api_v1_prefix}/redoc",
        openapi_url=f"{settings.api_v1_prefix}/openapi.json",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Generic audit trail for every successful write — catches the DELETEs and
    # PATCHes that don't have explicit AuditService.log() calls in services.
    app.middleware("http")(audit_writes_middleware)

    register_exception_handlers(app)

    app.include_router(api_router, prefix=settings.api_v1_prefix)

    @app.get("/healthz", include_in_schema=False)
    async def healthz() -> JSONResponse:
        return JSONResponse({"status": "ok", "service": settings.app_name})

    return app


app = create_app()
