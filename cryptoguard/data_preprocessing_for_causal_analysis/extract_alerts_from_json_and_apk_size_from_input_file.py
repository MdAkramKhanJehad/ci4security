#!/usr/bin/env python3

import argparse
import csv
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
CRYPTOGUARD_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_PREPROCESSED_OUTPUT_DIR = CRYPTOGUARD_ROOT / "cryptoguard_output_preprocessed_for_manual_verification"
DEFAULT_APK_INPUT_CSV = REPO_ROOT / "input_files" / "shuffled_filtered_unique_latest_with-added-date.csv"
DEFAULT_OUTPUT_CSV = Path(__file__).resolve().parent / "alerts_with_apk_size_cryptoguard.csv"
RULE_MAPPING_JSON = Path(__file__).resolve().parent / "cryptoguard_rule_mapping.json"

SAST_TOOL_NAME = "CryptoGuard"

CSV_HEADER = [
    "rule_id",
    "rule_description",
    "alert_description",
    "verdict",
    "artifact_location",
    "app_package_name",
    "version_code",
    "apk_size",
    "apk_category",
    "sast_tool_name",
]


def safe_load_json(json_file_path):
    try:
        with json_file_path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except UnicodeDecodeError:
        with json_file_path.open("r", encoding="utf-8-sig") as f:
            return json.load(f)


def extract_app_package_name_and_version(json_file_path):
    base_name = json_file_path.stem
    if "_" not in base_name:
        return base_name, "N/A"

    app_package_name, version_code = base_name.rsplit("_", 1)
    return app_package_name, version_code


def load_apk_size_lookup(input_apk_csv):
    apk_size_lookup = {}

    with input_apk_csv.open("r", newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        required_columns = {"pkg_name", "vercode", "apk_size"}
        missing_columns = required_columns - set(reader.fieldnames or [])
        if missing_columns:
            missing = ", ".join(sorted(missing_columns))
            raise ValueError(f"Missing required column(s) in {input_apk_csv}: {missing}")

        for row in reader:
            pkg_name = (row.get("pkg_name") or "").strip()
            vercode = (row.get("vercode") or "").strip()
            if pkg_name and vercode:
                apk_size_lookup[(pkg_name, vercode)] = (row.get("apk_size") or "").strip()

    return apk_size_lookup


def load_rule_mapping(rule_mapping_json):
    with rule_mapping_json.open("r", encoding="utf-8") as f:
        data = json.load(f)

    return {str(rule_number): str(rule_description) for rule_number, rule_description in data.items()}


def get_alerts_from_json_data(data):
    if not isinstance(data, dict):
        return []

    issues = data.get("Issues") or []
    return issues if isinstance(issues, list) else []


def clean_csv_text(value):
    if value is None:
        return "N/A"

    return " ".join(str(value).splitlines())


def get_rule_id(issue):
    rule_number = issue.get("RuleNumber", "N/A")
    if rule_number in ("", None):
        return "N/A"

    return str(rule_number)


def get_rule_description(issue, rule_mapping):
    rule_id = get_rule_id(issue)
    if rule_id in rule_mapping:
        return rule_mapping[rule_id]

    return clean_csv_text(issue.get("RuleDesc", "N/A"))


def should_include_alert(verdict):
    return verdict in (True, False)


def build_alert_row(issue, json_file_path, apk_size_lookup, rule_mapping):
    app_package_name, version_code = extract_app_package_name_and_version(json_file_path)
    rule_id = get_rule_id(issue)

    return {
        "rule_id": rule_id,
        "rule_description": get_rule_description(issue, rule_mapping),
        "alert_description": clean_csv_text(
            issue.get("Message")
            or issue.get("Description")
            or issue.get("RuleDesc")
            or "N/A"
        ),
        "verdict": issue.get("verificationStatus", ""),
        "artifact_location": issue.get("_FullPath", "N/A"),
        "app_package_name": app_package_name,
        "version_code": version_code,
        "apk_size": apk_size_lookup.get((app_package_name, version_code), ""),
        "apk_category": json_file_path.parent.name,
        "sast_tool_name": SAST_TOOL_NAME,
    }


def process_cryptoguard_reports(preprocessed_output_dir, input_apk_csv, output_csv_file):
    preprocessed_output_dir = Path(preprocessed_output_dir)
    input_apk_csv = Path(input_apk_csv)
    output_csv_file = Path(output_csv_file)

    print(f"Starting to process CryptoGuard JSON files in: {preprocessed_output_dir}")
    print(f"APK metadata CSV: {input_apk_csv}")
    print(f"Output CSV: {output_csv_file}")

    apk_size_lookup = load_apk_size_lookup(input_apk_csv)
    rule_mapping = load_rule_mapping(RULE_MAPPING_JSON)
    output_csv_file.parent.mkdir(parents=True, exist_ok=True)

    files_processed = 0
    rows_written = 0
    skipped_unvalidated = 0
    json_decode_errors = 0
    missing_apk_size = 0

    with output_csv_file.open("w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=CSV_HEADER)
        writer.writeheader()

        for json_file_path in sorted(preprocessed_output_dir.rglob("*.json")):
            try:
                data = safe_load_json(json_file_path)
            except json.JSONDecodeError:
                print(f"Warning: Could not decode JSON: {json_file_path}")
                json_decode_errors += 1
                continue

            files_processed += 1
            for issue in get_alerts_from_json_data(data):
                if not isinstance(issue, dict):
                    continue

                verdict = issue.get("verificationStatus", "")
                if not should_include_alert(verdict):
                    skipped_unvalidated += 1
                    continue

                row = build_alert_row(issue, json_file_path, apk_size_lookup, rule_mapping)
                if row["apk_size"] == "":
                    missing_apk_size += 1

                writer.writerow(row)
                rows_written += 1

    matched_apk_size = rows_written - missing_apk_size

    print("Done.")
    print(f"Files processed: {files_processed}")
    print(f"Rows written: {rows_written}")
    print(f"Skipped unvalidated alerts: {skipped_unvalidated}")
    print(f"JSON decode errors: {json_decode_errors}")
    print(f"Added apk_size for {matched_apk_size}/{rows_written} alerts.")
    print(f"Saved updated file to: {output_csv_file}")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Extract manually validated CryptoGuard alerts and attach APK size."
    )
    parser.add_argument(
        "--preprocessed-output-dir",
        default=DEFAULT_PREPROCESSED_OUTPUT_DIR,
        help="Directory containing manually validated CryptoGuard JSON files.",
    )
    parser.add_argument(
        "--input-apk-csv",
        default=DEFAULT_APK_INPUT_CSV,
        help="CSV containing pkg_name, vercode, and apk_size columns.",
    )
    parser.add_argument(
        "--output-csv",
        default=DEFAULT_OUTPUT_CSV,
        help="Output CSV file path.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    process_cryptoguard_reports(args.preprocessed_output_dir, args.input_apk_csv, args.output_csv)
