import os
import json
import csv

def process_sarif_reports(root_directory, output_csv_file):

    header = [
        'alert_description',
        'verdict',
        'artifact_location',
        'app_package_name',
        'version_code', 
        'apk_category',
        'sast_tool_name'
    ]


    with open(output_csv_file, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)

        writer.writerow(header)
        print(f"Starting to process files in '{root_directory}'...")

        for dirpath, _, filenames in os.walk(root_directory):
            for filename in filenames:
                if filename.endswith('.json'):
                    
                    apk_category = os.path.basename(dirpath)
                    sast_tool_name = "CogniCrypt"
                    
                    base_name = filename[:-5]
                    
                    if '_' in base_name:
                        parts = base_name.rsplit('_', 1)
                        app_package_name = parts[0]
                        version_code = parts[1]
                    else:
                        app_package_name = base_name
                        version_code = 'N/A'

                    file_path = os.path.join(dirpath, filename)

                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        
                        runs = data.get('runs', [])
                        if not runs:
                            continue
                        
                        results = runs[0].get('results', [])
                        
                        for alert in results:
                            properties = alert.get('properties', {})
                            verdict = properties.get('verificationStatus')

                            if verdict not in [True, False]:
                                continue

                            message = alert.get('message', {})
                            alert_description = message.get('text', 'N/A')

                            locations = alert.get('locations', [])
                            artifact_location = 'N/A'
                            if locations:
                                artifact_location = locations[0].get('physicalLocation', {}).get('artifactLocation', {}).get('uri', 'N/A')

                            row = [
                                alert_description,
                                verdict,
                                artifact_location,
                                app_package_name,
                                version_code, 
                                apk_category,
                                sast_tool_name
                            ]
                            writer.writerow(row)

                    except json.JSONDecodeError:
                        print(f"Warning: Could not decode JSON from {file_path}")
                    except Exception as e:
                        print(f"An error occurred while processing {file_path}: {e}")

    print(f"\nProcessing complete!")
    print(f"CSV file '{output_csv_file}' has been generated successfully.")


if __name__ == "__main__":
    ROOT_FOLDER = '../cognicrypt-CryptoAnalysis/final_out_reports'
    OUTPUT_FILE = 'verified_cognicrypt_alerts.csv'

    process_sarif_reports(ROOT_FOLDER, OUTPUT_FILE)