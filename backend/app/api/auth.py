import bcrypt
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import create_access_token, get_current_user, normalize_department
from app.database import get_db
from app.models.models import User


router = APIRouter(prefix="/auth", tags=["Authentication"])


class LoginRequest(BaseModel):
    email: str
    password: str


@router.post("/login")
def login(data: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    try:
        password_matches = bcrypt.checkpw(
            data.password.encode(), user.password_hash.encode()
        )
    except ValueError:
        password_matches = False

    if not password_matches:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    user_data = {
        "id": user.id,
        "role": user.role,
    }
    if user.department is not None:
        user_data["department"] = normalize_department(user.department) or user.department
    if user.name and user.department is not None:
        user_data["name"] = user.name

    return {
        "access_token": create_access_token(user.id),
        "token_type": "bearer",
        "user": user_data,
    }


@router.get("/session")
def get_session(current_user: User = Depends(get_current_user)):
    user_data = {
        "id": current_user.id,
        "role": current_user.role,
    }
    if current_user.department is not None:
        user_data["department"] = (
            normalize_department(current_user.department) or current_user.department
        )
    if current_user.name and current_user.department is not None:
        user_data["name"] = current_user.name
    return user_data