# import json
# from pathlib import Path


# CODEQL_ROOT = Path("codeql/preprocessed-output")
# SEMGREP_ROOT = Path("semgrep/preprocessed-output")


# def load_json(json_path):
#     with open(json_path, "r", encoding="utf-8") as f:
#         return json.load(f)


# def save_json(json_path, data):
#     with open(json_path, "w", encoding="utf-8") as f:
#         json.dump(data, f, indent=2, ensure_ascii=False)


# def get_codeql_fields(alert):
#     try:
#         location = alert["locations"][0]["physicalLocation"]
#         uri = location["artifactLocation"]["uri"]
#         line = location["region"]["startLine"]

#         snippet = (
#             location
#             .get("contextRegion", {})
#             .get("snippet", {})
#             .get("text", "")
#         )

#         return uri, line, snippet

#     except (KeyError, IndexError, TypeError):
#         return None, None, None


# def get_semgrep_fields(alert):
#     """
#     Extract required fields from a Semgrep alert.
#     """
#     try:
#         location = alert["locations"][0]["physicalLocation"]

#         uri = location["artifactLocation"]["uri"]

#         line = location["region"]["startLine"]

#         snippet = (
#             location
#             .get("region", {})
#             .get("snippet", {})
#             .get("text", "")
#         )

#         return uri, line, snippet

#     except (KeyError, IndexError, TypeError):
#         return None, None, None


# def normalize_uri(uri):
#     if not uri:
#         return ""

#     uri = uri.replace("\\", "/")

#     if "sources/" in uri:
#         uri = uri[uri.index("sources/"):]

#     return uri



# def process_file_pair(codeql_file, semgrep_file):

#     codeql_alerts = load_json(codeql_file)
#     semgrep_alerts = load_json(semgrep_file)

#     updated_count = 0

#     for cq_alert in codeql_alerts:

#         validation_status = cq_alert.get("validation_status", "")

#         if validation_status == "":
#             continue

#         cq_uri, cq_line, cq_snippet = get_codeql_fields(cq_alert)

#         if not all([cq_uri, cq_line is not None]):
#             continue

#         cq_uri = normalize_uri(cq_uri)

#         for sg_alert in semgrep_alerts:

#             sg_uri, sg_line, sg_snippet = get_semgrep_fields(sg_alert)
#             if not all([sg_uri, sg_line is not None]):
#                 continue

#             sg_uri = normalize_uri(sg_uri)

#             uri_match = (cq_uri == sg_uri)
#             line_match = (cq_line == sg_line)

#             snippet_match = False

#             if sg_snippet and cq_snippet:
#                 snippet_match = sg_snippet in cq_snippet

#             if uri_match and line_match and snippet_match:
#             # if uri_match and line_match:

#                 sg_alert["validation_status"] = validation_status
#                 updated_count += 1

#                 # Stop after first match
#                 break

#     save_json(semgrep_file, semgrep_alerts)

#     return updated_count


# def main():
#     total_updated = 0
#     processed_files = 0

#     for codeql_file in CODEQL_ROOT.rglob("*.json"):

#         relative_path = codeql_file.relative_to(CODEQL_ROOT)
#         semgrep_file = SEMGREP_ROOT / relative_path

#         if not semgrep_file.exists():
#             print(f"SKIP: Missing Semgrep file: {semgrep_file}")
#             continue

#         try:
#             updated = process_file_pair(codeql_file, semgrep_file)

#             processed_files += 1
#             total_updated += updated

#             print(
#                 f"OK: {relative_path} -> "
#                 f"{updated} alerts updated"
#             )

#         except Exception as e:
#             print(f"ERROR: {relative_path}: {e}")

#     print(f"Processed files : {processed_files}")
#     print(f"Updated alerts  : {total_updated}")


# if __name__ == "__main__":
#     main()




import json
from pathlib import Path


CODEQL_ROOT = Path("codeql/preprocessed-output")
SEMGREP_ROOT = Path("semgrep/preprocessed-output")


def load_json(json_path):
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(json_path, data):
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def get_codeql_fields(alert):
    try:
        location = alert["locations"][0]["physicalLocation"]
        uri = location["artifactLocation"]["uri"]
        line = location["region"]["startLine"]
        snippet = (
            location
            .get("contextRegion", {})
            .get("snippet", {})
            .get("text", "")
        )
        return uri, line, snippet
    except (KeyError, IndexError, TypeError):
        return None, None, None


def get_semgrep_fields(alert):
    try:
        location = alert["locations"][0]["physicalLocation"]
        uri = location["artifactLocation"]["uri"]
        line = location["region"]["startLine"]
        snippet = (
            location
            .get("region", {})
            .get("snippet", {})
            .get("text", "")
        )
        return uri, line, snippet
    except (KeyError, IndexError, TypeError):
        return None, None, None


def normalize_uri(uri):
    if not uri:
        return ""
    uri = uri.replace("\\", "/")
    if "sources/" in uri:
        uri = uri[uri.index("sources/"):]
    return uri


def build_semgrep_index(semgrep_alerts):
    """
    Index Semgrep alerts by normalised URI for fast lookup.
    Line number is excluded from the key because CodeQL and Semgrep
    report different line numbers for the same flagged expression.
    """
    index = {}
    for alert in semgrep_alerts:
        sg_uri, sg_line, sg_snippet = get_semgrep_fields(alert)
        if not sg_uri or not sg_snippet:
            continue
        norm = normalize_uri(sg_uri)
        index.setdefault(norm, []).append(alert)
    return index


def process_file_pair(codeql_file, semgrep_file):
    codeql_alerts = load_json(codeql_file)
    semgrep_alerts = load_json(semgrep_file)

    sg_index = build_semgrep_index(semgrep_alerts)

    updated_count = 0

    for cq_alert in codeql_alerts:
        validation_status = cq_alert.get("validation_status", "")
        if validation_status == "":
            continue

        cq_uri, cq_line, cq_snippet = get_codeql_fields(cq_alert)

        # Explicit None checks instead of all([...]) to avoid logic bug
        if cq_uri is None or cq_line is None or not cq_snippet:
            continue

        cq_uri_norm = normalize_uri(cq_uri)

        for sg_alert in sg_index.get(cq_uri_norm, []):
            _, _, sg_snippet = get_semgrep_fields(sg_alert)

            # Line number deliberately excluded — CodeQL and Semgrep number
            # lines differently for the same expression (observed: ±1-2 lines)
            if sg_snippet and sg_snippet in cq_snippet:
                sg_alert["validation_status"] = validation_status
                updated_count += 1
                break  # stop after first match per CodeQL alert

    # Only write back if something actually changed
    if updated_count > 0:
        save_json(semgrep_file, semgrep_alerts)

    return updated_count


def main():
    total_updated = 0
    processed_files = 0

    for codeql_file in CODEQL_ROOT.rglob("*.json"):
        relative_path = codeql_file.relative_to(CODEQL_ROOT)
        semgrep_file = SEMGREP_ROOT / relative_path

        if not semgrep_file.exists():
            print(f"SKIP: Missing Semgrep file: {semgrep_file}")
            continue

        try:
            updated = process_file_pair(codeql_file, semgrep_file)
            processed_files += 1
            total_updated += updated
            print(f"OK: {relative_path} -> {updated} alerts updated")
        except Exception as e:
            print(f"ERROR: {relative_path}: {e}")

    print(f"Processed files : {processed_files}")
    print(f"Updated alerts  : {total_updated}")


if __name__ == "__main__":
    main()