from typing import Any, Dict, List, Optional
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from app.core.logging import logger


class AppException(Exception):
    def __init__(
        self,
        message: str,
        code: str = "INTERNAL_ERROR",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[List[Dict[str, Any]]] = None,
    ):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or []
        super().__init__(message)


class ResourceNotFoundError(AppException):
    def __init__(self, message: str = "Resource not found", details: Optional[List[Dict[str, Any]]] = None):
        super().__init__(
            message=message,
            code="NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND,
            details=details,
        )


class UnauthorizedError(AppException):
    def __init__(self, message: str = "Unauthorized access", details: Optional[List[Dict[str, Any]]] = None):
        super().__init__(
            message=message,
            code="UNAUTHORIZED",
            status_code=status.HTTP_401_UNAUTHORIZED,
            details=details,
        )


class ForbiddenError(AppException):
    def __init__(self, message: str = "Forbidden action", details: Optional[List[Dict[str, Any]]] = None):
        super().__init__(
            message=message,
            code="FORBIDDEN",
            status_code=status.HTTP_403_FORBIDDEN,
            details=details,
        )


class ClinicalSafetyError(AppException):
    """Raised when an operation violates Clinical Decision Support guardrails."""
    def __init__(self, message: str = "Clinical safety constraint violation", details: Optional[List[Dict[str, Any]]] = None):
        super().__init__(
            message=message,
            code="CLINICAL_SAFETY_VIOLATION",
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details,
        )


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        request_id = getattr(request.state, "request_id", "unknown")
        logger.warning(
            "AppException [%s] on %s: %s (req_id: %s)",
            exc.code,
            request.url.path,
            exc.message,
            request_id,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "details": exc.details,
                },
                "meta": {
                    "request_id": request_id,
                    "path": request.url.path,
                },
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        request_id = getattr(request.state, "request_id", "unknown")
        errors = []
        for err in exc.errors():
            errors.append({
                "loc": err.get("loc"),
                "msg": err.get("msg"),
                "type": err.get("type"),
            })
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "success": False,
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "The incoming payload failed schema validation.",
                    "details": errors,
                },
                "meta": {
                    "request_id": request_id,
                    "path": request.url.path,
                },
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        request_id = getattr(request.state, "request_id", "unknown")
        logger.error("Unhandled Exception on %s: %s", request.url.path, str(exc), exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "An unexpected error occurred while processing the clinical request.",
                    "details": [],
                },
                "meta": {
                    "request_id": request_id,
                    "path": request.url.path,
                },
            },
        )
