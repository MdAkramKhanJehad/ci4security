import os
import json
import requests
import time


def get_api_key():
    with open("../api_key.txt") as f:
        return f.read().strip()


def save_results_to_json(data, output_file):
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
        print(f"\nProcessing complete!")
    except Exception as e:
        print(f"\nCould not write results to file '{output_file}': {e}")



def fetch_all_metadata(root_directory, output_file):
   
    api_key = get_api_key()
    if not api_key:
        print("api key not available")
        return

    all_apk_metadata = {}
    processed_apks = set()    
    base_api_url = "https://androzoo.uni.lu/api/get_gp_metadata"
    counter = 1

    for dirpath, _, filenames in os.walk(root_directory):
        for filename in filenames:
            if not filename.endswith('.apk'):
                continue

            base_name = filename[:-4]
            
            if '_' in base_name:
                parts = base_name.rsplit('_', 1)
                package_name = parts[0]
                version_code = parts[1]
            else:
                print(f"Skipping malformed {filename}")
                continue
            
            apk_identifier = base_name
            if apk_identifier in processed_apks:
                continue
            
            print(f"Processing: {apk_identifier}")
            
            request_url = f"{base_api_url}/{package_name}/{version_code}"
            params = {'apikey': api_key}

            try:
                response = requests.get(request_url, params=params, timeout=20)
                
                if response.status_code == 200 and 'application/json' in response.headers.get('Content-Type', ''):
                    metadata = response.json()
                    all_apk_metadata[apk_identifier] = metadata
                    print(f"Fetched metadata for {apk_identifier}")
                else:
                    print(f"Metadata Fetch Failed for {apk_identifier}")
                    all_apk_metadata[apk_identifier] = {
                        "error": "Fetch Failed",
                        "status_code": response.status_code,
                        "reason": response.reason,
                        "content_type": response.headers.get('Content-Type', 'N/A')
                    }

            except requests.exceptions.RequestException as err:
                print(f"Request Error for {apk_identifier}: {err}")
                all_apk_metadata[apk_identifier] = {"error": "Request Failed", "details": str(err)}
            
            processed_apks.add(apk_identifier)
            time.sleep(0.5) 
            print("Running: ", counter)
            counter += 1

    save_results_to_json(all_apk_metadata, output_file)


if __name__ == "__main__":
    root_folder = '../downloaded_apks'
    output_json_file = 'dataset_apk_metadata.json'

    fetch_all_metadata(root_folder, output_json_file)
