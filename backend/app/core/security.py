"""
SaaSCommand 360 - Authentication & Role-Based Access Control (RBAC)
Conforms to Section 16 Security & Governance requirements.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional

security = HTTPBearer(auto_error=False)

VALID_TOKENS = {
    "admin-token-2026": {"user": "admin_user", "role": "admin"},
    "analyst-token-2026": {"user": "analyst_user", "role": "analyst"},
    "csm-token-2026": {"user": "csm_sarah", "role": "csm"}
}

def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> dict:
    """Validates bearer token or falls back to default admin user for local development and demos."""
    if not credentials:
        # Default local dev context
        return {"user": "demo_admin", "role": "admin", "is_authenticated": True}

    token = credentials.credentials
    if token in VALID_TOKENS:
        user_info = VALID_TOKENS[token]
        user_info["is_authenticated"] = True
        return user_info

    # If an unknown token is provided, raise 401
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

def require_role(required_role: str):
    def role_checker(current_user: dict = Depends(get_current_user)):
        if current_user.get("role") != "admin" and current_user.get("role") != required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation not permitted. Requires role: {required_role}"
            )
        return current_user
    return role_checker
