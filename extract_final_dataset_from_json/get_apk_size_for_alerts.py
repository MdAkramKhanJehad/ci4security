import pandas as pd

INPUT_APK_CSV = "../input_files/shuffled_filtered_unique_latest_with-added-date.csv"
ALERTS_CSV = "alerts_with_category_cryptoguard_2.csv"
OUTPUT_CSV = "alerts_with_category_and_apk_size_cryptoguard_3.csv"

apk_df = pd.read_csv(INPUT_APK_CSV, dtype=str)
alerts_df = pd.read_csv(ALERTS_CSV, dtype=str)

apk_df_subset = apk_df[["pkg_name", "vercode", "apk_size"]].copy()

merged_df = alerts_df.merge(
    apk_df_subset,
    how="left",
    left_on=["app_package_name", "version_code"],
    right_on=["pkg_name", "vercode"]
)

alerts_df["apk_size"] = merged_df["apk_size"]

alerts_df.to_csv(OUTPUT_CSV, index=False)

matched = alerts_df["apk_size"].notna().sum()
total = len(alerts_df)
print(f"Added apk_size for {matched}/{total} alerts.")
print(f"Saved updated file to: {OUTPUT_CSV}")
