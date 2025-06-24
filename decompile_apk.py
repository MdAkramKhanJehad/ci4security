import os
import csv
import subprocess
from pathlib import Path


APK_ROOT = Path("downloaded_apk")
OUTPUT_ROOT = Path("decompiled_files")
LOG_FILE = Path("decompile_failures.csv")


def initialize_log_file():
    if not LOG_FILE.exists():
        with open(LOG_FILE, mode='w', newline='') as log:
            writer = csv.writer(log)
            writer.writerow(["apk_path", "output_path", "reason"])


def is_already_decompiled(apk_path):
    relative_path = apk_path.relative_to(APK_ROOT)
    output_dir = OUTPUT_ROOT / relative_path.parent / apk_path.stem
    return output_dir.exists() and any(output_dir.iterdir())


def get_output_directory(apk_path):
    relative_path = apk_path.relative_to(APK_ROOT)
    return OUTPUT_ROOT / relative_path.parent / apk_path.stem


def log_failure(apk_path, output_dir, reason):
    with open(LOG_FILE, mode='a', newline='') as log:
        writer = csv.writer(log)
        writer.writerow([str(apk_path), str(output_dir), reason])

 
def decompile_apk(apk_path, output_dir):
    output_dir.mkdir(parents=True, exist_ok=True)
    try:
        result = subprocess.run(
            ["jadx", "-d", str(output_dir), str(apk_path)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

        if any(output_dir.iterdir()):
            return True
        else:
            log_failure(apk_path, output_dir, "Empty output directory after jadx run")
            return False

    except Exception as e:
        log_failure(apk_path, output_dir, f"Crash: {e}")
        return False


def decompile_all_apks():
    initialize_log_file()
    apk_paths = list(APK_ROOT.rglob("*.apk"))
    decompiled_count = 0
    # testCounter = 1

    for apk_path in apk_paths:
        if is_already_decompiled(apk_path):
            print(f"Skipping already decompiled: {apk_path}")
            continue

        output_dir = get_output_directory(apk_path)
        print(f"Decompiling #{decompiled_count}: {apk_path} -> {output_dir}")

        success = decompile_apk(apk_path, output_dir)
        if success:
            decompiled_count += 1
            # testCounter += 1

            # if testCounter == 3:
            #     return
        else:
            print(f"partial or failed decompile: {apk_path}")
        

    print(f"\nTotal APKs successfully decompiled: {decompiled_count}")


if __name__ == '__main__':
    decompile_all_apks()
