import os
import secrets

os.environ["MYSQL_PASSWORD"] = secrets.token_urlsafe(24)
os.environ["JWT_SECRET"] = secrets.token_urlsafe(32)

import bcrypt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth import create_access_token
from app.database import Base, get_db
from app.main import app
from app.models.models import User


@pytest.fixture
def api_client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    test_sessions = sessionmaker(bind=engine, expire_on_commit=False)

    def override_get_db():
        session = test_sessions()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as client:
            yield client, test_sessions
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture
def create_user():
    def create(session_factory, role, email=None):
        password = secrets.token_urlsafe(18)
        email = email or f"{secrets.token_hex(8)}@example.invalid"
        user = User(
            name="Test User",
            email=email,
            password_hash=bcrypt.hashpw(
                password.encode(), bcrypt.gensalt(rounds=4)
            ).decode(),
            role=role,
        )
        with session_factory() as session:
            session.add(user)
            session.commit()
            session.refresh(user)
            return user.id, password

    return create


@pytest.fixture
def auth_headers():
    def headers(user_id):
        return {"Authorization": f"Bearer {create_access_token(user_id)}"}

    return headers