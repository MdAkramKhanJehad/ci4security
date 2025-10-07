import os
import json
import re
import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(BASE_DIR, "../extract_final_dataset_from_json/verified_cognicrypt_alerts.csv")
LIBSCOUT_JSON_DIR = os.path.join(BASE_DIR, "library_detection")
LIBSCOUT_PROFILES_DIR = os.path.join(BASE_DIR, "LibScout-Profiles/profiles")
OUTPUT_PATH = os.path.join(BASE_DIR, "alerts_with_category.csv")


def normalize_pkg(s: str) -> str:
    if not s:
        return ""
    s = s.strip().lower().replace("\\", "/").replace("/", ".")
    return re.sub(r"\s+", "", s)

def remove_last_token(s: str) -> str:
    parts = s.split(".")
    return ".".join(parts[:-1]) if len(parts) > 1 else s

def remove_trailing_number(s: str) -> str:
    return re.sub(r"\d+$", "", s)

def candidate_prefixes(dot_path: str):
    candidates, seen = [], set()
    cur = dot_path

    while cur and cur not in seen:
        tokens = cur.split(".")

        if (len(cur) >= 3 and cur not in seen and cur != "com" and all(len(tok) >= 2 for tok in tokens)):
            candidates.append(cur)
            seen.add(cur)

        last = tokens[-1]
        stripped = remove_trailing_number(last)
        if stripped != last:
            alt = ".".join(tokens[:-1] + [stripped])
            if (len(alt) >= 3 and alt not in seen and alt != "com" and all(len(tok) >= 2 for tok in alt.split(".")) ):
                candidates.append(alt)
                seen.add(alt)

        if "." not in cur:
            break
        cur = remove_last_token(cur)

    final_candidates = [
        c for c in candidates
        if len(c) >= 3 and c != "com" and all(len(tok) >= 2 for tok in c.split("."))
    ]

    return final_candidates


def find_json(app: str, version: str):
    folder = os.path.join(LIBSCOUT_JSON_DIR, app.replace(".", "/"))
    fname = f"{app}_{version}_{version}.json"
    fpath = os.path.join(folder, fname)
    return fpath if os.path.exists(fpath) else None


def build_lib_category_map():
    lib_map = {}
    for category in os.listdir(LIBSCOUT_PROFILES_DIR):
        cat_path = os.path.join(LIBSCOUT_PROFILES_DIR, category)
        if not os.path.isdir(cat_path):
            continue
        for f in os.listdir(cat_path):
            if not f.endswith(".libv"):
                continue
            base = f.split("_")[0].lower()
            key = re.sub(r"[.\-_:]", "", base)
            lib_map[key] = category
            lib_map.setdefault(remove_trailing_number(key), category)
    return lib_map


def find_category_for_lib(lib_name: str, lib_map: dict):
    if not lib_name:
        return None

    lib_name = lib_name.lower().strip()
    candidates = [lib_name]
    if "::" in lib_name:
        left, right = lib_name.split("::", 1)
        candidates.extend([left, right])
    if ":" in lib_name:
        candidates.extend(lib_name.split(":"))

    for c in candidates:
        norm = re.sub(r"[.\-_:]", "", c)
        norm_strip = remove_trailing_number(norm)
        if norm in lib_map:
            return lib_map[norm]
        if norm_strip in lib_map:
            return lib_map[norm_strip]
    return None


def match_against_libprofiles(candidates, lib_map):
    for c in candidates:
        c_norm = re.sub(r"[.\-_:]", "", c.lower())
        c_strip = remove_trailing_number(c_norm)
        for lib_name in lib_map.keys():
            if c_norm in lib_name or c_strip in lib_name or lib_name in c_norm:
                return lib_map[lib_name], lib_name
    return None, None


def match_in_pkgonly(artifact: str, pkg_only, lib_map: dict):
    if not pkg_only:
        return None, None

    cands = candidate_prefixes(artifact)
    items = []

    if isinstance(pkg_only, dict):
        items = pkg_only.items()
    elif isinstance(pkg_only, list):
        for entry in pkg_only:
            if isinstance(entry, dict):
                items.append((entry.get("libName", ""), entry.get("libRootPackage", "")))
            else:
                items.append((str(entry), str(entry)))

    for lib_name, root in items:
        root = normalize_pkg(root)
        if not root:
            continue
        for c in cands:
            if c in root or root in c:
                cat = find_category_for_lib(lib_name, lib_map)
                return (cat or "others"), lib_name
    return None, None


def match_in_libmatches(artifact: str, lib_matches, lib_map: dict):
    if not lib_matches:
        return None, None

    cands = candidate_prefixes(artifact)

    for lib in lib_matches:
        if not isinstance(lib, dict):
            continue

        root_raw = lib.get("libRootPackage", "")
        if not root_raw or not root_raw.strip():
            continue  

        root = normalize_pkg(root_raw)
        name = lib.get("libName", "")

        for c in cands:
            if c in root or root in c:
                cat = find_category_for_lib(name, lib_map)
                return (cat or "others"), name
    return None, None


def is_developer_written(artifact: str, app_pkg: str):
    artifact = normalize_pkg(artifact)
    app_pkg = normalize_pkg(app_pkg)
    parts = artifact.split(".")
    while len(parts) >= 2:
        cur = ".".join(parts)
        if app_pkg.startswith(cur) or cur in app_pkg:
            return True
        parts = parts[:-1]
    return False


def main():
    df = pd.read_csv(CSV_PATH)
    df = df.sort_values(by=["app_package_name"]).reset_index(drop=True)

    lib_map = build_lib_category_map()
    print(f"Loaded {len(lib_map)} libraries from LibScout profiles")

    code_locs, lib_names = [], []
    app_rows, app_matched = {}, {}

    for i, row in df.iterrows():
        app = str(row["app_package_name"]).strip()
        ver = str(row["version_code"]).strip()
        artifact = str(row["artifact_location"]).strip()

        artifact_dir = "/".join(artifact.replace("\\", "/").split("/")[:-1])
        artifact_dir = normalize_pkg(artifact_dir)

        code_location, lib_name = None, None
        json_path = find_json(app, ver)

        if json_path:
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                code_location, lib_name = match_in_pkgonly(
                    artifact_dir, data.get("lib_packageOnlyMatches"), lib_map
                )

                if not code_location:
                    code_location, lib_name = match_in_libmatches(
                        artifact_dir, data.get("lib_matches"), lib_map
                    )

            except Exception as e:
                print(f"Could not read JSON for {app}: {e}")

        if not code_location and is_developer_written(artifact_dir, app):
            code_location, lib_name = "developer_written", "not_applicable"

        if not code_location or code_location == "others":
            candidates = candidate_prefixes(artifact_dir)
            code_location, lib_name = match_against_libprofiles(candidates, lib_map)

        if not code_location:
            code_location, lib_name = "others", "unknown"

        code_locs.append(code_location)
        lib_names.append(lib_name)

        app_rows.setdefault(app, []).append(i)
        if code_location != "others":
            app_matched[app] = app_matched.get(app, 0) + 1

        if (i + 1) % 1000 == 0:
            print(f"Processed {i + 1} alerts...")

    for app, rows in app_rows.items():
        if app_matched.get(app, 0) == 0:
            for idx in rows:
                code_locs[idx] = "obfuscated"
                lib_names[idx] = "obfuscated"

    df["code_location"] = code_locs
    df["3rd_party_library_name"] = lib_names
    df.to_csv(OUTPUT_PATH, index=False)
    print(f"Classification complete! Saved to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
