#!/usr/bin/env python3

import argparse
import csv
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
COGNICRYPT_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_PREPROCESSED_OUTPUT_DIR = COGNICRYPT_ROOT / "final_out_reports"
DEFAULT_APK_INPUT_CSV = REPO_ROOT / "input_files" / "shuffled_filtered_unique_latest_with-added-date.csv"
DEFAULT_OUTPUT_CSV = Path(__file__).resolve().parent / "alerts_with_apk_size_cognicrypt.csv"

SAST_TOOL_NAME = "CogniCrypt"

CSV_HEADER = [
    "ruleId",
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


def get_alerts_from_json_data(data):
    if not isinstance(data, dict):
        return []

    runs = data.get("runs") or []
    if not runs or not isinstance(runs[0], dict):
        return []

    results = runs[0].get("results") or []
    return results if isinstance(results, list) else []


def get_first_location_uri(alert):
    locations = alert.get("locations") or []
    if not locations:
        return "N/A"

    first_location = locations[0] or {}
    return (
        first_location.get("physicalLocation", {})
        .get("artifactLocation", {})
        .get("uri", "N/A")
    )


def clean_csv_text(value):
    if value is None:
        return "N/A"

    return " ".join(str(value).splitlines())


def get_verdict(alert):
    properties = alert.get("properties") or {}
    return properties.get("verificationStatus", "")


def should_include_alert(verdict):
    return verdict in (True, False)


def build_alert_row(alert, json_file_path, apk_size_lookup):
    app_package_name, version_code = extract_app_package_name_and_version(json_file_path)

    return {
        "ruleId": alert.get("ruleId", "N/A"),
        "alert_description": clean_csv_text(alert.get("message", {}).get("text", "N/A")),
        "verdict": get_verdict(alert),
        "artifact_location": get_first_location_uri(alert),
        "app_package_name": app_package_name,
        "version_code": version_code,
        "apk_size": apk_size_lookup.get((app_package_name, version_code), ""),
        "apk_category": json_file_path.parent.name,
        "sast_tool_name": SAST_TOOL_NAME,
    }


def process_cognicrypt_reports(preprocessed_output_dir, input_apk_csv, output_csv_file):
    preprocessed_output_dir = Path(preprocessed_output_dir)
    input_apk_csv = Path(input_apk_csv)
    output_csv_file = Path(output_csv_file)

    print(f"Starting to process CogniCrypt JSON files in: {preprocessed_output_dir}")
    print(f"APK metadata CSV: {input_apk_csv}")
    print(f"Output CSV: {output_csv_file}")

    apk_size_lookup = load_apk_size_lookup(input_apk_csv)
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
            for alert in get_alerts_from_json_data(data):
                if not isinstance(alert, dict):
                    continue

                verdict = get_verdict(alert)
                if not should_include_alert(verdict):
                    skipped_unvalidated += 1
                    continue

                row = build_alert_row(alert, json_file_path, apk_size_lookup)
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
        description="Extract manually validated CogniCrypt alerts and attach APK size."
    )
    parser.add_argument(
        "--preprocessed-output-dir",
        default=DEFAULT_PREPROCESSED_OUTPUT_DIR,
        help="Directory containing manually validated CogniCrypt JSON files.",
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
    process_cognicrypt_reports(args.preprocessed_output_dir, args.input_apk_csv, args.output_csv)
