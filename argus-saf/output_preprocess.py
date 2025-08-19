import json


input_file = "/home/akram/android/akram/ci4sec/argus-saf/argus_results.json"
output_file = "output.json"

with open(input_file, "r", encoding="utf-8") as f:
    data = json.load(f)

for item in data:
    result_value = item.get("result")

    if isinstance(result_value, str) and result_value.strip() != "No misuse.":
        results_list = [r.strip() for r in result_value.split("\n") if r.strip()]
        item["result"] = [{"result": r, "status": ""} for r in results_list]

with open(output_file, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print(f"Processed JSON saved to {output_file}")
