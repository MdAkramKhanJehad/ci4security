import os
import subprocess
from pathlib import Path

# --- Configuration ---
# Point this to the absolute path of the "1M-5M" folder on your server
# e.g., Path("/home/username/decompiled_data/1M-5M")
DECOMPILED_ROOT = Path("../decompiled_files/1M-5M") 

# Where you want the SARIF files to be saved
REPORT_DIR = Path("output_test_1M-5M")

# Temporary directory to store the CodeQL databases during the run
DB_DIR = Path("db-codeql")

# Ensure output directories exist
REPORT_DIR.mkdir(parents=True, exist_ok=True)
DB_DIR.mkdir(parents=True, exist_ok=True)

def run_command(command, description):
    """Utility to run a shell command and handle errors."""
    print(f"[*] {description}...")
    result = subprocess.run(command, shell=True, text=True, capture_output=True)
    if result.returncode != 0:
        print(f"Error during {description}:\n{result.stderr}")
        return False
    return True

def process_apks():
    # Iterate over every folder inside "1M-5M"
    count = 1
    for apk_folder in DECOMPILED_ROOT.iterdir():
        # Ensure it's a directory (e.g., 'arproductions.andrew.worklog_73')
        if not apk_folder.is_dir():
            print(f"Skipping {apk_folder.name} - not a directory.")
            continue

        apk_name = apk_folder.name
        print(f"\n{'='*50}\nProcessing {count}: {apk_name}\n{'='*50}")
        count += 1

        db_path = DB_DIR / f"{apk_name}_db"
        sarif_out = REPORT_DIR / f"{apk_name}.sarif"

        # Step 1: Create the database
        # Pointing source-root to the APK folder; CodeQL will find the 'sources' subfolder automatically.
        create_cmd = (
            f"codeql database create {db_path} "
            f"--language=java "
            f"--source-root={apk_folder} "
            f"--build-mode=none "
            f"--overwrite"
        )
        
        if not run_command(create_cmd, f"Creating DB for {apk_name}"):
            continue

        # Step 2: Analyze the database
        analyze_cmd = (
            f"codeql database analyze {db_path} "
            f"codeql/java-queries:codeql-suites/java-security-extended.qls "
            f"--format=sarif-latest "
            f"--output={sarif_out} "
            f"--threads=0" # Uses all available CPU threads
        )

        if run_command(analyze_cmd, f"Analyzing {apk_name}"):
            print(f"Successfully generated: {sarif_out}")

        # Step 3: Cleanup the database to save disk space
        # print(f"[*] Cleaning up DB for {apk_name}...")
        # subprocess.run(f"rm -rf {db_path}", shell=True)

if __name__ == "__main__":
    if not DECOMPILED_ROOT.exists():
        print(f"Error: The root directory {DECOMPILED_ROOT} does not exist.")
    else:
        process_apks()
        print("\nAll processing complete.")