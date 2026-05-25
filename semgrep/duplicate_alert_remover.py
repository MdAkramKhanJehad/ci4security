
import json
import sys
from pathlib import Path


TARGET = Path("semgrep/preprocessed-output")
DRY_RUN = True
RULE_ID_TO_REMOVE = "gitlab.find_sec_bugs.TDES_USAGE-1"

def make_key(alert: dict):

    try:
        loc     = alert["locations"][0]["physicalLocation"]
        uri     = loc["artifactLocation"]["uri"]
        line    = loc["region"]["startLine"]
        snippet = loc["region"].get("snippet", {}).get("text", "")
        rule_id = alert.get("ruleId", "")
        message = alert.get("message", {}).get("text", "")
        return (uri, line, snippet, rule_id, message)
    except (KeyError, IndexError, TypeError):
        return None


def dedup_alerts(alerts: list[dict]):

    seen   = set()
    result = []
    removed = 0

    for alert in alerts:
        key = make_key(alert)
        if key is None or key not in seen:

            result.append(alert)
            if key is not None:
                seen.add(key)
        else:
            removed += 1

    return result, removed


def remove_rule_alerts(alerts: list[dict], rule_id: str):

    if not rule_id:
        return alerts, 0

    kept = []
    removed = 0

    for alert in alerts:
        if isinstance(alert, dict) and alert.get("ruleId") == rule_id:
            removed += 1
            continue
        kept.append(alert)

    return kept, removed


def process_file(path: Path):
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"ERROR  reading {path}: {exc}")
        return 0, 0
 
    if not isinstance(data, list):
        print(f"SKIP   {path}: not a JSON list")
        return 0, 0
 
    before = len(data)
    filtered, removed_by_rule = remove_rule_alerts(data, RULE_ID_TO_REMOVE)
    cleaned, removed_duplicates = dedup_alerts(filtered)
    removed = removed_by_rule + removed_duplicates
 
    if removed == 0:
        if RULE_ID_TO_REMOVE:
            print(f"OK     {path.name} ({before} alerts, no matches for ruleId={RULE_ID_TO_REMOVE})")
        else:
            print(f"OK     {path.name} ({before} alerts, no duplicates)")
        return before, 0
 
    if not DRY_RUN:
        try:
            path.write_text(json.dumps(cleaned, indent=2, ensure_ascii=False),encoding="utf-8")
            if RULE_ID_TO_REMOVE:
                print(f"FIXED  {path.name} ({before} alerts -> {len(cleaned)}, removed {removed_by_rule} by ruleId, {removed_duplicates} duplicates)")
            else:
                print(f"FIXED  {path.name} ({before} alerts -> {len(cleaned)}, removed {removed})")
        except Exception as exc:
            print(f"ERROR  writing {path}: {exc}")
    else:
        if RULE_ID_TO_REMOVE:
            print(f"DRY    {path.name} ({before} alerts -> would remove {removed_by_rule} by ruleId, {removed_duplicates} duplicates)")
        else:
            print(f"DRY    {path.name} ({before} alerts -> would remove {removed})")
 
    return before, removed



def main():
    target = TARGET.resolve()
 
    if not target.exists():
        print(f"ERROR: path not found: {target}")
        sys.exit(1)
 
    files = [target] if target.is_file() else sorted(target.rglob("*.json"))
 
    if not files:
        print(f"No .json files found under {target}")
        sys.exit(0)
 
    total_alerts  = 0
    total_removed = 0
 
    for f in files:
        before, removed = process_file(f)
        total_alerts  += before
        total_removed += removed
 
    print()
    print(f"Files processed : {len(files)}")
    print(f"Alerts scanned  : {total_alerts}")
    print(f"Duplicates {'found  ' if DRY_RUN else 'removed'} : {total_removed}")
    if DRY_RUN:
        print("(dry-run — no files were modified)")
 
 
if __name__ == "__main__":
    main()
