from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

try:  # pragma: no cover - optional dependency
    from jose import JWTError, jwt
except ImportError:  # pragma: no cover - executed when jose missing
    JWTError = RuntimeError  # type: ignore[assignment]
    jwt = None  # type: ignore[assignment]

from .config import get_settings


settings = get_settings()
reuseable_oauth = HTTPBearer(auto_error=False)


def verify_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(reuseable_oauth),
) -> str:
    """
    Validates the bearer token supplied with each request.
    Supports either a static API token or signed JWTs using the shared secret.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication credentials",
        )

    token = credentials.credentials
    if token == settings.api_token:
        return token

    if jwt is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="JWT support unavailable; install python-jose or use API token.",
        )

    try:
        payload = jwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
        if payload.get("exp") and datetime.utcnow().timestamp() > payload["exp"]:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expired",
            )
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        ) from exc

    return token


def create_jwt(sub: str) -> str:
    if jwt is None:  # pragma: no cover - depends on optional dependency
        raise RuntimeError(
            "JWT generation unavailable because python-jose is not installed."
        )
    expire = datetime.utcnow() + timedelta(minutes=settings.jwt_exp_minutes)
    payload = {"sub": sub, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
