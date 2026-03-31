import json
from pathlib import Path

CRYPTO_KEYWORDS = [
    "crypto", "crypt", "cipher", "encryption", "decryption",
    "hash", "md5", "sha1", "sha256", "rsa", "aes", "des",
    "ssl", "tls", "keystore", "secure random", "prng"
]

def is_crypto_related(text):
    if not text:
        return False
    text = text.lower()
    return any(keyword in text for keyword in CRYPTO_KEYWORDS)

def extract_crypto_alerts_full(sarif_path):
    with open(sarif_path, "r") as f:
        sarif = json.load(f)

    crypto_results = []

    for run in sarif.get("runs", []):
        rules_map = {}
        rules = run.get("tool", {}).get("driver", {}).get("rules", [])
        for r in rules:
            rules_map[r.get("id")] = {
                "name": r.get("name"),
                "description": r.get("fullDescription", {}).get("text"),
                "tags": r.get("properties", {}).get("tags", [])
            }

        for result in run.get("results", []):
            rule_id = result.get("ruleId")
            message = result.get("message", {}).get("text", "")

            rule_info = rules_map.get(rule_id, {})

            combined_text = " ".join([
                rule_id or "",
                message or "",
                rule_info.get("name") or "",
                rule_info.get("description") or "",
                " ".join(rule_info.get("tags", []))
            ])

            if not is_crypto_related(combined_text):
                continue

            full_alert = {
                "result": result,
                "rule_metadata": rule_info
            }

            crypto_results.append(full_alert)

    return crypto_results

if __name__ == "__main__":
    sarif_file = "output/1M-5M/com.angel.world.clock_14.sarif"
    crypto_alerts = extract_crypto_alerts_full(sarif_file)


    print(json.dumps(crypto_alerts, indent=2))