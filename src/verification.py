import pandas as pd


def verify(forecast_df, obs_df):
    df = pd.merge(forecast_df, obs_df, on="time_utc", how="inner")

    df["temp_error"] = df["temperature_fc"] - df["temperature_obs"]
    df["wind_error"] = df["wind_fc"] - df["wind_obs"]

    return df