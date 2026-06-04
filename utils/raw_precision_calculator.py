#!/usr/bin/env python3

import csv
import math
import random
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
RANDOM_STATE = 42

COGNICRYPT_INPUT_FILE = REPO_ROOT / "causal_analysis_cognicrypt" / "alerts_with_lib_category_and_apk_size_cognicrypt.csv"
CRYPTOGUARD_INPUT_FILE = REPO_ROOT / "causal_analysis_cryptoguard" / "alerts_with_lib_category_and_apk_size_cryptoguard.csv"
SEMGREP_INPUT_FILE = REPO_ROOT / "causal_analysis_semgrep" / "alerts_with_lib_category_and_apk_size_semgrep.csv"
CODEQL_INPUT_FILE = REPO_ROOT / "causal_analysis_codeql" / "alerts_with_lib_category_and_apk_size_codeql.csv"

TOOL_INPUT_FILES = [
    ("CogniCrypt", COGNICRYPT_INPUT_FILE),
    ("CryptoGuard", CRYPTOGUARD_INPUT_FILE),
    ("Semgrep", SEMGREP_INPUT_FILE),
    ("CodeQL", CODEQL_INPUT_FILE),
]


def normalize_verdict(value):
    normalized = str(value).strip().lower()

    if normalized in {"1", "true"}:
        return 1
    if normalized in {"0", "false"}:
        return 0

    raise ValueError(f"Unsupported verdict value: {value!r}")


def load_alert_rows(input_file):
    with input_file.open("r", newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        fieldnames = set(reader.fieldnames or [])
        required_columns = {"verdict", "code_location"}
        missing_columns = required_columns - fieldnames

        if missing_columns:
            missing = ", ".join(sorted(missing_columns))
            raise ValueError(f"Missing required column(s) in {input_file}: {missing}")

        rows = []
        for row in reader:
            code_location = (row.get("code_location") or "").strip()
            if "obfuscated" in code_location.lower():
                continue

            row["verdict"] = normalize_verdict(row.get("verdict"))
            row["is_third_party"] = 0 if code_location == "developer_written" else 1
            rows.append(row)

    return rows


def compute_tp_fp_precision(rows):
    true_positives = sum(1 for row in rows if row["verdict"] == 1)
    false_positives = sum(1 for row in rows if row["verdict"] == 0)
    total_labeled_alerts = true_positives + false_positives
    precision = true_positives / total_labeled_alerts if total_labeled_alerts > 0 else math.nan
    return true_positives, false_positives, precision


def format_precision(precision):
    if math.isnan(precision):
        return "nan"

    return f"{precision:.4f}"


def print_split_summary(split_name, rows):
    true_positives, false_positives, precision = compute_tp_fp_precision(rows)

    print(f"\n------ {split_name} ------")
    print(f"Total alerts: {len(rows)}")
    print(f"True positives (verdict=1):  {true_positives}")
    print(f"False positives (verdict=0): {false_positives}")
    print(f"Precision: {format_precision(precision)}")


def split_by_provenance(rows):
    developer_written_rows = [row for row in rows if row["is_third_party"] == 0]
    third_party_rows = [row for row in rows if row["is_third_party"] == 1]
    return developer_written_rows, third_party_rows


def downsample_third_party_to_match_developer(rows, random_state):
    developer_written_rows, third_party_rows = split_by_provenance(rows)
    target_count = len(developer_written_rows)

    if target_count == 0:
        raise ValueError("No developer-written alerts found (is_third_party=0).")

    if len(third_party_rows) < target_count:
        raise ValueError(
            f"Cannot downsample third-party alerts to {target_count} because only "
            f"{len(third_party_rows)} third-party alerts exist."
        )

    rng = random.Random(random_state)
    third_party_downsampled_rows = rng.sample(third_party_rows, target_count)
    combined_balanced_rows = developer_written_rows + third_party_downsampled_rows
    rng.shuffle(combined_balanced_rows)
    return combined_balanced_rows, developer_written_rows, third_party_downsampled_rows


def upsample_developer_to_match_third_party_bootstrap(rows, random_state):
    developer_written_rows, third_party_rows = split_by_provenance(rows)
    target_count = len(third_party_rows)

    if len(developer_written_rows) == 0:
        raise ValueError("No developer-written alerts found (is_third_party=0).")

    rng = random.Random(random_state)
    developer_written_upsampled_rows = rng.choices(developer_written_rows, k=target_count)
    combined_balanced_rows = developer_written_upsampled_rows + third_party_rows
    rng.shuffle(combined_balanced_rows)
    return combined_balanced_rows, developer_written_upsampled_rows, third_party_rows


def print_tool_precision(tool_name, input_file):
    rows = load_alert_rows(input_file)
    developer_written_rows, third_party_rows = split_by_provenance(rows)

    print(f"\n\n -> {tool_name} ================")
    print(f"Input file: {input_file}")
    print_split_summary("Overall (all alerts)", rows)
    print_split_summary("Developer-written only (is_third_party=0)", developer_written_rows)
    print_split_summary("Third-party only (is_third_party=1)", third_party_rows)

    try:
        down_balanced_rows, dev_all_rows, third_party_down_rows = downsample_third_party_to_match_developer(
            rows, RANDOM_STATE
        )
        print_split_summary("Balanced A (Downsample third-party to match developer count) - Combined", down_balanced_rows)
        print_split_summary("Balanced A - Developer-written (kept all)", dev_all_rows)
        print_split_summary("Balanced A - Third-party (downsampled)", third_party_down_rows)
    except ValueError as error:
        print(f"\n------ Balanced A (Downsample third-party to match developer count) ------")
        print(f"Skipped: {error}")

    try:
        up_balanced_rows, dev_up_rows, third_party_all_rows = upsample_developer_to_match_third_party_bootstrap(
            rows, RANDOM_STATE
        )
        print_split_summary("Balanced B (Bootstrap upsample developer to match third-party count) - Combined", up_balanced_rows)
        print_split_summary("Balanced B - Developer-written (bootstrapped)", dev_up_rows)
        print_split_summary("Balanced B - Third-party (kept all)", third_party_all_rows)
    except ValueError as error:
        print(f"\n------ Balanced B (Bootstrap upsample developer to match third-party count) ------")
        print(f"Skipped: {error}")


def main():
    for tool_name, input_file in TOOL_INPUT_FILES:
        print_tool_precision(tool_name, input_file)


if __name__ == "__main__":
    main()
