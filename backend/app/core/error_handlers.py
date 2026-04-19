import uuid
from collections.abc import Callable, Coroutine
from typing import Any

import structlog
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from app.core.exceptions import AppBaseException

logger = structlog.get_logger(__name__)


def _error_response(
    request: Request,
    status_code: int,
    error: str,
    message: str,
    details: object = None,
) -> JSONResponse:
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    return JSONResponse(
        status_code=status_code,
        content={
            "error": error,
            "message": message,
            "details": details,
            "request_id": request_id,
        },
    )

def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppBaseException)
    async def app_exception_handler(
        request: Request, exc: AppBaseException
    ) -> JSONResponse:
        logger.warning(
            "application_error",
            error=exc.error,
            message=exc.message,
            status_code=exc.status_code,
            path=request.url.path,
        )
        return _error_response(request, exc.status_code, exc.error, exc.message)

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        logger.warning("validation_error", errors=exc.errors(), path=request.url.path)
        return _error_response(
            request,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "validation_error",
            "Request validation failed",
            exc.errors(),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        logger.exception("unhandled_exception", path=request.url.path)
        return _error_response(
            request,
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "internal_error",
            "An unexpected error occurred",
        )
