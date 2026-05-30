#!/usr/bin/env python3
import json
import glob
import os
import re


rule_id = "java.lang.security.audit.crypto.unencrypted-socket.unencrypted-socket"
msg_substr = "Detected use of a Java "
matching_substr = 'new Socket'
uri_substr = ""
validation_status = False
dry_run = False
search_dir = "semgrep/preprocessed-output"


complex_match_flag = False
complex_pattern_substr = ".init(2"
complex_pattern_substr_2 = ""



METHOD_SIGNATURE_RE = re.compile(
    r"^\s*(?:(?:public|private|protected|static|final|native|synchronized|abstract|strictfp)\s+)*"
    r"[\w<>,\[\].?$\s]+?\s+([A-Za-z_][\w$]*)\s*\([^;]*\)"
    r"(?:\s+throws\s+[^\{]+)?\s*\{\s*$"
)


def get_primary_location(alert):
    for location in alert.get("locations", []):
        if not isinstance(location, dict):
            continue

        physical_location = location.get("physicalLocation", {})
        artifact_location = physical_location.get("artifactLocation", {})
        region = physical_location.get("region", {})

        return (
            artifact_location.get("uri", ""),
            region.get("startLine"),
        )

    return "", None


def resolve_source_path(json_file_path, uri):
    if not uri:
        return None

    candidates = []
    if os.path.isabs(uri):
        candidates.append(uri)

    candidates.append(os.path.abspath(os.path.join(os.getcwd(), uri)))
    candidates.append(os.path.abspath(os.path.join(os.path.dirname(json_file_path), uri)))

    repo_root = os.path.abspath(os.path.join(os.path.dirname(json_file_path), "..", "..", ".."))
    normalized_uri = re.sub(r"^(?:\.\./)+", "", uri)
    candidates.append(os.path.abspath(os.path.join(repo_root, normalized_uri)))

    for candidate in candidates:
        if os.path.exists(candidate):
            return candidate

    return candidates[0] if candidates else None


def get_method_ranges(source_lines):
    methods = []
    index = 0

    while index < len(source_lines):
        line = source_lines[index]
        match = METHOD_SIGNATURE_RE.match(line)
        if not match:
            index += 1
            continue

        start_index = index
        brace_depth = line.count("{") - line.count("}")
        end_index = index

        while brace_depth > 0 and end_index + 1 < len(source_lines):
            end_index += 1
            brace_depth += source_lines[end_index].count("{") - source_lines[end_index].count("}")

        methods.append(
            {
                "name": match.group(1),
                "start": start_index,
                "end": end_index,
            }
        )
        index = end_index + 1

    return methods


def method_has_all_substrings(method_lines, substrings):
    for substring in substrings:
        if not substring:
            continue

        if not any(substring in line for line in method_lines):
            return False

    return True


def find_method_containing_line(methods, line_index):
    for method in methods:
        if method["start"] <= line_index <= method["end"]:
            return method

    return None


def find_parent_method_with_patterns(source_lines, callee_name, required_substrings):
    call_pattern = re.compile(rf"\b{re.escape(callee_name)}\s*\(")
    methods = get_method_ranges(source_lines)

    for method in methods:
        if method["name"] == callee_name:
            continue

        method_lines = source_lines[method["start"] : method["end"] + 1]
        if call_pattern.search("\n".join(method_lines)) and method_has_all_substrings(method_lines, required_substrings):
            return True

    return False


def check_complex_pattern(alert, json_file_path, matching_substr, complex_pattern_substr, complex_pattern_substr_2):
    # Require the original snippet match before looking at callers in source
    if not check_snippet(alert, matching_substr):
        return False

    uri_text, start_line = get_primary_location(alert)
    if not uri_text or start_line is None:
        return False

    source_path = resolve_source_path(json_file_path, uri_text)
    if not source_path or not os.path.exists(source_path):
        return False

    with open(source_path, "r", encoding="utf-8") as source_file:
        source_lines = source_file.readlines()

    if start_line < 1 or start_line > len(source_lines):
        return False

    methods = get_method_ranges(source_lines)
    callee_method = find_method_containing_line(methods, start_line - 1)
    if not callee_method:
        return False

    required_substrings = [complex_pattern_substr]
    if complex_pattern_substr_2:
        required_substrings.append(complex_pattern_substr_2)

    callee_lines = source_lines[callee_method["start"] : callee_method["end"] + 1]
    if method_has_all_substrings(callee_lines, required_substrings):
        return True

    return find_parent_method_with_patterns(source_lines, callee_method["name"], required_substrings)


def check_snippet(alert, matching_substr):
    try:
        for location in alert.get("locations", []):
            snippet_text = ( location.get("physicalLocation", {}).get("region", {}).get("snippet", {}).get("text", ""))
            if matching_substr in snippet_text:
                return True
    except (KeyError, TypeError):
        pass
    return False


def check_uri(alert, uri_substr):
    if uri_substr == "":
        return True

    try:
        for location in alert.get("locations", []):
            uri_text = location.get("physicalLocation", {}).get("artifactLocation", {}).get("uri", "")
            if uri_substr in uri_text:
                return True
    except (KeyError, TypeError):
        pass
    return False


def load_json_file(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            f.seek(0)
            return json.load(f, strict=False)

 
def process_json_file(
    file_path,
    rule_id,
    msg_substr,
    matching_substr,
    complex_match_flag,
    complex_pattern_substr,
    complex_pattern_substr_2,
    validation_status,
    dry_run,
):
    try:
        data = load_json_file(file_path)
    except json.JSONDecodeError as exc:
        print(f"Skipping invalid JSON: {os.path.relpath(file_path, search_dir)} | {exc}")
        return False, 0

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
            if not check_uri(alert, uri_substr):
                continue
            if complex_match_flag:
                if not check_complex_pattern(
                    alert,
                    file_path,
                    matching_substr,
                    complex_pattern_substr,
                    complex_pattern_substr_2,
                ):
                    continue
            elif not check_snippet(alert, matching_substr):
                continue
            if alert.get("validation_status") == "":
                alert["validation_status"] = validation_status
                modified = True
                alerts_updated += 1

    if modified and not dry_run:
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
    print(f"URI Substring: {uri_substr}")
    print(f"Matching Substring: {matching_substr}")
    print(f"Complex Match Flag: {complex_match_flag}")
    print(f"Complex Pattern Substring: {complex_pattern_substr}")
    print(f"Complex Pattern Substring 2: {complex_pattern_substr_2}")
    print(f"Validation Status Value: {validation_status}")
    print(f"Dry Run: {dry_run}")
    print(f"Total JSON files: {total_files}\n")

    for file_path in json_files:
        was_modified, alerts_count = process_json_file(
            file_path,
            rule_id,
            msg_substr,
            matching_substr,
            complex_match_flag,
            complex_pattern_substr,
            complex_pattern_substr_2,
            validation_status,
            dry_run,
        )

        if was_modified:
            modified_files += 1
            total_alerts_updated += alerts_count
            rel_path = os.path.relpath(file_path, search_dir)
            if dry_run:
                print(f"{rel_path:<50} | Would update {alerts_count} alert(s)")
            else:
                print(f"{rel_path:<50} | Updated {alerts_count} alert(s)")

    print(f"{'='*70}")
    print(f"Total files processed : {total_files}")
    print(f"Files modified : {modified_files}")
    print(f"Total alerts updated  : {total_alerts_updated}")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    main()