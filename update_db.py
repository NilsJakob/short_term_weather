import sqlite3
import pandas as pd

# Connect to DB
conn = sqlite3.connect("data/weather.db")

# Load existing data
df = pd.read_sql("SELECT * FROM verification", conn)

print("Before update:")
print(df[["time_utc", "issued_at", "lead_time_minutes"]].head())

# ✅ Recompute lead_time_minutes
df["lead_time_minutes"] = (
    pd.to_datetime(df["time_utc"]) -
    pd.to_datetime(df["issued_at"])
).dt.total_seconds() / 60

# ✅ Replace table
df.to_sql("verification", conn, if_exists="replace", index=False)

print("\n✅ Update completed")

# ✅ Verify result
df_check = pd.read_sql("SELECT * FROM verification", conn)
print("\nAfter update:")
print(df_check[["time_utc", "lead_time_minutes"]].head())

conn.close()