import os
import glob   
import pandas as pd

from src.forecast import get_forecast
from src.observations import get_observation
from src.verification import verify


os.makedirs("data/forecasts", exist_ok=True)
os.makedirs("data/verified", exist_ok=True)
os.makedirs("data/observations", exist_ok=True)



def run():
    forecast = get_forecast()

    target_time = forecast["time_utc"].iloc[0]
    now = pd.Timestamp.utcnow()

    safe_time = target_time.strftime("%Y-%m-%d_%H-%M-%S")
    print("SAFE TIME:", safe_time)
    print("Now:", now)
    print("Target time:", target_time)

    print("Saving forecast to:", f"data/forecasts/{target_time}.csv")

    
    print("⚠️ Forcing observation fetch (debug mode)")
    obs = get_observation(target_time)

    # skip if forecast is in the future
    '''
    if target_time > now:
        print("Observation not available yet — skipping verification")

        # Save forecast for later verification
        safe_time = target_time.strftime("%Y-%m-%d_%H-%M-%S")
        filepath = f"data/forecasts/{safe_time}.csv"

        print("Saving forecast to:", filepath)
        forecast.to_csv(filepath, index=False)
        print("Forecast saved for later verification")

        return'''
    
    obs = get_observation(target_time)

    # Save observation
    obs_path = f"data/observations/{safe_time}.csv"
    print("Saving observation to:", obs_path)
    obs.to_csv(obs_path, index=False)
    print("Observation saved")

    result = verify(forecast, obs)

    print(result)

    #Save verified result
    result.to_csv(f"data/verified/{safe_time}.csv", index=False)
    print("Verification saved")


    

def verify_stored_forecasts():
    files = glob.glob("data/forecasts/*.csv")

    for f in files:
        forecast = pd.read_csv(f)
        forecast["time_utc"] = pd.to_datetime(forecast["time_utc"], utc=True)

        target_time = forecast["time_utc"].iloc[0]

        safe_time = target_time.strftime("%Y-%m-%d_%H-%M-%S")

        if target_time > pd.Timestamp.utcnow():
            continue  # not ready yet

        print(f"✅ Verifying {target_time}")

        
        obs = get_observation(target_time)

        # ✅ Save observation
        obs_path = f"data/observations/{safe_time}.csv"
        obs.to_csv(obs_path, index=False)
        print("✅ Observation saved:", safe_time)

        
        merged = forecast.merge(obs, on="time_utc", how="inner")

        print("Merged data:")
        print(merged)

        # Keep your verification if you want
        result = verify(forecast, obs)

        print(result)

        # Save verified result
        result.to_csv(f"data/verified/{safe_time}.csv", index=False)
        print("Verification saved")



if __name__ == "__main__":
    run()
    verify_stored_forecasts()
