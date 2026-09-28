import os
from pathlib import Path
from urllib.parse import quote_plus

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker


# Project root:
# Intelligent-Telecom-Operations-Platform/
ROOT = Path(__file__).resolve().parents[2]

# Load backend/.env explicitly
ENV_FILE = ROOT / "backend" / ".env"
load_dotenv(ENV_FILE)

MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")

if not MYSQL_PASSWORD:
    raise ValueError(
        f"MYSQL_PASSWORD environment variable is not set. "
        f"Expected .env file at: {ENV_FILE}"
    )

DATABASE_URL = (
    f"mysql+pymysql://root:{quote_plus(MYSQL_PASSWORD)}"
    "@localhost:3306/telecom_operations"
)

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()