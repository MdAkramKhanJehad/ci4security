import os
import json
import csv

def safe_load_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except UnicodeDecodeError:
        with open(path, "r", encoding="utf-8-sig") as f:
            return json.load(f)

def extract_app_package_name(target_fullpath):
    if not target_fullpath:
        return "N/A"
    s = target_fullpath.strip().rstrip("/")
    s = os.path.basename(s)
    if s.lower().endswith(".apk"):
        s = s[:-4]
    return s or "N/A"

def process_cryptoguard_reports(root_directory, output_csv_file):
    print(f"Starting to process files in '{root_directory}'...")
    print(f"Output CSV: {output_csv_file}")


    header = [
        "alert_description",
        "verdict",
        "artifact_location",
        "app_package_name",
        "version_code",
        "apk_category",
        "sast_tool_name",
    ]

    rows_written = 0
    files_processed = 0
    skipped_unverified = 0

    with open(output_csv_file, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(header)

        for dirpath, _, filenames in os.walk(root_directory):
            apk_category = os.path.basename(dirpath)
            sast_tool_name = "CryptoGuard"
            version_code = 0

            for filename in filenames:
                if not filename.endswith(".json"):
                    continue
                print(f"Processing file: {filename}")
                file_path = os.path.join(dirpath, filename)

                try:
                    data = safe_load_json(file_path)

                    target = data.get("Target", {}) or {}
                    app_package_name = extract_app_package_name(target.get("FullPath", ""))

                    issues = data.get("Issues", []) or []
                    for issue in issues:
                        verdict_raw = issue.get("verificationStatus", None)

                        if verdict_raw is True:
                            verdict = 1
                        elif verdict_raw is False:
                            verdict = 0
                        else:
                            skipped_unverified += 1
                            continue

                        alert_description = issue.get("Message", "N/A")
                        artifact_location = issue.get("_FullPath", "N/A")

                        writer.writerow([
                            alert_description,
                            verdict,
                            artifact_location,
                            app_package_name,
                            version_code,
                            apk_category,
                            sast_tool_name,
                        ])
                        rows_written += 1

                    files_processed += 1

                except json.JSONDecodeError:
                    print(f"Warning: Could not decode JSON: {file_path}")
                except Exception as e:
                    print(f"Error processing {file_path}: {e}")

    print("Done.")
    print(f"Files processed: {files_processed}")
    print(f"Rows written:    {rows_written}")
    print(f"Skipped (unverified/missing verificationStatus): {skipped_unverified}")
    print(f"Output CSV: {output_csv_file}")

if __name__ == "__main__":
    ROOT_FOLDER = "../cryptoguard/cryptoguard_output_preprocessed_for_manual_verification" 
    OUTPUT_FILE = "verified_cryptoguard_alerts.csv"
    process_cryptoguard_reports(ROOT_FOLDER, OUTPUT_FILE)
