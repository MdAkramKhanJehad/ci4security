import pandas as pd

INPUT_CSV = "alerts_with_category-and-apk-size.csv"
OUTPUT_CSV = "alerts_with_category-with-apk-size-updated.csv"

df = pd.read_csv(INPUT_CSV, dtype=str).fillna("")

def update_row(row):
    artifact = row["artifact_location"]
    code_loc = row["code_location"]

    if "com/google/android/" in artifact:
        if code_loc.strip().lower() == "android":
            return row

        if (
            "com/google/android/gms/ads" in artifact
            or "com/google/android/gms/internal/ads" in artifact
        ):
            row["code_location"] = "Android"
            row["3rd_party_library_name"] = "com.google.android.gms::play-services-ads-base"

        else:
            row["code_location"] = "Android"
            row["3rd_party_library_name"] = "com.google.android.gms"

    return row

df = df.apply(update_row, axis=1)

df.to_csv(OUTPUT_CSV, index=False)
