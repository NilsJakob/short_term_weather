import sqlite3
import pandas as pd

# Connect to DB
conn = sqlite3.connect("data/weather.db")

# ✅ Load full table
df = pd.read_sql("SELECT * FROM verification ORDER BY time_utc", conn)

# ✅ Print overview
print("\n📊 DATABASE OVERVIEW")
print("---------------------")
print("Rows:", len(df))
print("Columns:", df.columns.tolist())

# ✅ Show first rows
print("\n🔹 First rows:")
print(df.head())

# ✅ Show last rows
print("\n🔹 Latest rows:")
print(df.tail())

conn.close()
