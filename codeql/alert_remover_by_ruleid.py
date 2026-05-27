#!/usr/bin/env python3

import json
import glob
import os

ROOT_DIR = "codeql/preprocessed-output"
RULE_ID = "java/disabled-certificate-revocation-checking"  
DRY_RUN = True                           


def process_file(json_path):
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        return 0

    before = len(data)
    data = [
        alert for alert in data
        if not (isinstance(alert, dict) and alert.get("ruleId") == RULE_ID)
    ]
    removed = before - len(data)

    if removed > 0 and not DRY_RUN:
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    return removed


def main():
    json_files = sorted(glob.glob(os.path.join(ROOT_DIR, "**/*.json"), recursive=True))

    total_removed = 0
    files_affected = 0

    print(f"Root: {ROOT_DIR}")
    print(f"Rule ID: {RULE_ID}")
    print(f"Dry run: {DRY_RUN}")
    print(f"Files found: {len(json_files)}\n")

    for json_path in json_files:
        removed = process_file(json_path)

        if removed > 0:
            files_affected += 1
            total_removed += removed
            rel_path = os.path.relpath(json_path, ROOT_DIR)
            action = "Would remove" if DRY_RUN else "Removed"
            print(f"{rel_path} | {action} {removed}")

    print("\nSummary")
    print(f"Files affected: {files_affected}")
    print(f"Total alerts: {total_removed}")

    if DRY_RUN:
        print("No files modified. Set DRY_RUN = False to actually remove.")


if __name__ == "__main__":
    main()