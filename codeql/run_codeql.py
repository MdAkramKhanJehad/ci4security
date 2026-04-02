import os
import subprocess
from pathlib import Path

DECOMPILED_ROOT = Path("../decompiled_files/500k-1M") 
REPORT_DIR = Path("output/500k-1M")
DB_DIR_PART_1 = Path("db-codeql")
DB_DIR_PART_2 = Path("../../../../spl/akram/ci4security/codeql/db-codeql")

REPORT_DIR.mkdir(parents=True, exist_ok=True)
DB_DIR_PART_2.mkdir(parents=True, exist_ok=True)


def run_command(command, description):
    print(f"{description}...")
    result = subprocess.run(command, text=True, capture_output=True)
    if result.returncode != 0:
        print(f"Error during {description}:\n{result.stderr}")
        return False
    return True


def process_apks():
    count = 1

    for apk_folder in DECOMPILED_ROOT.iterdir():

        if not apk_folder.is_dir():
            print(f"Skipping {apk_folder.name} - not a directory.")
            continue

        apk_name = apk_folder.name
        print(f"\n{'='*50}\nProcessing {count}: {apk_name}\n{'='*50}")
        count += 1

        db_path_part_1 = DB_DIR_PART_1 / f"{apk_name}_db"
        db_path_part_2 = DB_DIR_PART_2 / f"{apk_name}_db"
        sarif_out = REPORT_DIR / f"{apk_name}.sarif"

        if (db_path_part_2.exists() and db_path_part_2.is_dir()):
            print(f"Database already exists at {db_path_part_2}. Skipping creation.")
            path_for_db = db_path_part_2
        elif (db_path_part_1.exists() and db_path_part_1.is_dir()):
            print(f"Database exists at {db_path_part_1}. Using existing database.")
            path_for_db = db_path_part_1
        else:
            create_cmd = [
                "codeql", "database", "create", str(db_path_part_2),
                "--language=java",
                f"--source-root={apk_folder}",
                "--build-mode=none",
                "--overwrite"
            ]
            
            if not run_command(create_cmd, f"Creating DB for {apk_name}"):
                continue

        analyze_cmd = [
            "codeql", "database", "analyze", str(path_for_db),
            "codeql/java-queries:codeql-suites/java-security-extended.qls",
            "codeql/java-queries:codeql-suites/java-security-experimental.qls",
            "--format=sarif-latest",
            f"--output={sarif_out}",
            "--sarif-add-snippets",
            "--threads=0"
        ]

        if run_command(analyze_cmd, f"Analyzing {apk_name}"):
            print(f"Successfully generated: {sarif_out}")

        # print(f"[*] Cleaning up DB for {apk_name}...")
        # subprocess.run(f"rm -rf {db_path}", shell=True)

if __name__ == "__main__":
    if not DECOMPILED_ROOT.exists():
        print(f"Error: The root directory {DECOMPILED_ROOT} does not exist.")
    else:
        process_apks()
        print("\nAll processing complete.")