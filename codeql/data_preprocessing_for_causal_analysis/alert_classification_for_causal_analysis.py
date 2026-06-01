#!/usr/bin/env python3

import csv
import json
import re
from functools import lru_cache
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_INPUT_CSV = SCRIPT_DIR / "alerts_with_apk_size_codeql.csv"
DEFAULT_OUTPUT_CSV = SCRIPT_DIR / "alerts_with_lib_category_and_apk_size_codeql.csv"
LIBSCOUT_JSON_DIR = REPO_ROOT / "library_classification" / "library_detection"
LIBSCOUT_PROFILES_DIR = REPO_ROOT / "library_classification" / "LibScout-Profiles" / "profiles"

CODE_LOCATION_COLUMN = "code_location"
LIBRARY_NAME_COLUMN = "3rd_party_library_name"

GENERIC_PACKAGE_PREFIXES = {"com", "org", "net", "io", "android", "androidx"}

PACKAGE_PREFIX_FALLBACKS = [
    ("com.facebook.applinks", "Facebook-App-Links"),
    ("com.facebook", "Facebook-Core"),
    ("com.google.android.gms.internal.ads", "com.google.android.gms::play-services-ads-base"),
    ("com.google.android.gms.ads", "com.google.android.gms::play-services-ads-base"),
    ("com.google.android.gms.location", "com.google.android.gms::play-services-location"),
    ("com.google.android.gms.maps", "com.google.android.gms::play-services-maps"),
    ("com.google.android.gms.tasks", "com.google.android.gms::play-services-tasks"),
    ("com.google.firebase.auth", "com.google.firebase::firebase-auth"),
    ("com.google.firebase.database", "com.google.firebase::firebase-database"),
    ("com.google.firebase.firestore", "com.google.firebase::firebase-firestore"),
    ("com.google.firebase.functions", "com.google.firebase::firebase-functions"),
    ("com.google.firebase.iid", "com.google.firebase::firebase-iid"),
    ("com.google.firebase.messaging", "com.google.firebase::firebase-messaging"),
    ("com.google.firebase.storage", "com.google.firebase::firebase-storage"),
    ("com.google.gson", "Gson"),
    ("com.squareup.okhttp", "OkHttp"),
    ("okhttp3", "OkHttp"),
    ("okhttp", "OkHttp"),
    ("okio", "okio"),
    ("org.apache.http", "apache-httpclient-android"),
    ("org.jsoup", "jsoup"),
]


def normalize_pkg(value):
    if value is None:
        return ""

    value = str(value).strip().lower()
    value = value.replace("\\", "/").replace("/", ".")
    value = re.sub(r"\s+", "", value)
    value = re.sub(r"\.+", ".", value)
    return value.strip(".")


def normalize_artifact_path(artifact_location):
    artifact = "" if artifact_location is None else str(artifact_location).strip()
    artifact = artifact.replace("\\", "/").strip("/")

    for prefix in ("sources/", "source/", "src/main/java/", "java/"):
        if artifact.startswith(prefix):
            artifact = artifact[len(prefix):]
            break

    return artifact


def artifact_to_package_dir(artifact_location):
    artifact = normalize_artifact_path(artifact_location)

    if "/" in artifact:
        artifact = artifact.rsplit("/", 1)[0]
    else:
        artifact = re.sub(r"\.(java|kt|class)$", "", artifact, flags=re.IGNORECASE)
        if "." in artifact:
            artifact = artifact.rsplit(".", 1)[0]

    return normalize_pkg(artifact)


def remove_trailing_number(value):
    return re.sub(r"\d+$", "", value)


def profile_key(value):
    value = "" if value is None else str(value).strip().lower()
    return re.sub(r"[.\-_:]", "", value)


def lib_name_parts(lib_name):
    lib_name = "" if lib_name is None else str(lib_name).strip()
    parts = [lib_name]

    if "::" in lib_name:
        left, right = lib_name.split("::", 1)
        parts.extend([left, right])

    if ":" in lib_name:
        parts.extend(lib_name.split(":"))

    return [part.strip() for part in parts if part and part.strip()]


def package_candidates(package_name):
    package_name = normalize_pkg(package_name)
    candidates = []
    seen = set()
    current = package_name

    while current:
        tokens = current.split(".")

        if (
            len(current) >= 3
            and current not in GENERIC_PACKAGE_PREFIXES
            and all(len(token) >= 2 for token in tokens)
            and current not in seen
        ):
            candidates.append(current)
            seen.add(current)

        last_token = tokens[-1]
        stripped_last = remove_trailing_number(last_token)
        if stripped_last != last_token:
            stripped = ".".join(tokens[:-1] + [stripped_last])
            stripped_tokens = stripped.split(".")

            if (
                len(stripped) >= 3
                and stripped not in GENERIC_PACKAGE_PREFIXES
                and all(len(token) >= 2 for token in stripped_tokens)
                and stripped not in seen
            ):
                candidates.append(stripped)
                seen.add(stripped)

        if "." not in current:
            break

        current = ".".join(tokens[:-1])

    return candidates


def packages_match(artifact_pkg, lib_root_pkg):
    artifact_pkg = normalize_pkg(artifact_pkg)
    lib_root_pkg = normalize_pkg(lib_root_pkg)

    if not artifact_pkg or not lib_root_pkg:
        return False

    return artifact_pkg == lib_root_pkg or artifact_pkg.startswith(lib_root_pkg + ".")


def is_developer_written(artifact_pkg, app_package_name):
    artifact_pkg = normalize_pkg(artifact_pkg)
    app_package_name = normalize_pkg(app_package_name)

    if not artifact_pkg or not app_package_name:
        return False

    return artifact_pkg == app_package_name or artifact_pkg.startswith(app_package_name + ".")


def build_lib_category_map(profiles_dir):
    category_by_key = {}

    for category_dir in profiles_dir.iterdir():
        if not category_dir.is_dir():
            continue

        category = category_dir.name
        for profile_file in category_dir.glob("*.libv"):
            lib_base_name = profile_file.stem.split("_", 1)[0]

            for part in lib_name_parts(lib_base_name):
                key = profile_key(part)
                if not key:
                    continue

                category_by_key.setdefault(key, (category, lib_base_name))
                stripped_key = remove_trailing_number(key)
                if stripped_key:
                    category_by_key.setdefault(stripped_key, (category, lib_base_name))

    return category_by_key


def find_profile_for_lib(lib_name, lib_category_map):
    for part in lib_name_parts(lib_name):
        key = profile_key(part)
        stripped_key = remove_trailing_number(key)

        if key in lib_category_map:
            return lib_category_map[key]

        if stripped_key in lib_category_map:
            return lib_category_map[stripped_key]

    return None


def build_lib_entries(libscout_data, lib_category_map):
    entries = []

    package_only_matches = libscout_data.get("lib_packageOnlyMatches") or {}
    if isinstance(package_only_matches, dict):
        package_only_iter = package_only_matches.items()
    elif isinstance(package_only_matches, list):
        package_only_iter = []
        for entry in package_only_matches:
            if isinstance(entry, dict):
                package_only_iter.append((entry.get("libName", ""), entry.get("libRootPackage", "")))
            else:
                package_only_iter.append((str(entry), str(entry)))
    else:
        package_only_iter = []

    for lib_name, root_package in package_only_iter:
        root_package = normalize_pkg(root_package)
        if not root_package:
            continue

        profile = find_profile_for_lib(lib_name, lib_category_map)
        if profile:
            category, canonical_lib_name = profile
            entries.append((root_package, category, canonical_lib_name))
        else:
            entries.append((root_package, "others", "unknown"))

    for lib_match in libscout_data.get("lib_matches") or []:
        if not isinstance(lib_match, dict):
            continue

        root_package = normalize_pkg(lib_match.get("libRootPackage", ""))
        lib_name = str(lib_match.get("libName", "")).strip()

        if not root_package or not lib_name:
            continue

        profile = find_profile_for_lib(lib_name, lib_category_map)
        if profile:
            category, canonical_lib_name = profile
            entries.append((root_package, category, canonical_lib_name))
        else:
            entries.append((root_package, "others", "unknown"))

    entries.sort(key=lambda item: (item[0].count("."), len(item[0])), reverse=True)
    return entries


def find_libscout_json(app_package_name, version_code):
    app_package_name = str(app_package_name).strip()
    version_code = str(version_code).strip()

    app_dir = LIBSCOUT_JSON_DIR / app_package_name.replace(".", "/")
    exact_path = app_dir / f"{app_package_name}_{version_code}_{version_code}.json"
    if exact_path.exists():
        return exact_path

    if app_dir.exists():
        matches = sorted(app_dir.glob(f"{app_package_name}_{version_code}_*.json"))
        if matches:
            return matches[0]

    return None


@lru_cache(maxsize=None)
def load_libscout_entries(app_package_name, version_code, lib_category_map_items):
    lib_category_map = dict(lib_category_map_items)
    json_path = find_libscout_json(app_package_name, version_code)
    if not json_path:
        return tuple()

    try:
        with json_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return tuple()

    return tuple(build_lib_entries(data, lib_category_map))


def classify_with_libscout(artifact_pkg, app_package_name, version_code, lib_category_map):
    lib_category_map_items = tuple(sorted(lib_category_map.items()))
    entries = load_libscout_entries(app_package_name, version_code, lib_category_map_items)

    for root_package, category, lib_name in entries:
        if packages_match(artifact_pkg, root_package):
            return category, lib_name

    return None, None


def classify_with_profiles(artifact_pkg, lib_category_map):
    for candidate in package_candidates(artifact_pkg):
        candidate_key = profile_key(candidate)
        stripped_candidate_key = remove_trailing_number(candidate_key)

        for lib_key, (category, lib_name) in lib_category_map.items():
            if (
                candidate_key == lib_key
                or stripped_candidate_key == lib_key
                or candidate_key.startswith(lib_key)
                or stripped_candidate_key.startswith(lib_key)
                or lib_key.startswith(candidate_key)
                or lib_key.startswith(stripped_candidate_key)
            ):
                return category, lib_name

    return None, None


def classify_with_package_prefixes(artifact_pkg, lib_category_map):
    for root_package, lib_name in PACKAGE_PREFIX_FALLBACKS:
        if not packages_match(artifact_pkg, root_package):
            continue

        profile = find_profile_for_lib(lib_name, lib_category_map)
        if profile:
            return profile

    return None, None


def classify_alert(row, lib_category_map):
    artifact_location = row.get("artifact_location", "")
    artifact_pkg = artifact_to_package_dir(artifact_location)
    app_package_name = row.get("app_package_name", "")
    version_code = row.get("version_code", "")

    code_location, lib_name = classify_with_libscout(
        artifact_pkg,
        app_package_name,
        version_code,
        lib_category_map,
    )
    if code_location and code_location != "others":
        return code_location, lib_name

    if is_developer_written(artifact_pkg, app_package_name):
        return "developer_written", "not_applicable"

    code_location, lib_name = classify_with_package_prefixes(artifact_pkg, lib_category_map)
    if code_location:
        return code_location, lib_name

    code_location, lib_name = classify_with_profiles(artifact_pkg, lib_category_map)
    if code_location:
        return code_location, lib_name

    return "others", "unknown"


def mark_fully_unmatched_apps_as_obfuscated(rows):
    rows_by_app = {}
    matched_count_by_app = {}

    for index, row in enumerate(rows):
        app_package_name = row.get("app_package_name", "")
        rows_by_app.setdefault(app_package_name, []).append(index)

        if row.get(CODE_LOCATION_COLUMN) != "others":
            matched_count_by_app[app_package_name] = matched_count_by_app.get(app_package_name, 0) + 1

    for app_package_name, row_indexes in rows_by_app.items():
        if matched_count_by_app.get(app_package_name, 0) != 0:
            continue

        for row_index in row_indexes:
            rows[row_index][CODE_LOCATION_COLUMN] = "obfuscated"
            rows[row_index][LIBRARY_NAME_COLUMN] = "obfuscated"


def remove_obfuscated_rows(rows):
    return [
        row
        for row in rows
        if not (
            row.get(CODE_LOCATION_COLUMN) == "obfuscated"
            and row.get(LIBRARY_NAME_COLUMN) == "obfuscated"
        )
    ]


def classify_alerts(input_csv, output_csv):
    input_csv = Path(input_csv)
    output_csv = Path(output_csv)

    lib_category_map = build_lib_category_map(LIBSCOUT_PROFILES_DIR)

    with input_csv.open("r", newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)

    for required_column in ("artifact_location", "app_package_name", "version_code"):
        if required_column not in fieldnames:
            raise ValueError(f"Missing required column in {input_csv}: {required_column}")

    counter = 0
    for row in rows:
        code_location, lib_name = classify_alert(row, lib_category_map)
        row[CODE_LOCATION_COLUMN] = code_location
        row[LIBRARY_NAME_COLUMN] = lib_name
        print(f"Classified alert {counter + 1}/{len(rows)}: {row.get('app_package_name', '')} - {code_location} - {lib_name}")
        counter += 1

    mark_fully_unmatched_apps_as_obfuscated(rows)
    rows = remove_obfuscated_rows(rows)

    for new_column in (CODE_LOCATION_COLUMN, LIBRARY_NAME_COLUMN):
        if new_column not in fieldnames:
            fieldnames.append(new_column)

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open("w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Classified {len(rows)} alerts.")
    print(f"Saved output CSV to: {output_csv}")


if __name__ == "__main__":
    classify_alerts(DEFAULT_INPUT_CSV, DEFAULT_OUTPUT_CSV)
