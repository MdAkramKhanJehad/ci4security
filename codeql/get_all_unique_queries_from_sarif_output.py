import json
import os
from pathlib import Path

def get_all_unique_queries_from_sarif():

    output_dir = Path("output/1M-5M")
    unique_queries = {}
    sarif_count = 0
    
    if not output_dir.exists():
        print(f"Directory {output_dir} does not exist")
        return json.dumps({})
    
    for sarif_file in output_dir.glob("*.sarif"):
        try:
            with open(sarif_file, 'r') as f:
                sarif_data = json.load(f)
            
            if "runs" in sarif_data:
                for run in sarif_data["runs"]:
                    if "tool" in run and "driver" in run["tool"]:
                        driver = run["tool"]["driver"]
                        if "rules" in driver:
                            for rule in driver["rules"]:
                                rule_id = rule.get("id", "unknown")
                                # Create a unique query object
                                query_obj = {
                                    "name": rule.get("shortDescription", {}).get("text", rule_id),
                                    "details": rule.get("fullDescription", {}).get("text", "")
                                }
                                unique_queries[rule_id] = query_obj
            
            sarif_count += 1
            print(f"Processed {sarif_file.name} (Total unique queries so far: {len(unique_queries)})")
        
        except json.JSONDecodeError as e:
            print(f"Error parsing {sarif_file}: {e}")
        except Exception as e:
            print(f"Error processing {sarif_file}: {e}")
    
    numbered_queries = []
    for idx, (rule_id, query_obj) in enumerate(unique_queries.items(), start=1):
        query_obj["number"] = idx
        query_obj["rule_id"] = rule_id
        numbered_queries.append(query_obj)
    
    print(f"\n[Summary] Processed {sarif_count} SARIF files. Found {len(numbered_queries)} unique queries.")
    
    result = {"total_queries": len(numbered_queries), "queries": numbered_queries}
    return json.dumps(result, indent=2)

if __name__ == "__main__":
    output = get_all_unique_queries_from_sarif()
    print(output)
    
    with open("unique_queries.json", "w") as f:
        f.write(output)
    print("Queries saved to unique_queries.json")