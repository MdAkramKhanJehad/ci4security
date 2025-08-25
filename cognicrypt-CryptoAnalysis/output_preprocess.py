import json
import os

input_root = "/home/akram/android/akram/ci4sec/cognicrypt-CryptoAnalysis/out_reports"
output_root = "/home/akram/android/akram/ci4sec/cognicrypt-CryptoAnalysis/final_out_reports"

counter = 1

for root, dirs, files in os.walk(input_root):
    for file in files:
        if file.endswith(".json"):
            print("-*-"*15, f": {counter}")
            counter = counter + 1
            
            input_path = os.path.join(root, file)
            relative_path = os.path.relpath(input_path, input_root)
            output_path = os.path.join(output_root, relative_path)

            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            try:
                with open(input_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                for run in data.get("runs", []):
                    if "results" in run:
                        for result in run["results"]:
                            if "properties" not in result or not isinstance(result["properties"], dict):
                                result["properties"] = {}
                            if "verificationStatus" not in result["properties"]:
                                result["properties"]["verificationStatus"] = ""

                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)

                print(f"Processed: {input_path} → {output_path}")

            except Exception as e:
                print(f"Error processing {input_path}: {e}")

print("All JSON files processed")
