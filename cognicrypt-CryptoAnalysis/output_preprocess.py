import json

input_file = "input.json"
output_file = "output_with_status.json"

with open(input_file, "r", encoding="utf-8") as f:
    data = json.load(f)

for run in data.get("runs", []):
    if "results" in run:
        for result in run["results"]:
            result["status"] = ""  

with open(output_file, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print(f"Updated JSON saved to {output_file}")
