import pandas as pd

INPUT_CSV = "alerts_with_category_and_apk_size_cryptoguard_3.csv"
OUTPUT_CSV = "alerts_with_category_and_apk_size_updated_cryptoguard_4.csv"

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
    
    elif "/analytics/" in artifact:
        row["code_location"] = "Analytics"
        row["3rd_party_library_name"] = "unknown"

    elif "/okhttp/" in artifact:
        row["code_location"] = "Utilities"
        row["3rd_party_library_name"] = "unknown"
    
    elif ("com/facebook/" in artifact) and (row["code_location"] != "SocialMedia"):
        if "com/facebook/appevents" in artifact:
            row["code_location"] = "SocialMedia"
            row["3rd_party_library_name"] = "Facebook-App-Links"
        else:
            row["code_location"] = "SocialMedia"
            row["3rd_party_library_name"] = "Facebook-Core"

    return row

df = df.apply(update_row, axis=1)

df.to_csv(OUTPUT_CSV, index=False)
