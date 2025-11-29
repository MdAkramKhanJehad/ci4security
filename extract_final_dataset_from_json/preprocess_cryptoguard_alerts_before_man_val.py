import os
import json

INPUT_ROOT = os.path.abspath("../cryptoguard_output")
OUTPUT_ROOT = os.path.abspath("../cryptoguard_output_preprocessed_for_manual_verification")


def normalize_fullpath(fullpath):
    if not isinstance(fullpath, str):
        return fullpath

    apk_marker = ".apk/"
    idx = fullpath.find(apk_marker)
    if idx != -1:
        fullpath = fullpath[idx + len(apk_marker):]
    if fullpath.endswith(".class"):
        fullpath = fullpath[:-6] + ".java"

    return fullpath


def process_issues_field(data):
    issues = data.get("Issues")

    if isinstance(issues, list):
        data["total_issues"] = len(issues)

        for issue in issues:
            if isinstance(issue, dict) and "_FullPath" in issue:
                issue["_FullPath"] = normalize_fullpath(issue["_FullPath"])
    else:
        data["total_issues"] = 0


def add_verification_status(data):
    issues = data.get("Issues")
    if isinstance(issues, list):
        for issue in issues:
            if isinstance(issue, dict):
                issue["verificationStatus"] = ""


def process_single_json_file(input_path, output_path):
    try:
        with open(input_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"Failed to read JSON {input_path}: {e}")
        return

    process_issues_field(data)
    add_verification_status(data)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    try:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Failed to write JSON {output_path}: {e}")


def process_all_jsons():
    counter = 0

    for dirpath, dirnames, filenames in os.walk(INPUT_ROOT):
        for filename in filenames:
            if not filename.lower().endswith(".json"):
                continue

            input_path = os.path.join(dirpath, filename)
            rel_path = os.path.relpath(input_path, INPUT_ROOT)
            output_path = os.path.join(OUTPUT_ROOT, rel_path)
            process_single_json_file(input_path, output_path)
            
            counter += 1

        print(f"Processed {counter} JSON files in directory: {dirpath}")


def main():
    process_all_jsons()

if __name__ == "__main__":
    main()
