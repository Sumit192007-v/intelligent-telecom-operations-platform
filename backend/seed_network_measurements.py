import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import pymysql
from dotenv import dotenv_values


ROOT = Path(__file__).resolve().parents[1]
TARGET_ROWS = 4500
BATCH_SIZE = 500
CSV_PATH = ROOT / "dataset" / "telecom_real_measurements.csv"
ENV_PATH = ROOT / "backend" / ".env"

INSERT_SQL = """
INSERT INTO network_measurements (
    operator, timestamp, latitude, longitude, download_mbps, upload_mbps,
    rtt_ms, network_technology, `5g_frequency_mhz`, `5g_pci`,
    lte_earfcn, cell_event
) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
"""

METROS = (
    (40.7128, -74.0060),
    (41.8781, -87.6298),
    (32.7767, -96.7970),
    (37.7749, -122.4194),
    (34.0522, -118.2437),
    (33.7490, -84.3880),
    (47.6062, -122.3321),
)
OPERATORS = ("AT&T", "T-Mobile", "Verizon")


def measurement_key(operator, timestamp, latitude, longitude, latency):
    if timestamp.tzinfo is not None:
        timestamp = timestamp.astimezone(timezone.utc).replace(tzinfo=None)
    return (
        operator,
        timestamp.replace(microsecond=0),
        round(float(latitude), 6),
        round(float(longitude), 6),
        round(float(latency), 3),
    )


def db_value(value):
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        return value.item()
    return value


def make_synthetic_rows(count, known_keys):
    rng = random.Random(4500)
    rows = []
    timestamp = datetime.now().replace(microsecond=0)
    while len(rows) < count:
        center_latitude, center_longitude = rng.choice(METROS)
        latitude = round(rng.gauss(center_latitude, 0.12), 6)
        longitude = round(rng.gauss(center_longitude, 0.12), 6)
        latency = round(rng.uniform(75, 130) if rng.random() < 0.18 else rng.uniform(15, 74.9), 1)
        operator = rng.choice(OPERATORS)
        row_timestamp = timestamp - timedelta(seconds=len(rows))
        key = measurement_key(operator, row_timestamp, latitude, longitude, latency)
        if key in known_keys:
            continue
        known_keys.add(key)
        rows.append((
            operator,
            row_timestamp,
            latitude,
            longitude,
            round(rng.uniform(5, 250), 2),
            round(rng.uniform(1, 100), 2),
            latency,
            rng.choice(("LTE", "5G", "5G NSA")),
            rng.choice((600.0, 700.0, 850.0, 1900.0, 2100.0, 3500.0)),
            rng.randint(0, 1007),
            rng.choice((700, 1200, 1650, 2100, 39000)),
            None,
        ))
    return rows


def main():
    config = dotenv_values(ENV_PATH)
    password = config.get("MYSQL_PASSWORD")
    if not password:
        raise RuntimeError("MYSQL_PASSWORD is missing from backend/.env")

    frame = pd.read_csv(CSV_PATH)
    frame["timestamp"] = pd.to_datetime(
        frame["timestamp"], format="mixed", errors="coerce", utc=True
    ).dt.tz_localize(None)
    frame = frame.sample(frac=1, random_state=4500).reset_index(drop=True)

    connection = pymysql.connect(
        host="localhost",
        user="root",
        password=password,
        database="telecom_operations",
        autocommit=False,
    )
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM network_measurements")
            current_count = cursor.fetchone()[0]
            remaining = max(0, TARGET_ROWS - current_count)
            if remaining == 0:
                print(f"Already at target: {current_count} rows")
                return

            cursor.execute("""
                SELECT operator, timestamp, latitude, longitude, rtt_ms
                FROM network_measurements
            """)
            known_keys = {
                measurement_key(*row)
                for row in cursor.fetchall()
                if row[4] is not None
            }

            source_rows = []
            for row in frame.to_dict("records"):
                timestamp = row["timestamp"]
                latency = row["rtt_ms"]
                if pd.isna(timestamp) or pd.isna(latency):
                    continue
                key = measurement_key(
                    row["operator"], timestamp, row["latitude"],
                    row["longitude"], latency,
                )
                if key in known_keys:
                    continue
                known_keys.add(key)
                source_rows.append((
                    row["operator"], timestamp.to_pydatetime(),
                    db_value(row["latitude"]), db_value(row["longitude"]),
                    db_value(row["download_mbps"]), db_value(row["upload_mbps"]),
                    db_value(latency), db_value(row["network_technology"]),
                    db_value(row["5g_frequency_mhz"]), db_value(row["5g_pci"]),
                    db_value(row["lte_earfcn"]), db_value(row["cell_event"]),
                ))
                if len(source_rows) == remaining:
                    break

            inserted_from_csv = len(source_rows)
            rows = source_rows
            rows.extend(make_synthetic_rows(remaining - len(rows), known_keys))

            for offset in range(0, len(rows), BATCH_SIZE):
                cursor.executemany(INSERT_SQL, rows[offset:offset + BATCH_SIZE])
            connection.commit()

            cursor.execute("SELECT COUNT(*) FROM network_measurements")
            final_count = cursor.fetchone()[0]
            print(f"Inserted {inserted_from_csv} CSV and {len(rows) - inserted_from_csv} synthetic rows")
            print(f"Total network measurements: {final_count}")
            if final_count < TARGET_ROWS:
                raise RuntimeError(f"Target not reached: {final_count} < {TARGET_ROWS}")
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


if __name__ == "__main__":
    main()