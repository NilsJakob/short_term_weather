import os
import glob
import pandas as pd

from src.forecast import get_forecast
from src.observations import get_observation
from src.verification import verify
from src.build_dataset import build_dataset

# ✅ Ensure folders exist
os.makedirs("data/forecasts", exist_ok=True)
os.makedirs("data/observations", exist_ok=True)
os.makedirs("data/verified", exist_ok=True)
os.makedirs("data", exist_ok=True)


def run():
    print("\n🚀 Running pipeline")

    # ✅ 1. Get forecast
    forecast = get_forecast()

    if forecast is None or forecast.empty:
        print("❌ No forecast data")
        return

    target_time = forecast["time_utc"].iloc[0]
    issued_at = pd.to_datetime(forecast["issued_at"].iloc[0])
    safe_time = issued_at.strftime("%Y-%m-%d_%H-%M-%S")

    # ✅ 2. Save forecast
    forecast_path = f"data/forecasts/{safe_time}.csv"
    forecast.to_csv(forecast_path, index=False)
    print("✅ Forecast saved:", forecast_path)

    # ✅ 3. Get observation
    print(f"\n📡 Fetching observation for {target_time}")
    obs = get_observation(target_time)

    # ✅ ✅ CRITICAL VALIDATION (prevents crash)
    if obs is None:
        print("❌ Observation is None")
        return

    if obs.empty:
        print("⏭ Skipping — observation is empty")
        return

    if "time_utc" not in obs.columns:
        print(f"❌ Missing 'time_utc' in obs. Columns: {obs.columns}")
        return

    # ✅ Ensure datetime format
    obs["time_utc"] = pd.to_datetime(obs["time_utc"], utc=True)

    # ✅ 4. Save observation
    obs_path = f"data/observations/{safe_time}.csv"
    obs.to_csv(obs_path, index=False)
    print("✅ Observation saved:", obs_path)

    # ✅ 5. Verify
    print("\n🔍 Running verification...")
    result = verify(forecast, obs)

    if result is None or result.empty:
        print("⚠️ No verification results produced")
        return

    print("✅ Verified rows:", len(result))

    # ✅ 6. Save verification
    result_path = f"data/verified/{safe_time}.csv"
    result.to_csv(result_path, index=False)
    print("✅ Verification saved:", result_path)


def verify_stored_forecasts():
    print("\n🔁 Running verification of stored forecasts")

    files = glob.glob("data/forecasts/*.csv")

    if not files:
        print("⚠️ No stored forecasts found")
        return

    for f in files:
        print("\n📂 Processing:", f)

        forecast = pd.read_csv(f)

        # ✅ Validate forecast
        if "time_utc" not in forecast.columns:
            print("❌ Missing time_utc in forecast, skipping")
            continue

        forecast["time_utc"] = pd.to_datetime(forecast["time_utc"], utc=True)

        target_time = forecast["time_utc"].iloc[0]
        issued_at = pd.to_datetime(forecast["issued_at"].iloc[0])
        safe_time = issued_at.strftime("%Y-%m-%d_%H-%M-%S")

        # ✅ Skip future forecasts
        if target_time > pd.Timestamp.utcnow():
            print("⏭ Skipping (future forecast)")
            continue

        print("✅ Verifying:", target_time)

        # ✅ Fetch observation
        obs = get_observation(target_time)

        # ✅ ✅ CRITICAL VALIDATION (prevents crash)
        if obs is None or obs.empty or "time_utc" not in obs.columns:
            print("⏭ Skipping — invalid observation data")
            continue

        obs["time_utc"] = pd.to_datetime(obs["time_utc"], utc=True)

        # ✅ Save observation
        obs_path = f"data/observations/{safe_time}.csv"
        obs.to_csv(obs_path, index=False)
        print("✅ Observation saved:", obs_path)

        # ✅ Sort before merge (important)
        forecast = forecast.sort_values("time_utc")
        obs = obs.sort_values("time_utc")

        # ✅ Robust alignment
        merged = pd.merge_asof(
            forecast,
            obs,
            on="time_utc",
            direction="nearest",
            tolerance=pd.Timedelta("1h")
        )

        merged = merged.dropna(subset=["temperature_obs"])

        print("✅ Merged rows:", len(merged))

        # ✅ Verify
        result = verify(forecast, obs)

        if result is None or result.empty:
            print("⚠️ No verification results")
            continue

        result_path = f"data/verified/{safe_time}.csv"
        result.to_csv(result_path, index=False)

        print("✅ Verification saved:", result_path)


if __name__ == "__main__":
    print("📁 Working directory:", os.getcwd())

    run()
    verify_stored_forecasts()

    try:
        build_dataset()
        print("✅ Dataset built")
    except Exception as e:
        print("⚠️ Dataset build failed:", e)