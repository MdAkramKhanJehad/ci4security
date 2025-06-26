import asyncio
import aiohttp
import aiofiles
import csv
import os
import datetime
import random
from collections import defaultdict
from pathlib import Path
from itertools import islice


INPUT_FILE = 'input_file/shuffled_filtered_unique_latest_with-added-date.csv'
API_KEY_FILE = 'api_key.txt'
OUTPUT_DIR = 'downloaded_apk'
LOG_FILE = 'download_log.csv'

SAMPLES_PER_STRATUM = 64  
MAX_DOWNLOADS = SAMPLES_PER_STRATUM * 11 
CONCURRENT_LIMIT = 5 


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


def parse_download_count(text):
    if '+' in text:
        text = text.replace('+', '').strip()
    if 'M' in text:
        return int(float(text.replace('M', '').strip()) * 1_000_000)
    if 'k' in text:
        return int(float(text.replace('k', '').strip()) * 1000)
    return int(text.replace(',', '').strip())


def get_stratum(download_count):
    for label, (low, high) in STRATA.items():
        if low <= download_count < high:
            return label
    return None


def read_api_key():
    with open(API_KEY_FILE) as f:
        return f.read().strip()


def ensure_dirs():
    Path(OUTPUT_DIR).mkdir(exist_ok=True)
    for label in STRATA:
        Path(f'{OUTPUT_DIR}/{label}').mkdir(parents=True, exist_ok=True)


async def app_exists_on_playstore(session, pkg_name):
    url = f'https://play.google.com/store/apps/details?id={pkg_name}'
    headers = {
        'User-Agent': 'Mozilla/5.0'  
    }
    try:
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                html = await response.text()
                return "Google Play" in html
            elif response.status == 404:
                # print(f"App not found on Play Store: {pkg_name}")
                return False
            else:
                print(f"{response.status} for {pkg_name}")
                return False
                
    except Exception as e:
        print(f"[Play Store Request Error] {pkg_name}: {e}")
        return False


async def get_metadata(session, apikey, pkg_name, vercode):
    url = f'https://androzoo.uni.lu/api/get_gp_metadata/{pkg_name}/{vercode}'
    params = {'apikey': apikey}

    async with session.get(url, params=params) as response:
        if response.status == 200:
            content_type = response.headers.get('Content-Type', '')
            if 'application/json' in content_type:
                return await response.json()
            else:
                text = await response.text()
                print(f"[Unexpected Content Type] {pkg_name} (vercode: {vercode})")
                print(f"Response content: {text[:200]}...")
                return None
        else:
            print(f"Metadata Fetch Failed: {pkg_name} (vercode: {vercode}) - Status: {response.status}")
            return None


async def download_apk(session, apikey, sha256, path, pkg_name):
    url = 'https://androzoo.uni.lu/api/download'
    params = {'apikey': apikey, 'sha256': sha256}
    try:
        async with session.get(url, params=params) as r:
            if r.status == 200:
                async with aiofiles.open(path, 'wb') as f:
                    await f.write(await r.read())
                return True
            else:
                print(f'[Download Failed] {pkg_name} ({sha256}) - Status: {r.status}')
                return False
    except Exception as e:
        print(f'Download Error: {pkg_name} ({sha256}) - {e}')
        return False



def save_log(rows):
    keys = ['sha256', 'pkg_name', 'versioncode', 'market', 'apk_size', 'numDownloads', 'strata']
    file_exists = os.path.exists(LOG_FILE)
    with open(LOG_FILE, 'a', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        if not file_exists:
            writer.writeheader()
        for row in rows:
            writer.writerow(row)


async def process_apks(apk_list, apikey):
    downloaded = 0
    strata_counts = defaultdict(int)
    log_rows = []

    semaphore = asyncio.Semaphore(CONCURRENT_LIMIT)
    async with aiohttp.ClientSession() as session:
        async def worker(apk):
            nonlocal downloaded
            async with semaphore:
                sha256, apk_size, pkg_name, vercode, market = apk
                if 'play.google.com' not in market.lower():
                    return

                exists = await app_exists_on_playstore(session, pkg_name)
                if not exists:
                    return

                metadata = await get_metadata(session, apikey, pkg_name, vercode)
                if not metadata:
                    return

                try:
                    if isinstance(metadata, list) and metadata:
                        metadata = metadata[0]

                    numDownloadsText = metadata['details']['appDetails']['numDownloads']
                    numDownloads = parse_download_count(numDownloadsText.split()[0])
                    stratum = get_stratum(numDownloads)
                except Exception as e:
                    print(f'Parse Error: {pkg_name} (vercode: {vercode}) - {e}')
                    return

                if strata_counts[stratum] >= SAMPLES_PER_STRATUM:
                    return

                out_path = f'{OUTPUT_DIR}/{stratum}/{pkg_name}_{vercode}.apk'
                if strata_counts[stratum] >= SAMPLES_PER_STRATUM:
                    return

                if await download_apk(session, apikey, sha256, out_path, pkg_name):
                    strata_counts[stratum] += 1
                    downloaded += 1
                    print(f'[Downloaded {downloaded}] {pkg_name} - {numDownloadsText} [{stratum}]')
                    log_rows.append({
                        'sha256': sha256,
                        'pkg_name': pkg_name,
                        'versioncode': vercode,
                        'market': market,
                        'apk_size': apk_size,
                        'numDownloads': numDownloadsText,
                        'strata': stratum
                    })


                if all(v >= SAMPLES_PER_STRATUM for v in strata_counts.values()):
                    raise asyncio.CancelledError  

        tasks = []
        for apk in apk_list:
            tasks.append(asyncio.create_task(worker(apk)))

        try:
            await asyncio.gather(*tasks)
        except asyncio.CancelledError:
            print("All strata filled. Cancelled remaining tasks.")

    return log_rows


def load_csv_in_chunks(file_path, chunk_size=100000):
    with open(file_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        while True:
            chunk = list(islice(reader, chunk_size))
            print(len(chunk))
            if not chunk:
                break
            yield chunk


def main():
    ensure_dirs()
    apikey = read_api_key()
    strata_counts = defaultdict(int)
    total_log_rows = []

    # print(" Before for loop")
    for chunk in load_csv_in_chunks(INPUT_FILE):
        print(f"\nProcessing next chunk at {datetime.datetime.now()}...")
        apk_batch = []
        for row in chunk:
            if not row['vercode'].isdigit():
                continue
            apk_batch.append((row['sha256'], row['apk_size'], row['pkg_name'], row['vercode'], row['markets']))
        
        log_rows = asyncio.run(process_apks(apk_batch, apikey))
        save_log(log_rows)
        total_log_rows.extend(log_rows)

        strata_done = defaultdict(int)
        for r in total_log_rows:
            strata_done[r['strata']] += 1
        if all(strata_done[stratum] >= SAMPLES_PER_STRATUM for stratum in STRATA):
            print("All strata filled. Exiting early.")
            break

    print(f"\nFinished downloading {len(total_log_rows)} APKs.\n")


if __name__ == '__main__':
    main()
