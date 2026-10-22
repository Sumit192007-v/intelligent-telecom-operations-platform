import base64
import hashlib
import hmac
import json
import os
import time

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import User


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def _encode_segment(value: dict) -> str:
    encoded = json.dumps(value, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(encoded).rstrip(b"=").decode()


def create_access_token(user_id: int) -> str:
    secret = os.getenv("JWT_SECRET")
    if not secret:
        raise RuntimeError("JWT_SECRET is not configured")

    header = _encode_segment({"alg": "HS256", "typ": "JWT"})
    payload = _encode_segment({"sub": str(user_id), "exp": int(time.time()) + 3600})
    signing_input = f"{header}.{payload}".encode()
    signature = hmac.new(secret.encode(), signing_input, hashlib.sha256).digest()
    encoded_signature = base64.urlsafe_b64encode(signature).rstrip(b"=").decode()
    return f"{header}.{payload}.{encoded_signature}"


def _decode_access_token(token: str) -> int:
    secret = os.getenv("JWT_SECRET")
    if not secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication is not configured",
        )

    try:
        header, payload, signature = token.split(".")
        signing_input = f"{header}.{payload}".encode()
        expected = hmac.new(secret.encode(), signing_input, hashlib.sha256).digest()
        actual = base64.urlsafe_b64decode(signature + "=" * (-len(signature) % 4))
        if not hmac.compare_digest(expected, actual):
            raise ValueError("Invalid signature")

        header_data = json.loads(
            base64.urlsafe_b64decode(header + "=" * (-len(header) % 4))
        )
        payload_data = json.loads(
            base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4))
        )
        user_id = int(payload_data["sub"])
        if header_data.get("alg") != "HS256" or payload_data["exp"] <= time.time():
            raise ValueError("Expired or unsupported token")
        return user_id
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    user_id = _decode_access_token(token)
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


EMPLOYEE_ROLES = {"staff", "support_agent", "engineer", "manager", "admin"}
MANAGEMENT_ROLES = {"manager", "admin"}
CONFIGURED_DEPARTMENTS = ("Technical", "Network", "Billing", "Customer Support")


def normalize_department(dept: str | None) -> str | None:
    if not dept:
        return None
    d = dept.strip().lower()
    if d in ("network", "network operations"):
        return "Network"
    if d in ("technical", "technical support", "field engineering"):
        return "Technical"
    if d in ("billing", "billing and payments", "billing & payments"):
        return "Billing"
    if d in ("customer support", "support", "customer service"):
        return "Customer Support"
    if d in ("operations", "management"):
        return "Operations"
    return dept.strip()


def require_role(role: str):
    def check_role(current_user: User = Depends(get_current_user)) -> User:
        if role == "staff":
            if current_user.role != "staff" and current_user.role not in EMPLOYEE_ROLES:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient permissions",
                )
        elif current_user.role != role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return current_user

    return check_role


def require_employee(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "staff" and current_user.role not in EMPLOYEE_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Employee access required",
        )
    return current_user


def require_department(*allowed_departments: str):
    normalized_allowed = {d.strip().lower() for d in allowed_departments}

    def check_dept(current_user: User = Depends(require_employee)) -> User:
        # Managers and admins have cross-department oversight
        if current_user.role in MANAGEMENT_ROLES:
            return current_user

        if not current_user.department:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Employee account does not have a department assigned.",
            )

        user_dept = normalize_department(current_user.department)
        if not user_dept or user_dept.lower() not in normalized_allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access restricted to {', '.join(allowed_departments)} department.",
            )
        return current_user

    return check_dept