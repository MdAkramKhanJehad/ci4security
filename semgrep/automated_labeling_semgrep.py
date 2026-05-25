#!/usr/bin/env python3
import json
import glob
import os


rule_id = "java.lang.security.audit.crypto.ssl.insecure-hostname-verifier.insecure-hostname-verifier"
msg_substr = "Insecure HostnameVerifier implementation detected. This"
matching_substr = ' public class C14188b implements HostnameVerifier {\n        @Override // javax.net.ssl.HostnameVerifier\n        public boolean verify(String str, SSLSession sSLSession) {\n            return true;\n        }'
validation_status = True
search_dir = "semgrep/preprocessed-output"


def check_snippet(alert, matching_substr):
    try:
        for location in alert.get("locations", []):
            snippet_text = ( location.get("physicalLocation", {}).get("region", {}).get("snippet", {}).get("text", ""))
            if matching_substr in snippet_text:
                return True
    except (KeyError, TypeError):
        pass
    return False

 
def process_json_file(file_path, rule_id, msg_substr, matching_substr, validation_status):
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    modified = False
    alerts_updated = 0

    if isinstance(data, list):
        for alert in data:
            if not isinstance(alert, dict):
                continue

            if alert.get("ruleId") != rule_id:
                continue
            if msg_substr not in alert.get("message", {}).get("text", ""):
                continue
            if not check_snippet(alert, matching_substr):
                continue
            if alert.get("validation_status") == "":
                alert["validation_status"] = validation_status
                modified = True
                alerts_updated += 1

    if modified:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    return modified, alerts_updated


def main():
    json_files = sorted(glob.glob(os.path.join(search_dir, "**/*.json"), recursive=True))

    total_files = len(json_files)
    modified_files = 0
    total_alerts_updated = 0

    print(f"Search Directory: {search_dir}")
    print(f"Rule ID: {rule_id}")
    print(f"Message Substring: {msg_substr}")
    print(f"Matching Substring: {matching_substr}")
    print(f"Validation Status Value: {validation_status}")
    print(f"Total JSON files: {total_files}\n")

    for file_path in json_files:
        was_modified, alerts_count = process_json_file(
            file_path, rule_id, msg_substr, matching_substr, validation_status
        )

        if was_modified:
            modified_files += 1
            total_alerts_updated += alerts_count
            rel_path = os.path.relpath(file_path, search_dir)
            print(f"{rel_path:<50} | Updated {alerts_count} alert(s)")

    print(f"{'='*70}")
    print(f"Total files processed : {total_files}")
    print(f"Files modified : {modified_files}")
    print(f"Total alerts updated  : {total_alerts_updated}")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    main()