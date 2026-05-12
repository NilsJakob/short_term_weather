import requests
import pandas as pd
from datetime import datetime, timedelta, timezone
import glob

from src.config import FROST_CLIENT_ID, LAT, LON

# ADD THESE
DEFAULT_STATION = "SN18700"
SELECTED_STATION = None

# ======================
# STATION LOGIC
# ======================

def get_nearest_station_raw():
    url = "https://frost.met.no/sources/v0.jsonld"

    params = {
        "geometry": f"nearest(POINT({LON} {LAT}))",
        "nearestmaxcount": 1
    }

    r = requests.get(url, params=params, auth=(FROST_CLIENT_ID, ""))

    if r.status_code != 200:
        raise Exception("Station lookup failed")

    data = r.json()
    return data["data"][0]["id"]


def has_recent_data(station_id):
    url = "https://frost.met.no/observations/v0.jsonld"

    end = datetime.now(UTC)
    start = end - timedelta(hours=6)

    params = {
        "sources": station_id,
        "elements": "air_temperature",
        "referencetime": f"{start.isoformat()}/{end.isoformat()}"
    }

    r = requests.get(url, params=params, auth=(FROST_CLIENT_ID, ""))

    if r.status_code != 200:
        return False

    data = r.json()
    return len(data.get("data", [])) > 0


def get_nearest_station_with_data():
    url = "https://frost.met.no/sources/v0.jsonld"

    params = {
        "geometry": f"nearest(POINT({LON} {LAT}))",
        "elements": "air_temperature",
        "nearestmaxcount": 1
    }

    r = requests.get(url, params=params, auth=(FROST_CLIENT_ID, ""))

    if r.status_code != 200:
        raise Exception("Fallback station lookup failed")

    data = r.json()
    return data["data"][0]["id"]



# Cache to avoid repeated API calls
#SELECTED_STATION = None

def select_station():
    global SELECTED_STATION

    # Use cached station if already selected
    if SELECTED_STATION is not None:
        return SELECTED_STATION

    try:
        raw_station = get_nearest_station_raw()

        if has_recent_data(raw_station):
            print("Using closest station:", raw_station)
            SELECTED_STATION = (raw_station, "closest")
            return SELECTED_STATION

        fallback = get_nearest_station_with_data()
        print("Using fallback station:", fallback)
        SELECTED_STATION = (fallback, "fallback_data")
        return SELECTED_STATION

    except Exception:
        print("API error → using default station")
        SELECTED_STATION = (DEFAULT_STATION, "hard_fallback")
        return SELECTED_STATION

def get_observation(timestamp):
    print(f"Fetching observation for {timestamp}")


    # SELECT STATION HERE
    station_id, station_type = select_station()
    print(f"📡 Using station: {station_id} ({station_type})")


    endpoint = "https://frost.met.no/observations/v0.jsonld"

    
    start = timestamp - pd.Timedelta(hours=2)
    end = timestamp + pd.Timedelta(hours=2)

    params = {
        "sources": "SN18700",
        "elements": "air_temperature,wind_speed",
        "referencetime": f"{start.isoformat()}/{end.isoformat()}",
        "timeresolutions": "PT1H",
    }


    r = requests.get(endpoint, params=params, auth=(FROST_CLIENT_ID, ""))

    
    if r.status_code != 200:
        print("FROST response:", r.text)   # NEW (debugging)
        raise Exception(f"FROST error: {r.status_code}")


    data = r.json()

    rows = []
    for entry in data["data"]:
        for obs in entry["observations"]:
            rows.append({
                "time_utc": entry["referenceTime"],
                obs["elementId"]: obs["value"]
            })

    df = pd.DataFrame(rows)
    
    df.rename(columns={
        "air_temperature": "temperature_obs",
        "wind_speed": "wind_obs"
    }, inplace=True)

    df = df.groupby("time_utc").first().reset_index()
    df["time_utc"] = pd.to_datetime(df["time_utc"], utc=True)

    # ✅ select closest
    df = df.iloc[(df["time_utc"] - timestamp).abs().argsort()[:1]]

    print("✅ Observation fetched")
    return df
