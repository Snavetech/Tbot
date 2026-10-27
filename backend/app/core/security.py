"""
Security and access control utilities
"""
from typing import Optional
from fastapi import Header, HTTPException, status
from backend.app.config import settings


def verify_control_access(x_api_token: Optional[str] = Header(None, alias="X-API-Token")):
    """
    Validates control endpoint access.
    If AUTH_API_TOKEN is set in settings, requires matching token.
    Otherwise allows localhost requests during local development.
    """
    if settings.AUTH_API_TOKEN:
        if not x_api_token or x_api_token != settings.AUTH_API_TOKEN:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unauthorized: Invalid or missing X-API-Token header for trading control"
            )
    return True
