from contextlib import asynccontextmanager
import logging
import time

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.database import engine

logger = logging.getLogger("api")
settings = get_settings()
if hasattr(status, "HTTP_422_UNPROCESSABLE_CONTENT"):
    HTTP_422_STATUS = status.HTTP_422_UNPROCESSABLE_CONTENT
else:
    HTTP_422_STATUS = 422


@asynccontextmanager
async def lifespan(_: FastAPI):
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = round(time.time() - start, 3)
    logger.info(
        f"{request.method} {request.url.path} -> {response.status_code} ({duration}s)"
    )
    return response


app.include_router(api_router, prefix=settings.API_V1_PREFIX)


def _error_code_from_status(status_code: int) -> str:
    mapping = {
        status.HTTP_400_BAD_REQUEST: "VALIDATION_ERROR",
        status.HTTP_401_UNAUTHORIZED: "UNAUTHORIZED",
        status.HTTP_403_FORBIDDEN: "FORBIDDEN",
        status.HTTP_404_NOT_FOUND: "NOT_FOUND",
        status.HTTP_409_CONFLICT: "CONFLICT",
        HTTP_422_STATUS: "UNPROCESSABLE_ENTITY",
        status.HTTP_429_TOO_MANY_REQUESTS: "RATE_LIMITED",
        status.HTTP_500_INTERNAL_SERVER_ERROR: "INTERNAL_ERROR",
    }
    return mapping.get(status_code, "INTERNAL_ERROR")


def _error_response(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "error",
            "error": {
                "code": code,
                "message": message,
            },
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    message = "Request validation failed"
    if exc.errors():
        message = f"Request validation failed: {exc.errors()[0].get('msg', 'invalid input')}"

    return _error_response(
        status_code=status.HTTP_400_BAD_REQUEST,
        code="VALIDATION_ERROR",
        message=message,
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(_: Request, exc: HTTPException) -> JSONResponse:
    if isinstance(exc.detail, dict):
        code = str(exc.detail.get("code", _error_code_from_status(exc.status_code)))
        message = str(exc.detail.get("message", "Request failed"))
        return _error_response(exc.status_code, code, message)

    return _error_response(
        status_code=exc.status_code,
        code=_error_code_from_status(exc.status_code),
        message=str(exc.detail) if exc.detail else "Request failed",
    )
