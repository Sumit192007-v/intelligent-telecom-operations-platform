from fastapi import Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import User

GUEST_EMAIL = "guest@local.invalid"


def get_guest_customer(db: Session = Depends(get_db)) -> User:
    """Authentication is removed: every customer request acts as one shared guest user."""
    user = db.query(User).filter(User.email == GUEST_EMAIL).first()
    if user is None:
        user = User(
            name="Guest Customer",
            email=GUEST_EMAIL,
            password_hash="",
            role="customer",
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return user
