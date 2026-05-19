import os
import glob
import pandas as pd
import sqlite3
from pathlib import Path

from src.forecast import get_forecast
from src.observations import get_observation
from src.verification import verify
from src.build_dataset import build_dataset

# ✅ Ensure folders exist
os.makedirs("data/forecasts", exist_ok=True)
os.makedirs("data/observations", exist_ok=True)
os.makedirs("data/verified", exist_ok=True)

DB_PATH = Path("data/weather.db")


# ✅ ---------------------------------------------------
# DATABASE SETUP
# ✅ ---------------------------------------------------
def init_db(conn):
    conn.execute("""
    CREATE TABLE IF NOT EXISTS verification (
        time_utc TEXT PRIMARY KEY,
        temperature_fc REAL,
        wind_fc REAL,
        issued_at TEXT,
        temperature_obs REAL,
        wind_obs REAL,
        temp_error REAL,
        wind_error REAL,
        station_id TEXT,
        lead_time_minutes REAL
    )
    """)
    conn.commit()


# ✅ ---------------------------------------------------
# UPSERT FUNCTION (REUSABLE ✅)
# ✅ ---------------------------------------------------
def upsert_verification(conn, df):
    df["time_utc"] = df["time_utc"].astype(str)
    df["issued_at"] = df["issued_at"].astype(str)

    cursor = conn.cursor()

    for _, row in df.iterrows():
        cursor.execute("""
            INSERT INTO verification (
                time_utc,
                temperature_fc,
                wind_fc,
                issued_at,
                temperature_obs,
                wind_obs,
                temp_error,
                wind_error,
                station_id,
                lead_time_minutes
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(time_utc)
            DO UPDATE SET
                temperature_fc = excluded.temperature_fc,
                wind_fc = excluded.wind_fc,
                issued_at = excluded.issued_at,
                temperature_obs = excluded.temperature_obs,
                wind_obs = excluded.wind_obs,
                temp_error = excluded.temp_error,
                wind_error = excluded.wind_error,
                station_id = excluded.station_id,
                lead_time_minutes = excluded.lead_time_minutes
        """, (
            row["time_utc"],
            row["temperature_fc"],
            row["wind_fc"],
            row["issued_at"],
            row["temperature_obs"],
            row["wind_obs"],
            row["temp_error"],
            row["wind_error"],
            row["station_id"],
            row["lead_time_minutes"]
        ))

    conn.commit()


# ✅ ---------------------------------------------------
# MAIN PIPELINE
# ✅ ---------------------------------------------------
def run():
    print("\n🚀 Running pipeline")

    conn = sqlite3.connect(DB_PATH)
    init_db(conn)
    print("✅ DB ready")

    # ✅ 1. Forecast
    forecast = get_forecast()
    if forecast is None or forecast.empty:
        print("❌ No forecast data")
        return

    target_time = forecast["time_utc"].iloc[0]
    issued_at = pd.to_datetime(forecast["issued_at"].iloc[0])
    safe_time = issued_at.strftime("%Y-%m-%d_%H-%M-%S")

    forecast.to_csv(f"data/forecasts/{safe_time}.csv", index=False)
    print("✅ Forecast saved")

    # ✅ 2. Observation
    obs = get_observation(target_time)
    if obs is None or obs.empty:
        print("⏭ No observation")
        return

    obs["time_utc"] = pd.to_datetime(obs["time_utc"], utc=True)
    obs.to_csv(f"data/observations/{safe_time}.csv", index=False)
    print("✅ Observation saved")

    # ✅ 3. Verification
    result = verify(forecast, obs)
    if result is None or result.empty:
        print("⚠️ No verification results")
        return

    print("✅ Verified rows:", len(result))

    # ✅ Lead time
    result["lead_time_minutes"] = (
        pd.to_datetime(result["time_utc"]) -
        pd.to_datetime(result["issued_at"])
    ).dt.total_seconds() / 60

    # ✅ Save CSV
    result.to_csv(f"data/verified/{safe_time}.csv", index=False)

    # ✅ UPSERT (single clean insert ✅)
    upsert_verification(conn, result)
    print("✅ Upserted into SQLite")

    # ✅ Backfill history
    verify_stored_forecasts(conn)

    # ✅ Debug count
    count = pd.read_sql("SELECT COUNT(*) as n FROM verification", conn)
    print("✅ Rows in DB:", count["n"][0])

    conn.close()


# ✅ ---------------------------------------------------
# VERIFY STORED FORECASTS (FIXED ✅)
# ✅ ---------------------------------------------------
def verify_stored_forecasts(conn):
    print("\n🔁 Running stored forecast verification")

    files = glob.glob("data/forecasts/*.csv")
    if not files:
        return

    latest_file = max(files)

    for f in files:
        if f == latest_file:
            continue

        forecast = pd.read_csv(f)

        if "time_utc" not in forecast.columns:
            continue

        forecast["time_utc"] = pd.to_datetime(forecast["time_utc"], utc=True)

        target_time = forecast["time_utc"].iloc[0]

        if target_time > pd.Timestamp.now('UTC'):
            continue

        obs = get_observation(target_time)
        if obs is None or obs.empty:
            continue

        obs["time_utc"] = pd.to_datetime(obs["time_utc"], utc=True)

        result = verify(forecast, obs)
        if result is None or result.empty:
            continue

        result["lead_time_minutes"] = (
            pd.to_datetime(result["time_utc"]) -
            pd.to_datetime(result["issued_at"])
        ).dt.total_seconds() / 60

        upsert_verification(conn, result)


# ✅ ---------------------------------------------------
# ENTRY POINT
# ✅ ---------------------------------------------------
if __name__ == "__main__":
    run()

    try:
        build_dataset()
        print("✅ Dataset built")
    except Exception as e:
        print("⚠️ Dataset build failed:", e)
