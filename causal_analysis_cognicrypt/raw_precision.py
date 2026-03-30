import pandas as pd


alerts_df = pd.read_csv("alerts_with_category_with_apk_size_updated.csv")
alerts_df = alerts_df[~alerts_df["code_location"].str.contains("obfuscated", case=False, na=False)].copy()

alerts_df["verdict"] = alerts_df["verdict"].astype(int)
alerts_df["is_third_party"] = (~alerts_df["code_location"].isin(["developer_written"])).astype(int)


def compute_tp_fp_precision(input_df: pd.DataFrame, verdict_column: str = "verdict"):
    true_positives = int((input_df[verdict_column] == 1).sum())
    false_positives = int((input_df[verdict_column] == 0).sum())
    total_labeled_alerts = true_positives + false_positives
    precision = (true_positives / total_labeled_alerts) if total_labeled_alerts > 0 else float("nan")
    return true_positives, false_positives, precision


def print_split_summary(split_name: str, split_df: pd.DataFrame):
    true_positives, false_positives, precision = compute_tp_fp_precision(split_df)
    total_alerts = len(split_df)

    print(f"\n------ {split_name} ------")
    print(f"Total alerts: {total_alerts}")
    print(f"True positives (verdict=1):  {true_positives}")
    print(f"False positives (verdict=0): {false_positives}")
    print(f"Precision: {precision:.4f}")


def downsample_third_party_to_match_developer( full_df, random_state):
    developer_written_df = full_df[full_df["is_third_party"] == 0].copy()
    third_party_df = full_df[full_df["is_third_party"] == 1].copy()

    target_count = len(developer_written_df)
    if target_count == 0:
        raise ValueError("No developer-written alerts found (is_third_party=0).")

    if len(third_party_df) < target_count:
        raise ValueError(
            f"Cannot downsample third-party alerts to {target_count} because only "
            f"{len(third_party_df)} third-party alerts exist."
        )

    third_party_downsampled_df = third_party_df.sample( n=target_count, replace=False, random_state=random_state )

    combined_balanced_df = pd.concat([developer_written_df, third_party_downsampled_df], axis=0)
    combined_balanced_df = combined_balanced_df.sample(frac=1, random_state=random_state).reset_index(drop=True)
    return combined_balanced_df, developer_written_df, third_party_downsampled_df


def upsample_developer_to_match_third_party_bootstrap( full_df, random_state ):

    developer_written_df = full_df[full_df["is_third_party"] == 0].copy()
    third_party_df = full_df[full_df["is_third_party"] == 1].copy()

    target_count = len(third_party_df)
    
    developer_written_upsampled_df = developer_written_df.sample(
        n=target_count, replace=True, random_state=random_state
    )

    combined_balanced_df = pd.concat([developer_written_upsampled_df, third_party_df], axis=0)
    combined_balanced_df = combined_balanced_df.sample(frac=1, random_state=random_state).reset_index(drop=True)
    return combined_balanced_df, developer_written_upsampled_df, third_party_df


print_split_summary("Overall (all alerts)", alerts_df)

developer_written_alerts_df = alerts_df[alerts_df["is_third_party"] == 0].copy()
print_split_summary("Developer-written only (is_third_party=0)", developer_written_alerts_df)

third_party_alerts_df = alerts_df[alerts_df["is_third_party"] == 1].copy()
print_split_summary("Third-party only (is_third_party=1)", third_party_alerts_df)

down_balanced_df, dev_all_df, third_party_down_df = downsample_third_party_to_match_developer( alerts_df, 42)
print_split_summary("Balanced A (Downsample third-party to match developer count) - Combined", down_balanced_df)
print_split_summary("Balanced A - Developer-written (kept all)", dev_all_df)
print_split_summary("Balanced A - Third-party (downsampled)", third_party_down_df)


up_balanced_df, dev_up_df, third_party_all_df = upsample_developer_to_match_third_party_bootstrap( alerts_df, 42)
print_split_summary("Balanced B (Bootstrap upsample developer to match third-party count) - Combined", up_balanced_df)
print_split_summary("Balanced B - Developer-written (bootstrapped)", dev_up_df)
print_split_summary("Balanced B - Third-party (kept all)", third_party_all_df)
