import pandas as pd
import glob

def build_dataset():
    print("Building combined dataset...")

    # Get all verified files
    files = glob.glob("data/verified/*.csv")

    if not files:
        print("No verified files found")
        return

    dfs = []

    for f in files:
        df = pd.read_csv(f)

        # Ensure datetime parsing
        df["time_utc"] = pd.to_datetime(df["time_utc"], utc=True)

        dfs.append(df)

    # Combine all into one dataset
    combined = pd.concat(dfs, ignore_index=True)

    # Sort by time
    combined = combined.sort_values("time_utc")

    
    combined["lead_time_minutes"] = (
        combined["time_utc"] - pd.to_datetime(combined["issued_at"])
    ).dt.total_seconds() / 60


    # Save dataset
    combined.to_csv("data/combined_dataset.csv", index=False)

    print("Combined dataset saved: data/combined_dataset.csv")
    print("Rows:", len(combined))

    return combined


if __name__ == "__main__":
    build_dataset()