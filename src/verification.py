import pandas as pd


def verify(forecast_df, obs_df):
    # ✅ ensure sorting (required!)
    forecast_df = forecast_df.sort_values("time_utc")
    obs_df = obs_df.sort_values("time_utc")

    # ✅ nearest-time merge
    df = pd.merge_asof(
        forecast_df,
        obs_df,
        on="time_utc",
        direction="nearest",
        tolerance=pd.Timedelta("1h")  # allow 1 hour difference
    )

    # ✅ remove rows where no match found
    df = df.dropna(subset=["temperature_obs"])

    # ✅ compute errors
    df["temp_error"] = df["temperature_fc"] - df["temperature_obs"]
    df["wind_error"] = df["wind_fc"] - df["wind_obs"]

    print("✅ Verified rows:", len(df))

    return df
