import os
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import URL, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker


# Project root:
# Intelligent-Telecom-Operations-Platform/
ROOT = Path(__file__).resolve().parents[2]

# Load backend/.env explicitly
ENV_FILE = ROOT / "backend" / ".env"
load_dotenv(ENV_FILE)

MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")
MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "telecom_operations")

if not MYSQL_PASSWORD:
    raise ValueError(
        f"MYSQL_PASSWORD environment variable is not set. "
        f"Expected .env file at: {ENV_FILE}"
    )

DATABASE_URL = URL.create(
    "mysql+pymysql",
    username=MYSQL_USER,
    password=MYSQL_PASSWORD,
    host=MYSQL_HOST,
    port=MYSQL_PORT,
    database=MYSQL_DATABASE,
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