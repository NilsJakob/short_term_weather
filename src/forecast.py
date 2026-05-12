import requests
import pandas as pd
from datetime import datetime, timedelta, timezone
from src.config import LAT, LON, USER_AGENT, FORECAST_HORIZON_HOURS


def get_forecast():
    print("🔄 Fetching forecast...")

    url = (
        f"https://api.met.no/weatherapi/locationforecast/2.0/compact"
        f"?lat={LAT}&lon={LON}"
    )

    headers = {"User-Agent": USER_AGENT}
    r = requests.get(url, headers=headers)

    if r.status_code != 200:
        raise Exception(f"Forecast error: {r.status_code}")

    data = r.json()

    rows = []
    for ts in data["properties"]["timeseries"]:
        details = ts["data"]["instant"]["details"]

        rows.append({
            "time_utc": ts["time"],
            "temperature_fc": details.get("air_temperature"),
            "wind_fc": details.get("wind_speed"),
        })

    df = pd.DataFrame(rows)
    
    
    from datetime import datetime, timezone, timedelta

    issued_at = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)

    df["time_utc"] = pd.to_datetime(df["time_utc"], utc=True)

    target_time = issued_at + timedelta(hours=1)

    df["issued_at"] = issued_at   # ✅ assign AFTER everything


    df_future = df[df["time_utc"] >= target_time]
    df = df_future.sort_values("time_utc").head(1)

    df["issued_at"] = issued_at

    now = datetime.now(timezone.utc)
    target_time = now + timedelta(hours=FORECAST_HORIZON_HOURS)

    # ✅ keep only forecasts for next hour
    df = df.iloc[(df["time_utc"] - target_time).abs().argsort()[:1]]

    print("✅ Forecast extracted for:", df["time_utc"].iloc[0])
    return df