import os
import subprocess
import json
import time
from filelock import FileLock


INPUT_DIR = os.path.abspath("../decompiled_files")
OUTPUT_DIR = os.path.abspath("./semgrep_results")
TRACKING_FILE = os.path.abspath("analysis_tracker.json")
LOCK_FILE = os.path.abspath("global_process.lock")
TIMEOUT_SECONDS = 3600


def get_target_folders(root):
    targets = []
    if not os.path.exists(root):
        return []

    for bucket in os.listdir(root):
        bucket_path = os.path.join(root, bucket)
        if os.path.isdir(bucket_path):
            for apk_folder in os.listdir(bucket_path):
                full_path = os.path.join(bucket_path, apk_folder)
                if os.path.isdir(full_path):
                    targets.append(full_path)

    return targets


def _load_tracker():
    if os.path.exists(TRACKING_FILE):
        with open(TRACKING_FILE, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except Exception:
                return {}
                
    return {}


def _save_tracker(data):
    with open(TRACKING_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


def claim_for_processing(apk_path):
    
    with FileLock(LOCK_FILE):
        data = _load_tracker()
        status = data.get(apk_path, {}).get("status")
        if status in ["processing", "completed"]:
            return False

        data[apk_path] = { "status": "processing", "last_update": time.strftime("%Y-%m-%d %H:%M:%S"), "error": None}
        _save_tracker(data)
        return True


def update_status(apk_path, status, error=None):
    with FileLock(LOCK_FILE):
        data = _load_tracker()
        data[apk_path] = { "status": status, "last_update": time.strftime("%Y-%m-%d %H:%M:%S"), "error": error}
        _save_tracker(data)


def run_analysis(apk_folder):
    rel_path = os.path.relpath(apk_folder, INPUT_DIR)   
    bucket = rel_path.split(os.sep, 1)[0]
    apk_name = os.path.basename(apk_folder)

    target_out_dir = os.path.join(OUTPUT_DIR, bucket)
    os.makedirs(target_out_dir, exist_ok=True)

    output_file_name = f"{apk_name}.json"
    final_out = os.path.join(target_out_dir, output_file_name)
    tmp_out = os.path.join(target_out_dir, f"{output_file_name}.tmp.{os.getpid()}")

    if not claim_for_processing(apk_folder):
        return

    print(f"Starting: {bucket}/{apk_name}")

    docker_cmd = [
        "docker", "run", "--rm",
        "-v", f"{apk_folder}:/src:ro",
        "-v", f"{target_out_dir}:/out",
        "semgrep/semgrep:latest",
        "semgrep", "scan",
        "--config", "auto",
        # "--metrics", "off",
        "/src",
        "--json",
        "--output", f"/out/{os.path.basename(tmp_out)}"
    ]

    try:
        if os.path.exists(tmp_out):
            os.remove(tmp_out)

        subprocess.run(docker_cmd, timeout=TIMEOUT_SECONDS, check=True, text=True, capture_output=True)

        if os.path.exists(tmp_out) and os.path.getsize(tmp_out) > 0:
            os.replace(tmp_out, final_out)
            update_status(apk_folder, "completed")
            print(f"Success: {bucket}/{apk_name}")
        else:
            if os.path.exists(tmp_out):
                os.remove(tmp_out)
            update_status(apk_folder, "failed", "No output JSON produced")
            print(f"Failed: {bucket}/{apk_name} - No output JSON produced")

    except subprocess.TimeoutExpired:
        if os.path.exists(tmp_out):
            os.remove(tmp_out)
        update_status(apk_folder, "failed", "Timeout (1 Hour)")
        print(f"Timeout: {bucket}/{apk_name}")

    except subprocess.CalledProcessError as e:
        if os.path.exists(tmp_out):
            os.remove(tmp_out)
        err = (e.stderr or str(e))[:2000]
        update_status(apk_folder, "failed", err)
        print(f"Failed: {bucket}/{apk_name} - {err}")

    except Exception as e:
        if os.path.exists(tmp_out):
            os.remove(tmp_out)
        update_status(apk_folder, "failed", str(e))
        print(f"Failed: {bucket}/{apk_name} - {str(e)}")


def main():
    folders = get_target_folders(INPUT_DIR)
    for folder in folders:
        run_analysis(folder)


if __name__ == "__main__":
    main()
