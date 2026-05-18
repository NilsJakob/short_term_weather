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
    else:
        print("✅ Verified rows:", len(result))

        result["lead_time_minutes"] = (
            pd.to_datetime(result["time_utc"]) -
            pd.to_datetime(result["issued_at"])
        ).dt.total_seconds() / 60

        
        try:
            result.to_sql("verification", conn, if_exists="append", index=False)
            print("✅ Inserted into SQLite")
        except Exception as e:
            if "UNIQUE constraint failed" in str(e):
                print("⏭ Duplicate skipped")
            else:
                print("❌ Unexpected DB error:", e)   # ✅ DO NOT raise


    print("✅ Verified rows:", len(result))

    result["lead_time_minutes"] = (
        pd.to_datetime(result["time_utc"]) -
        pd.to_datetime(result["issued_at"])
    ).dt.total_seconds() / 60

    # ✅ SAVE CSV
    result.to_csv(f"data/verified/{safe_time}.csv", index=False)

    # ✅ INSERT INTO SQLITE (single clean insert)
    try:
        result.to_sql("verification", conn, if_exists="append", index=False)
        print("✅ Inserted into SQLite")
    except Exception as e:
        if "UNIQUE constraint failed" in str(e):
            print("⏭ Duplicate skipped")
        else:
            raise e

    # ✅ Backfill / historical verification
    verify_stored_forecasts(conn)

    # ✅ Debug count
    try:
        count = pd.read_sql("SELECT COUNT(*) as n FROM verification", conn)
        print("✅ Rows in DB:", count["n"][0])
    except Exception as e:
        print("⚠️ Could not read DB (likely empty):", e)

    print("✅ Rows in DB:", count["n"][0])

    conn.close()


# ✅ ---------------------------------------------------
# VERIFY STORED FORECASTS
# ✅ ---------------------------------------------------
def verify_stored_forecasts(conn):
    print("\n🔁 Running stored forecast verification")

    files = glob.glob("data/forecasts/*.csv")

    
    latest_file = max(files)

    for f in files:
        if f == latest_file:
            continue   # ✅ skip current file (already processed)

        forecast = pd.read_csv(f)

        if "time_utc" not in forecast.columns:
            continue

        forecast["time_utc"] = pd.to_datetime(forecast["time_utc"], utc=True)

        target_time = forecast["time_utc"].iloc[0]

        if target_time > pd.Timestamp.now('UTC'):
            continue

        obs = get_observation(target_time)

        if obs is None or obs.empty or "time_utc" not in obs.columns:
            continue

        obs["time_utc"] = pd.to_datetime(obs["time_utc"], utc=True)

        result = verify(forecast, obs)

        if result is None or result.empty:
            continue

        try:
            result.to_sql("verification", conn, if_exists="append", index=False)
        except Exception as e:
            if "UNIQUE constraint failed" in str(e):
                print("⏭ Duplicate skipped (history)")
            else:
                raise e


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
