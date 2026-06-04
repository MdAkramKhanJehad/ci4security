#!/usr/bin/env python3

import argparse
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = Path(__file__).resolve().parents[2]

sys.path.insert(0, str(REPO_ROOT))

from utils.shared_classifier_alert_util import classify_alerts


DEFAULT_INPUT_CSV = SCRIPT_DIR / "alerts_with_apk_size_cognicrypt.csv"
DEFAULT_OUTPUT_CSV = REPO_ROOT / "causal_analysis_cognicrypt" / "alerts_with_lib_category_and_apk_size_cognicrypt.csv"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Classify CogniCrypt alerts as developer-written code or third-party libraries."
    )
    parser.add_argument("--input-csv", default=DEFAULT_INPUT_CSV)
    parser.add_argument("--output-csv", default=DEFAULT_OUTPUT_CSV)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    classify_alerts(args.input_csv, args.output_csv)
