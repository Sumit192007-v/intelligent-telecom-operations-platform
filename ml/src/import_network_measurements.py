import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import URL, create_engine, text


ROOT = Path(__file__).resolve().parents[2]

CSV_PATH = ROOT / "ml/data/features/telecom_features.csv"
ENV_PATH = ROOT / "backend" / ".env"

load_dotenv(ENV_PATH)

MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")
if not MYSQL_PASSWORD:
    raise ValueError("MYSQL_PASSWORD must be set in the environment or backend/.env")

DATABASE_URL = URL.create(
    "mysql+pymysql",
    username=os.getenv("MYSQL_USER", "root"),
    password=MYSQL_PASSWORD,
    host=os.getenv("MYSQL_HOST", "localhost"),
    port=int(os.getenv("MYSQL_PORT", "3306")),
    database=os.getenv("MYSQL_DATABASE", "telecom_operations"),
)


def main():
    print("Loading CSV...")

    df = pd.read_csv(CSV_PATH)

    print(f"Rows loaded: {len(df)}")

    columns = [
        "operator",
        "timestamp",
        "latitude",
        "longitude",
        "download_mbps",
        "upload_mbps",
        "rtt_ms",
        "network_technology",
        "5g_frequency_mhz",
        "5g_pci",
        "lte_earfcn",
        "cell_event",
    ]

    df = df[columns].copy()

    df["timestamp"] = pd.to_datetime(
        df["timestamp"],
        errors="coerce",
        utc=True,
    ).dt.tz_localize(None)
    invalid_timestamps = df["timestamp"].isna().sum()

    print(f"Rows with missing/invalid timestamps: {invalid_timestamps}")

    df = df.dropna(subset=["timestamp"]).copy()

    print(f"Rows remaining for import: {len(df)}")

    print("Connecting to MySQL...")

    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
    )

    with engine.begin() as connection:
        connection.execute(
            text("TRUNCATE TABLE network_measurements")
        )

    print("Existing network measurements cleared.")

    df.to_sql(
    "network_measurements",
    con=engine,
    if_exists="append",
    index=False,
    chunksize=1000,
)

    print("Import completed.")

    with engine.connect() as connection:
        count = connection.execute(
            text("SELECT COUNT(*) FROM network_measurements")
        ).scalar()

    print(f"Rows in MySQL: {count}")


if __name__ == "__main__":
    main()