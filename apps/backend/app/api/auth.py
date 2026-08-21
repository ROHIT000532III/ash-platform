from __future__ import annotations

import re
from collections import deque
from threading import Lock
from time import monotonic

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel, Field, field_validator

from app.core.dependencies import authentication_service, bearer_scheme
from app.core.database import DatabaseError, UserAlreadyExistsError

router = APIRouter(prefix="/api/auth", tags=["auth"])
USERNAME = re.compile(r"^[A-Za-z0-9_.-]{3,32}$")


class Credentials(BaseModel):
    username: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=12, max_length=256)

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str) -> str:
        value = value.strip()
        if not USERNAME.fullmatch(value):
            raise ValueError("Username must use 3-32 letters, numbers, dots, dashes, or underscores.")
        return value


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict[str, str]


def _response(username: str, user_id: str, token: str) -> AuthResponse:
    return AuthResponse(access_token=token, user={"id": user_id, "username": username})


_auth_rate_limit_lock = Lock()
_auth_rate_limit_buckets: dict[str, deque[float]] = {}
_AUTH_RATE_LIMIT_MAX = 20
_AUTH_RATE_LIMIT_WINDOW = 60


def _rate_limit_auth(request: Request, limit: int = _AUTH_RATE_LIMIT_MAX, window: int = _AUTH_RATE_LIMIT_WINDOW) -> None:
    client_ip = request.client.host if request.client else "unknown"
    now = monotonic()
    with _auth_rate_limit_lock:
        bucket = _auth_rate_limit_buckets.setdefault(client_ip, deque())
        while bucket and bucket[0] <= now - window:
            bucket.popleft()
        if len(bucket) >= limit:
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many authentication requests. Please try again later.")
        bucket.append(now)


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(credentials: Credentials, request: Request) -> AuthResponse:
    _rate_limit_auth(request)
    try:
        user, token = authentication_service.register(credentials.username, credentials.password)
        return _response(user.username, user.id, token)
    except UserAlreadyExistsError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username is already registered.") from error
    except DatabaseError as error:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Authentication storage is unavailable.") from error


@router.post("/login", response_model=AuthResponse)
def login(credentials: Credentials, request: Request) -> AuthResponse:
    _rate_limit_auth(request)
    try:
        result = authentication_service.login(credentials.username, credentials.password)
    except DatabaseError as error:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Authentication storage is unavailable.") from error
    if result is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password.")
    user, token = result
    return _response(user.username, user.id, token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)) -> Response:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication is required.")
    if not authentication_service.logout(credentials.credentials):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication is required.")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
