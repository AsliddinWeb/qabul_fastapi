from __future__ import annotations

from fastapi import APIRouter, Depends, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db, get_redis_client
from app.core.schemas import MessageResponse
from app.modules.auth.schemas import (
    LoginResponse,
    OtpRequest,
    OtpRequestResponse,
    OtpVerify,
    RefreshRequest,
    StaffLogin,
    TokenPair,
)
from app.modules.auth.service import AuthService

router = APIRouter()


def _service(
    session: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis_client),
) -> AuthService:
    return AuthService(session, redis)


@router.post(
    "/otp/request",
    response_model=OtpRequestResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Send an OTP code to the given phone",
)
async def request_otp(payload: OtpRequest, svc: AuthService = Depends(_service)) -> OtpRequestResponse:
    return await svc.request_otp(payload)


@router.post(
    "/otp/verify",
    response_model=LoginResponse,
    summary="Exchange OTP code for an access/refresh token pair",
)
async def verify_otp(payload: OtpVerify, svc: AuthService = Depends(_service)) -> LoginResponse:
    return await svc.verify_otp(payload)


@router.post(
    "/login",
    response_model=LoginResponse,
    summary="Staff (non-applicant) password login",
)
async def staff_login(payload: StaffLogin, svc: AuthService = Depends(_service)) -> LoginResponse:
    return await svc.staff_login(payload)


@router.post("/refresh", response_model=TokenPair, summary="Rotate refresh token")
async def refresh(payload: RefreshRequest, svc: AuthService = Depends(_service)) -> TokenPair:
    return await svc.refresh(payload)


@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="Revoke a refresh token",
)
async def logout(payload: RefreshRequest, svc: AuthService = Depends(_service)) -> MessageResponse:
    await svc.logout(payload.refresh_token)
    return MessageResponse(message="logged_out")
