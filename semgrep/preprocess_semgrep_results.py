#!/usr/bin/env python3

import json
import os
from pathlib import Path


def read_sarif_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def extract_results_from_sarif(sarif_data):
    results = []
    if "runs" in sarif_data and len(sarif_data["runs"]) > 0:
        run = sarif_data["runs"][0]
        if "results" in run:
            results = run["results"]
    return results


def add_validation_status(results):
    for result in results:
        result["validation_status"] = ""
    return results


def create_output_directory(input_path, output_path, sarif_file_path):
    relative_dir = sarif_file_path.parent.relative_to(input_path)
    output_subdir = output_path / relative_dir
    output_subdir.mkdir(parents=True, exist_ok=True)
    return output_subdir


def write_json_file(output_file_path, results):
    with open(output_file_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)


def process_sarif_file(sarif_file_path, input_path, output_path):
    try:
        sarif_data = read_sarif_file(sarif_file_path)
        results = extract_results_from_sarif(sarif_data)
        results = add_validation_status(results)

        output_subdir = create_output_directory(input_path, output_path, sarif_file_path)
        output_filename = sarif_file_path.name.replace(".sarif", ".json")
        output_file_path = output_subdir / output_filename

        write_json_file(output_file_path, results)

        relative_input = sarif_file_path.relative_to(input_path)
        relative_output = output_file_path.relative_to(output_path)
        return True, f"Processed: {relative_input} -> {relative_output}"

    except json.JSONDecodeError as e:
        return False, f"Error: {sarif_file_path} - Invalid JSON: {e}"
    except Exception as e:
        return False, f"Error: {sarif_file_path} - {str(e)}"


def find_sarif_files(input_path):
    for root, dirs, files in os.walk(input_path):
        for file in files:
            if file.endswith(".sarif"):
                yield Path(root) / file


def print_summary(processed_count, error_count):
    print("\n" + "="*60)
    print("Processing complete!")
    print(f"Successfully processed: {processed_count} files")
    if error_count > 0:
        print(f"Errors encountered: {error_count} files")
    print("="*60)


def preprocess_sarif_files(input_dir, output_dir):
    input_path = Path(input_dir).resolve()
    output_path = Path(output_dir).resolve()
    output_path.mkdir(parents=True, exist_ok=True)

    processed_count = 0
    error_count = 0

    for sarif_file_path in find_sarif_files(input_path):
        success, message = process_sarif_file(sarif_file_path, input_path, output_path)
        print(processed_count, " : ", message)
        if success:
            processed_count += 1
        else:
            error_count += 1

    print_summary(processed_count, error_count)


if __name__ == "__main__":
    preprocess_sarif_files("semgrep/semgrep_results", "semgrep/preprocessed-output")