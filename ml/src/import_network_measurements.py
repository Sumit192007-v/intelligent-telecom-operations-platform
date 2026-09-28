from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text
from urllib.parse import quote_plus


ROOT = Path(__file__).resolve().parents[2]

CSV_PATH = ROOT / "ml/data/features/telecom_features.csv"

MYSQL_PASSWORD = "spsv@0123"

DATABASE_URL = (
    f"mysql+pymysql://root:{quote_plus(MYSQL_PASSWORD)}"
    "@localhost:3306/telecom_operations"
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