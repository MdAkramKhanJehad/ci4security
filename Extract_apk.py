import csv
import os
import random
import requests
from pathlib import Path
from collections import defaultdict
from datetime import datetime
from itertools import islice

INPUT_FILE = 'input_files/shuffled_filtered_unique_latest_with-added-date.csv'
API_KEY_FILE = 'api_key.txt'
OUTPUT_DIR = 'downloaded_apks'
OBFUSCATED_FILE = 'obfuscated_apks.csv'
LOG_FILE = 'download_log.csv'
MAX_DOWNLOADS = 1000
CHUNK_SIZE = 60000

STRATA = {
    '<100': (0, 100),
    '100-500': (100, 500),
    '500-1k': (500, 1000),
    '1k-5k': (1000, 5000),
    '5k-10k': (5000, 10000),
    '10k-50k': (10000, 50000),
    '50k-100k': (50000, 100000),
    '100k-500k': (100000, 500000),
    '500k-1M': (500000, 1000000),
    '1M-5M': (1000000, 5000000),
    '>5M': (5000000, float('inf')),
}
SAMPLES_PER_STRATUM = MAX_DOWNLOADS // len(STRATA)

def read_api_key():
    with open(API_KEY_FILE) as f:
        return f.read().strip()

def ensure_dirs():
    Path(OUTPUT_DIR).mkdir(exist_ok=True)
    for label in STRATA:
        Path(f'{OUTPUT_DIR}/{label}').mkdir(parents=True, exist_ok=True)

def parse_download_count(text):
    text = text.replace('+', '').strip()
    if 'M' in text:
        return int(float(text.replace('M', '')) * 1_000_000)
    if 'k' in text:
        return int(float(text.replace('k', '')) * 1_000)
    return int(text.replace(',', ''))

def get_stratum(download_count):
    for label, (low, high) in STRATA.items():
        if low <= download_count < high:
            return label
    return None

def get_metadata(apikey, pkg_name, vercode):
    url = f'https://androzoo.uni.lu/api/get_gp_metadata/{pkg_name}/{vercode}'
    params = {'apikey': apikey}
    try:
        r = requests.get(url, params=params, timeout=20)
        if r.status_code == 200 and 'application/json' in r.headers.get('Content-Type', ''):
            return r.json()
        else:
            print(f"[Metadata Fetch Failed] {pkg_name} (vercode: {vercode}) - Status: {r.status_code}")
            return None
    except Exception as e:
        print(f"[Metadata Request Error] {pkg_name} - {e}")
        return None

def is_on_playstore(pkg_name):
    url = f'https://play.google.com/store/apps/details?id={pkg_name}'
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        r = requests.get(url, headers=headers, timeout=10)
        return r.status_code == 200 and "Google Play" in r.text
    except Exception as e:
        print(f"[Play Store Check Error] {pkg_name} - {e}")
        return False

def download_apk(apikey, sha256, path, pkg_name):
    url = 'https://androzoo.uni.lu/api/download'
    params = {'apikey': apikey, 'sha256': sha256}
    try:
        r = requests.get(url, params=params, stream=True, timeout=60)
        if r.status_code == 200:
            with open(path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
            return True
        else:
            print(f"[Download Failed] {pkg_name} ({sha256}) - Status: {r.status_code}")
            return False
    except Exception as e:
        print(f"[Download Error] {pkg_name} ({sha256}) - {e}")
        return False

def load_obfuscated_packages(path):
    obf = set()
    with open(path, newline='') as f:
        reader = csv.reader(f)
        next(reader)
        for row in reader:
            obf.add(row[0].strip())
    return obf

def save_log(log_rows):
    keys = ['sha256', 'pkg_name', 'versioncode', 'market', 'numDownloads', 'apk_size', 'strata']
    file_exists = os.path.exists(LOG_FILE)
    with open(LOG_FILE, 'a', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        if not file_exists:
            writer.writeheader()
        for row in log_rows:
            writer.writerow(row)

def load_csv_in_chunks(file_path, chunk_size):
    with open(file_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        while True:
            chunk = list(islice(reader, chunk_size))
            if not chunk:
                break
            yield chunk

def main():
    print(f"[{datetime.now()}] Starting APK downloader...")
    ensure_dirs()
    apikey = read_api_key()
    obfuscated = load_obfuscated_packages(OBFUSCATED_FILE)
    strata_counts = defaultdict(int)
    log_rows = []
    downloaded = 0
    skip_count = 0

    for chunk in load_csv_in_chunks(INPUT_FILE, CHUNK_SIZE):
        random.shuffle(chunk)

        for row in chunk:
            sha256 = row['sha256']
            pkg_name = row['pkg_name']
            vercode = row['vercode']
            market = row['markets']
            apk_size = row['apk_size']

            if not vercode.isdigit():
                continue
            if pkg_name in obfuscated:
                print(f"[Obfuscated] Skipping {pkg_name}")
                continue
            if 'play.google.com' not in market.lower():
                continue
            if not is_on_playstore(pkg_name):
                continue

            metadata = get_metadata(apikey, pkg_name, vercode)
            if not metadata:
                continue

            try:
                if isinstance(metadata, list) and len(metadata) > 0:
                    metadata = metadata[0]

                app_details = metadata.get('details', {}).get('appDetails', {})
                app_type = app_details.get('appType', '').lower()
                if app_type == "game":
                    continue

                numDownloadsText = app_details.get('numDownloads', '0')
                numDownloads = parse_download_count(numDownloadsText.split()[0])
                stratum = get_stratum(numDownloads)

                if not (stratum == '500-1k'):
                    print(stratum, "   - Skipping")
                    continue

                if not stratum:
                    continue

                out_path = f'{OUTPUT_DIR}/{stratum}/{pkg_name}_{vercode}.apk'

                if  os.path.exists(out_path):
                    skip_count += 1
                    print(f"[Skip {skip_count}] Already exists: {pkg_name}_{vercode}")
                    continue

            except Exception as e:
                print(f"[Parse Error] {pkg_name} - {e}")
                continue

            if strata_counts[stratum] >= SAMPLES_PER_STRATUM:
                continue

            if download_apk(apikey, sha256, out_path, pkg_name):
                strata_counts[stratum] += 1
                downloaded += 1
                print(f"[Downloaded {downloaded}] {pkg_name} - {numDownloadsText} [{stratum}]")
                log_rows.append({
                    'sha256': sha256,
                    'pkg_name': pkg_name,
                    'versioncode': vercode,
                    'market': market,
                    'numDownloads': numDownloadsText,
                    'apk_size': apk_size,
                    'strata': stratum
                })

            if downloaded >= MAX_DOWNLOADS:
                save_log(log_rows)
                print(f"[{datetime.now()}] Finished downloading {downloaded} APKs.")
                return

    save_log(log_rows)
    print(f"[{datetime.now()}] Finished downloading {downloaded} APKs.")

if __name__ == '__main__':
    main()
