import os
import glob
import pandas as pd

from src.forecast import get_forecast
from src.observations import get_observation
from src.verification import verify

# ✅ Ensure folders exist
os.makedirs("data/forecasts", exist_ok=True)
os.makedirs("data/observations", exist_ok=True)
os.makedirs("data/verified", exist_ok=True)
os.makedirs("data", exist_ok=True)


def run():
    print("\n🚀 Running pipeline")

    # ✅ 1. Get forecast
    forecast = get_forecast()

    target_time = forecast["time_utc"].iloc[0]
    issued_at = pd.to_datetime(forecast["issued_at"].iloc[0])

    # ✅ Use issued_at for unique filenames
    safe_time = issued_at.strftime("%Y-%m-%d_%H-%M-%S")

    print("SAFE TIME:", safe_time)
    print("Target time:", target_time)

    # ✅ 2. Save forecast
    forecast_path = f"data/forecasts/{safe_time}.csv"
    forecast.to_csv(forecast_path, index=False)
    print("✅ Forecast saved:", forecast_path)

    # ✅ 3. Get observations
    obs = get_observation(target_time)

    # ✅ Save observations
    obs_path = f"data/observations/{safe_time}.csv"
    obs.to_csv(obs_path, index=False)
    print("✅ Observation saved:", obs_path)

    # ✅ 4. Verify
    result = verify(forecast, obs)

    print("✅ Verified rows:", len(result))

    # ✅ Save verification
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
        forecast["time_utc"] = pd.to_datetime(forecast["time_utc"], utc=True)

        target_time = forecast["time_utc"].iloc[0]
        issued_at = pd.to_datetime(forecast["issued_at"].iloc[0])

        safe_time = issued_at.strftime("%Y-%m-%d_%H-%M-%S")

        # ✅ Skip future forecasts
        if target_time > pd.Timestamp.utcnow():
            print("⏭ Skipping (future forecast)")
            continue

        print("✅ Verifying:", target_time)

        # ✅ Fetch observations
        obs = get_observation(target_time)
        obs["time_utc"] = pd.to_datetime(obs["time_utc"], utc=True)

        # ✅ Save observations
        obs_path = f"data/observations/{safe_time}.csv"
        obs.to_csv(obs_path, index=False)
        print("✅ Observation saved:", obs_path)

        # ✅ Sort before merge_asof
        forecast = forecast.sort_values("time_utc")
        obs = obs.sort_values("time_utc")

        # ✅ Robust time alignment
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

        result_path = f"data/verified/{safe_time}.csv"
        result.to_csv(result_path, index=False)

        print("✅ Verification saved:", result_path)


if __name__ == "__main__":
    run()
    verify_stored_forecasts()