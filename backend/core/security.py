"""
core/security.py

JWT validation + multi-tenant auth dependency.

Design rules:
- tenant_id is ALWAYS extracted from the JWT — never from URL or request body.
- The Supabase JWT contains: sub (user_id), tenant_id, email, role.
- Every protected route uses `Depends(get_current_tenant)` to enforce this.
- A missing or invalid token returns 401. An inactive tenant returns 403.
"""

import logging
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import settings
from backend.core.database import get_db

logger = logging.getLogger(__name__)

# FastAPI security scheme — expects "Authorization: Bearer <token>"
bearer_scheme = HTTPBearer(auto_error=True)


def decode_jwt(token: str) -> dict:
    """
    Decode and verify a Supabase JWT.
    Raises JWTError if the token is invalid or expired.
    """
    return jwt.decode(
        token,
        settings.SUPABASE_JWT_SECRET,
        algorithms=["HS256"],
        options={"verify_aud": False},  # Supabase doesn't enforce aud by default
    )


async def get_current_tenant(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
):
    """
    FastAPI dependency for all protected routes.

    1. Extracts Bearer token from Authorization header.
    2. Decodes and validates the JWT.
    3. Pulls tenant_id and user_id from the payload.
    4. Loads the Tenant from DB and verifies it is active.
    5. Returns the Tenant ORM object.

    Raises:
        401 — if token is missing, invalid, or expired.
        403 — if tenant is not found or is inactive.
    """
    from backend.models.tenant import Tenant  # local import to avoid circular deps

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token is invalid or has expired.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_jwt(credentials.credentials)
        user_id: str = payload.get("sub")
        tenant_id: str = payload.get("tenant_id")

        if not user_id or not tenant_id:
            logger.warning(
                "jwt_missing_claims",
                extra={"user_id": user_id, "tenant_id": tenant_id},
            )
            raise credentials_exception

    except JWTError as exc:
        logger.warning("jwt_decode_failed", extra={"error": str(exc)})
        raise credentials_exception

    # Load tenant from DB — always verify tenant exists and is active
    tenant = await db.get(Tenant, UUID(tenant_id))
    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant not found.",
        )

    if not tenant.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant account is inactive. Please contact support.",
        )

    logger.debug(
        "tenant_authenticated",
        extra={"tenant_id": str(tenant.id), "user_id": user_id},
    )

    return tenant


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> str:
    """
    Lightweight dependency that only returns the user_id from the token.
    Use this when you need the user identity but not the full Tenant object.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token is invalid or has expired.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_jwt(credentials.credentials)
        user_id: str = payload.get("sub")
        if not user_id:
            raise credentials_exception
        return user_id
    except JWTError:
        raise credentials_exception
