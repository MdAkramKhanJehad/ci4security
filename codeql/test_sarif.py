import json
from pathlib import Path

def load_sarif(sarif_path):
    with open(sarif_path, "r") as f:
        return json.load(f)

if __name__ == "__main__":
    sarif_file = "output/1M-5M/com.angel.world.clock_14.sarif"
    sarif_object = load_sarif(sarif_file)

    output_file = Path("a.json")
    with open(output_file, "w") as f:
        json.dump(sarif_object, f, indent=2)

    print(f"Saved full SARIF object to {output_file}")