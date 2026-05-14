import requests
import folium
from datetime import datetime, timedelta, timezone

from src.config import FROST_CLIENT_ID, LAT, LON


# ✅ 1. Get nearest stations
def get_nearest_stations(maxcount=10):
    url = "https://frost.met.no/sources/v0.jsonld"

    params = {
        "geometry": f"nearest(POINT({LON} {LAT}))",
        "elements": "air_temperature",
        "nearestmaxcount": maxcount
    }

    r = requests.get(url, params=params, auth=(FROST_CLIENT_ID, ""))

    if r.status_code != 200:
        print("❌ Failed to fetch stations:", r.status_code)
        return []

    data = r.json()["data"]

    stations = []
    for s in data:
        stations.append({
            "id": s["id"],
            "name": s["name"],
            "lat": s["geometry"]["coordinates"][1],
            "lon": s["geometry"]["coordinates"][0],
        })

    print("✅ Found stations:", [s["id"] for s in stations])
    return stations


# ✅ 2. Get latest temperature
def get_latest_temp(station_id):
    url = "https://frost.met.no/observations/v0.jsonld"

    now = datetime.now(timezone.utc)
    start = now - timedelta(hours=12)

    params = {
        "sources": station_id,
        "elements": "air_temperature",
        "referencetime": f"{start.isoformat()}/{now.isoformat()}",
    }

    r = requests.get(url, params=params, auth=(FROST_CLIENT_ID, ""))

    if r.status_code != 200:
        return None

    data = r.json().get("data", [])
    if not data:
        return None

    latest = data[-1]

    try:
        temp = latest["observations"][0]["value"]
        time = latest["referenceTime"]
    except:
        return None

    return temp, time


# ✅ 3. Plot map
def main():
    print("📍 Forecast location:", LAT, LON)
    stations = get_nearest_stations(maxcount=10)

    # ✅ Map centered on your forecast location
    m = folium.Map(location=[LAT, LON], zoom_start=11)

    # ✅ Add your forecast point
    folium.Marker(
        [LAT, LON],
        popup="📍 Forecast location",
        icon=folium.Icon(color="blue")
    ).add_to(m)

    for s in stations:
        obs = get_latest_temp(s["id"])

        if obs:
            temp, time = obs
            color = "green"
            popup = (
                f"🆔 {s['id']}<br>"
                f"{s['name']}<br>"
                f"{temp:.1f} °C<br>"
                f"{time}"
            )
        else:
            color = "red"
            popup = f"{s['name']}<br>❌ No recent data"

        folium.Marker(
            location=[s["lat"], s["lon"]],
            popup=popup,
            icon=folium.Icon(color=color)
        ).add_to(m)

    # ✅ Save map
    m.save("station_map.html")
    print("✅ Map saved as station_map.html")


if __name__ == "__main__":
    main()
