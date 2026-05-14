import requests
import pandas as pd
from datetime import datetime, timedelta, timezone

from src.config import FROST_CLIENT_ID, LAT, LON

# --------------------------------------------------
# ✅ 1. Check if station has recent temperature data
# --------------------------------------------------
def has_recent_data(station_id, hours=12):
    url = "https://frost.met.no/observations/v0.jsonld"

    now = datetime.now(timezone.utc)
    start = now - timedelta(hours=hours)

    params = {
        "sources": station_id,
        "elements": "air_temperature",
        "referencetime": f"{start.isoformat()}/{now.isoformat()}",
    }

    r = requests.get(url, params=params, auth=(FROST_CLIENT_ID, ""))

    if r.status_code != 200:
        print(f"❌ API error for {station_id}: {r.status_code}")
        return False

    data = r.json().get("data", [])

    if not data:
        print(f"⚠️ No recent data for {station_id}")
        return False

    print(f"✅ {station_id} has recent data ({len(data)} obs)")
    return True


# --------------------------------------------------
# ✅ 2. Select best nearby station
# --------------------------------------------------
def select_station(maxcount=10):
    url = "https://frost.met.no/sources/v0.jsonld"

    params = {
        "geometry": f"nearest(POINT({LON} {LAT}))",
        "elements": "air_temperature",
        "nearestmaxcount": maxcount
    }

    r = requests.get(url, params=params, auth=(FROST_CLIENT_ID, ""))

    if r.status_code != 200:
        print("❌ Failed to fetch station list:", r.status_code)
        return None, "no_station"

    data = r.json().get("data", [])

    print("\n🔎 Evaluating nearby stations...")

    for station in data:
        station_id = station["id"]
        name = station["name"]

        print(f"\n🔍 Checking {station_id} ({name})")

        if has_recent_data(station_id):
            print(f"✅ SELECTED: {station_id}")
            return station_id, "nearest_with_data"
        else:
            print(f"❌ Rejected: {station_id}")

    print("\n🚫 No nearby stations with recent data found")
    return None, "no_station"


# --------------------------------------------------
# ✅ 3. Fetch observation from selected station
# --------------------------------------------------
def get_observation(target_time):
    print(f"\n📡 Fetching observation for {target_time}")

    station_id, station_type = select_station()

    # ✅ IMPORTANT: no fallback — wait instead
    if station_id is None:
        print("⚠️ No suitable local station — skipping")
        return pd.DataFrame()

    print(f"✅ Using station: {station_id} ({station_type})")

    url = "https://frost.met.no/observations/v0.jsonld"

    start_time = target_time - timedelta(hours=1)
    end_time = target_time + timedelta(hours=1)

    params = {
        "sources": station_id,
        "elements": "air_temperature,wind_speed",
        "referencetime": f"{start_time.isoformat()}/{end_time.isoformat()}",
    }

    r = requests.get(url, params=params, auth=(FROST_CLIENT_ID, ""))

    if r.status_code != 200:
        print("❌ Observation fetch failed:", r.status_code)
        return pd.DataFrame()

    data = r.json().get("data", [])

    if not data:
        print("⚠️ No observation data returned")
        return pd.DataFrame()

    rows = []

    for item in data:
        obs = {o["elementId"]: o["value"] for o in item["observations"]}

        rows.append({
            "time_utc": item["referenceTime"],
            "temperature_obs": obs.get("air_temperature"),
            "wind_obs": obs.get("wind_speed"),
            "station_id": station_id
        })

    df = pd.DataFrame(rows)
    df["time_utc"] = pd.to_datetime(df["time_utc"], utc=True)

    print("✅ Observation fetched")
    return df