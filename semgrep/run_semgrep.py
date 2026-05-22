

#!/usr/bin/env python3

import json
import subprocess
import sys
from pathlib import Path


BASE_DIR= Path("../decompiled_files")
OUTPUT_BASE_DIR = Path("./semgrep_results")
RULES_FILE= Path("semgrep_crypto_api_misuse_related_rules.json")
FORCE= False  
SUBFOLDER= "500k-1M"  


def load_rules():
    with RULES_FILE.open() as f:
        data = json.load(f)
    return next(iter(data.values()))


def build_config_flags(rules):
    flags = []
    for rule_id in rules:
        flags.extend(["--config", f"r/{rule_id}"])
    return flags


def run_semgrep(config_flags, sources_dir, sarif_output):
    cmd = [
        "semgrep", "scan",
        *config_flags,
        "--no-git-ignore",
        "--sarif",
        f"--output={sarif_output}",
        str(sources_dir),
    ]
    result = subprocess.run(cmd)
    return result.returncode == 0


def analyze_app(app_dir, output_dir, config_flags):
    app_name    = app_dir.name
    sources_dir = app_dir / "sources"

    if not sources_dir.is_dir():
        print(f"SKIP: {app_name} — no sources/ folder")
        return "skipped"

    sarif_output = output_dir / f"{app_name}.sarif"

    if sarif_output.exists() and not FORCE:
        print(f"SKIP: {app_name} — already analyzed")
        return "skipped"

    print(f"\nRUN:  {app_name}")
    print(f"Output: {sarif_output}")

    success = run_semgrep(config_flags, sources_dir, sarif_output)

    if success:
        print("-------- Done")
        return "success"
    else:
        print("-------- Failed")
        if sarif_output.exists():
            sarif_output.unlink()
        return "failed"



def run_batch(subfolder, config_flags, rules):
    target_dir = BASE_DIR / subfolder
    output_dir = OUTPUT_BASE_DIR / subfolder

    if not target_dir.is_dir():
        print(f"ERROR: Directory not found: {target_dir}")
        return

    output_dir.mkdir(parents=True, exist_ok=True)
    app_dirs = sorted([p for p in target_dir.iterdir() if p.is_dir()])

    print("->" * 60)
    print(f"Subfolder : {subfolder}")
    print(f"Target    : {target_dir}")
    print(f"Output    : {output_dir}")
    print(f"Rules     : {len(rules)}")
    print(f"Apps      : {len(app_dirs)}")
    print("->" * 60)

    total, success, skipped, failed = 0, 0, 0, 0
    failed_apps = []

    for app_dir in app_dirs:
        total += 1
        result = analyze_app(app_dir, output_dir, config_flags)

        if result == "success":
            success += 1
        elif result == "skipped":
            skipped += 1
        else:
            failed += 1
            failed_apps.append(app_dir.name)

    print("\n" + "->" * 60)
    print(f"  Total: {total}  |  Done: {success}  |  Skipped: {skipped}  |  Failed: {failed}")
    if failed_apps:
        print("\n  Failed apps:")
        for app in failed_apps:
            print(f"    - {app}")
    print("->" * 60)


if __name__ == "__main__":
    if not SUBFOLDER:
        print("ERROR: Set the SUBFOLDER variable at the top of the script.")
        sys.exit(1)

    rules = load_rules()
    config_flags = build_config_flags(rules)

    run_batch(SUBFOLDER, config_flags, rules)








# import argparse
# import json
# import subprocess
# import sys
# from pathlib import Path


# SCRIPT_DIR = Path(__file__).resolve().parent
# DEFAULT_DECOMPILED_ROOT = SCRIPT_DIR.parent / "decompiled_files"
# DEFAULT_OUTPUT_ROOT = SCRIPT_DIR / "output"
# DEFAULT_RULES_FILE = SCRIPT_DIR / "semgrep_crypto_api_misuse_related_rules.json"


# def build_parser() -> argparse.ArgumentParser:
# 	parser = argparse.ArgumentParser(
# 		description="Run Semgrep on every decompiled app inside one size bucket."
# 	)
# 	parser.add_argument(
# 		"bucket",
# 		help="Bucket folder name or path, for example '<100' or '100-500'.",
# 	)
# 	parser.add_argument(
# 		"--decompiled-root",
# 		type=Path,
# 		default=DEFAULT_DECOMPILED_ROOT,
# 		help="Root directory that contains the bucket folders.",
# 	)
# 	parser.add_argument(
# 		"--output-root",
# 		type=Path,
# 		default=DEFAULT_OUTPUT_ROOT,
# 		help="Directory where bucket-specific SARIF outputs are written.",
# 	)
# 	parser.add_argument(
# 		"--rules-file",
# 		type=Path,
# 		default=DEFAULT_RULES_FILE,
# 		help="JSON file that contains the Semgrep rule IDs to run.",
# 	)
# 	parser.add_argument(
# 		"--overwrite",
# 		action="store_true",
# 		help="Re-run analysis even when the SARIF file already exists.",
# 	)
# 	return parser



# def load_semgrep_configs(rules_file: Path) -> list[str]:
# 	if not rules_file.exists():
# 		print(f"Error: rules file does not exist: {rules_file}", file=sys.stderr)
# 		raise SystemExit(1)

# 	with rules_file.open("r", encoding="utf-8") as handle:
# 		payload = json.load(handle)

# 	rule_ids = payload.get("crypto_api_misuse_detection_rules")
# 	if not isinstance(rule_ids, list) or not rule_ids:
# 		print(
# 			f"Error: expected a non-empty crypto_api_misuse_detection_rules list in {rules_file}",
# 			file=sys.stderr,
# 		)
# 		raise SystemExit(1)

# 	configs: list[str] = []
# 	for rule_id in rule_ids:
# 		if not isinstance(rule_id, str) or not rule_id.strip():
# 			print(f"Error: invalid rule ID in {rules_file}: {rule_id!r}", file=sys.stderr)
# 			raise SystemExit(1)
# 		configs.append(f"r/{rule_id.strip()}")

# 	return configs


# def resolve_bucket_path(bucket: str, decompiled_root: Path) -> Path:
# 	bucket_path = Path(bucket)
# 	if bucket_path.is_absolute():
# 		return bucket_path
# 	if bucket_path.parts and bucket_path.parts[0] == decompiled_root.name:
# 		return bucket_path
# 	return decompiled_root / bucket_path


# def run_semgrep(sources_root: Path, output_file: Path, configs: list[str]) -> bool:
# 	command = ["semgrep", "scan"]
# 	for config in configs:
# 		command.extend(["--config", config])
# 	command.extend(
# 		[
# 			"--no-git-ignore",
# 			"--sarif",
# 			f"--output={output_file}",
# 			str(sources_root),
# 		]
# 	)

# 	print(f"Running: {' '.join(command)}")
# 	result = subprocess.run(command, text=True, capture_output=True)

# 	if result.stdout:
# 		print(result.stdout)
# 	if result.returncode != 0:
# 		if result.stderr:
# 			print(result.stderr, file=sys.stderr)
# 		print(f"Semgrep failed for {sources_root}")
# 		return False

# 	if result.stderr:
# 		print(result.stderr, file=sys.stderr)

# 	print(f"Wrote {output_file}")
# 	return True


# def process_bucket(bucket_path: Path, output_root: Path, configs: list[str], overwrite: bool) -> None:
# 	if not bucket_path.exists():
# 		print(f"Error: bucket directory does not exist: {bucket_path}", file=sys.stderr)
# 		raise SystemExit(1)

# 	if not bucket_path.is_dir():
# 		print(f"Error: bucket path is not a directory: {bucket_path}", file=sys.stderr)
# 		raise SystemExit(1)

# 	bucket_output_dir = output_root / bucket_path.name
# 	bucket_output_dir.mkdir(parents=True, exist_ok=True)

# 	app_dirs = [entry for entry in sorted(bucket_path.iterdir()) if entry.is_dir()]
# 	if not app_dirs:
# 		print(f"No app folders found in {bucket_path}")
# 		return

# 	for app_dir in app_dirs:
# 		sources_root = app_dir / "sources"
# 		if not sources_root.is_dir():
# 			print(f"Skipping {app_dir.name}: missing sources/ directory")
# 			continue

# 		output_file = bucket_output_dir / f"{app_dir.name}.sarif"
# 		if output_file.exists() and not overwrite:
# 			print(f"Skipping {app_dir.name}: {output_file} already exists")
# 			continue

# 		print(f"Analyzing {app_dir.name}")
# 		success = run_semgrep(sources_root.resolve(), output_file.resolve(), configs)
# 		if not success:
# 			continue


# def main() -> None:
# 	parser = build_parser()
# 	args = parser.parse_args()

# 	configs = load_semgrep_configs(args.rules_file.resolve())
# 	bucket_path = resolve_bucket_path(args.bucket, args.decompiled_root.resolve())
# 	process_bucket(bucket_path, args.output_root.resolve(), configs, args.overwrite)


# if __name__ == "__main__":
# 	main()
	