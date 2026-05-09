from __future__ import annotations

import traceback

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.core.logging import get_logger

_logger = get_logger("errors")


class AppError(Exception):
    """Base application error."""

    status_code: int = status.HTTP_400_BAD_REQUEST
    code: str = "app_error"
    message: str = "Application error"

    def __init__(self, message: str | None = None, *, code: str | None = None, status_code: int | None = None):
        if message is not None:
            self.message = message
        if code is not None:
            self.code = code
        if status_code is not None:
            self.status_code = status_code
        super().__init__(self.message)


class NotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    code = "not_found"
    message = "Resource not found"


class ConflictError(AppError):
    status_code = status.HTTP_409_CONFLICT
    code = "conflict"
    message = "Conflict"


class UnauthorizedError(AppError):
    status_code = status.HTTP_401_UNAUTHORIZED
    code = "unauthorized"
    message = "Unauthorized"


class ForbiddenError(AppError):
    status_code = status.HTTP_403_FORBIDDEN
    code = "forbidden"
    message = "Forbidden"


class ValidationError(AppError):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    code = "validation_error"
    message = "Validation error"


def _error_response(status_code: int, code: str, message: str, details: object | None = None) -> JSONResponse:
    body: dict = {"error": {"code": code, "message": message}}
    if details is not None:
        body["error"]["details"] = details
    return JSONResponse(status_code=status_code, content=body)


# Uzbek labels for known field paths — keeps user-facing summary readable.
# Add entries here when adding new fields users will see.
_FIELD_LABELS: dict[str, str] = {
    # Auth
    "phone": "Telefon raqam",
    "code": "Tasdiqlash kodi",
    "password": "Parol",
    "email": "Email",
    "full_name": "F.I.Sh.",
    # Applicant profile
    "last_name": "Familiya",
    "first_name": "Ism",
    "other_name": "Otasining ismi",
    "birth_date": "Tug'ilgan sana",
    "gender": "Jinsi",
    "passport_series": "Pasport seriyasi va raqami",
    "pinfl": "JSHSHIR (PINFL)",
    "region_id": "Viloyat",
    "district_id": "Tuman",
    "address": "Manzil",
    "nationality": "Millati",
    "additional_phone": "Qo'shimcha telefon",
    # Diplom
    "university_name": "Muassasa nomi",
    "diplom_series": "Diplom yoki shahodatnoma seriyasi",
    "graduation_year": "Bitirgan yili",
    "specialty": "Mutaxassislik",
    # Application
    "program_id": "Yo'nalish",
    "branch_id": "Filial",
    "education_form_id": "Ta'lim shakli",
    "education_level_id": "Ta'lim darajasi",
    "admission_type": "Qabul turi",
    "diplom_id": "Diplom",
    # Lead
    "source_id": "Manba",
    "stage_id": "Bosqich",
    "assigned_to_id": "Operator",
}


def _humanize_field_path(loc: tuple) -> str:
    """Convert pydantic loc tuple ("body", "address") to "Manzil" or fallback."""
    # Drop the leading "body"/"query"/"path" segment if present.
    parts = [p for p in loc if not isinstance(p, int) and p not in {"body", "query", "path", "header", "cookie"}]
    if not parts:
        return "Maydon"
    leaf = str(parts[-1])
    return _FIELD_LABELS.get(leaf, leaf.replace("_", " ").capitalize())


def _humanize_validation_message(err: dict) -> str:
    """Map pydantic's English error msg to a short Uzbek hint."""
    t = err.get("type", "")
    msg = err.get("msg", "") or ""
    ctx = err.get("ctx") or {}

    if t == "missing":
        return "majburiy"
    if t == "string_too_short":
        n = ctx.get("min_length")
        return f"juda qisqa (kamida {n} belgi)" if n else "juda qisqa"
    if t == "string_too_long":
        n = ctx.get("max_length")
        return f"juda uzun (ko'pi bilan {n} belgi)" if n else "juda uzun"
    if t == "value_error" and "email" in msg.lower():
        return "noto'g'ri email manzili"
    if t == "string_pattern_mismatch":
        return "format noto'g'ri"
    if t == "int_parsing" or t == "float_parsing":
        return "raqam kerak"
    if t == "date_from_datetime_parsing" or "date" in t:
        return "sana noto'g'ri"
    if t == "uuid_parsing" or "uuid" in t:
        return "noto'g'ri identifikator"
    if t == "enum":
        return "qiymat ro'yxatda yo'q"
    if t in {"greater_than", "greater_than_equal"}:
        return f"kichik (≥ {ctx.get('ge') or ctx.get('gt')})"
    if t in {"less_than", "less_than_equal"}:
        return f"katta (≤ {ctx.get('le') or ctx.get('lt')})"
    # Fall back to pydantic's English msg as last resort.
    return msg or "qiymat noto'g'ri"


def _format_validation_summary(errors: list[dict]) -> str:
    """Build a 1-sentence Uzbek summary of all field errors.

    Example: "Familiya: majburiy. Tug'ilgan sana: sana noto'g'ri. (3 ta xato)"
    """
    if not errors:
        return "Validatsiya xatosi"

    parts: list[str] = []
    for err in errors[:3]:  # show up to 3 to keep toast short
        label = _humanize_field_path(err.get("loc", ()))
        msg = _humanize_validation_message(err)
        parts.append(f"{label}: {msg}")

    summary = ". ".join(parts)
    if len(errors) > 3:
        summary += f". (yana {len(errors) - 3} ta xato)"
    return summary


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error_handler(_: Request, exc: AppError) -> JSONResponse:
        return _error_response(exc.status_code, exc.code, exc.message)

    @app.exception_handler(RequestValidationError)
    async def _validation_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
        # Build a human-readable Uzbek summary message from the first few
        # field errors, while keeping the full structured `details` for
        # client-side per-field highlighting.
        errors = exc.errors()
        summary = _format_validation_summary(errors)
        return _error_response(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "validation_error",
            summary,
            details=errors,
        )

    @app.exception_handler(IntegrityError)
    async def _integrity_handler(request: Request, exc: IntegrityError) -> JSONResponse:
        # Surface unique-constraint / FK violations as 409 with a useful message.
        msg = str(getattr(exc, "orig", exc)).splitlines()[0]
        _logger.warning(
            "db.integrity_error",
            path=request.url.path,
            method=request.method,
            error=msg,
        )
        return _error_response(
            status.HTTP_409_CONFLICT,
            "integrity_error",
            f"Ma'lumotlar bazasi cheklovi buzildi: {msg}",
        )

    @app.exception_handler(SQLAlchemyError)
    async def _db_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
        _logger.error(
            "db.error",
            path=request.url.path,
            method=request.method,
            error=str(getattr(exc, "orig", exc)),
            traceback=traceback.format_exc(),
        )
        return _error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "database_error",
            "Ma'lumotlar bazasi xatosi",
        )

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
        _logger.error(
            "internal_error",
            path=request.url.path,
            method=request.method,
            error=str(exc),
            traceback=traceback.format_exc(),
        )
        return _error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "internal_error",
            "Server xatosi",
        )
