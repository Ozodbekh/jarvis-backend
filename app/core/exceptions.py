from typing import Any, ClassVar

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logging import get_logger

logger = get_logger("app.errors")

ERROR_MESSAGES: dict[str, str] = {
    "INTERNAL_ERROR": "Something went wrong.",
    "VALIDATION_ERROR": "The request is not valid.",
    "NOT_FOUND": "Not found.",
    "METHOD_NOT_ALLOWED": "Method not allowed.",
    "HTTP_ERROR": "The request failed.",
}

HTTP_STATUS_CODES: dict[int, str] = {
    status.HTTP_404_NOT_FOUND: "NOT_FOUND",
    status.HTTP_405_METHOD_NOT_ALLOWED: "METHOD_NOT_ALLOWED",
}


class AppError(Exception):
    status_code: ClassVar[int] = status.HTTP_500_INTERNAL_SERVER_ERROR

    def __init__(self, code: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(code)
        self.code = code
        self.details = details or {}

    @property
    def message(self) -> str:
        return ERROR_MESSAGES.get(self.code, ERROR_MESSAGES["HTTP_ERROR"])


class BadRequestError(AppError):
    status_code = status.HTTP_400_BAD_REQUEST


class NotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND


class ConflictError(AppError):
    status_code = status.HTTP_409_CONFLICT


class UpstreamError(AppError):
    status_code = status.HTTP_502_BAD_GATEWAY


class ServiceUnavailableError(AppError):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE


def error_body(code: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "code": code,
        "message": ERROR_MESSAGES.get(code, ERROR_MESSAGES["HTTP_ERROR"]),
        "details": details or {},
    }


async def _app_error(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, AppError)
    logger.info("app_error", code=exc.code, status=exc.status_code, path=request.url.path)
    return JSONResponse(error_body(exc.code, exc.details), status_code=exc.status_code)


async def _validation_error(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)
    errors = [{"loc": list(error["loc"]), "msg": error["msg"], "type": error["type"]} for error in exc.errors()]
    return JSONResponse(
        error_body("VALIDATION_ERROR", {"errors": errors}),
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
    )


async def _http_error(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, StarletteHTTPException)
    code = HTTP_STATUS_CODES.get(exc.status_code, "HTTP_ERROR")
    return JSONResponse(error_body(code), status_code=exc.status_code, headers=exc.headers)


async def _unhandled_error(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("unhandled_error", path=request.url.path)
    return JSONResponse(error_body("INTERNAL_ERROR"), status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, _app_error)
    app.add_exception_handler(RequestValidationError, _validation_error)
    app.add_exception_handler(StarletteHTTPException, _http_error)
    app.add_exception_handler(Exception, _unhandled_error)
