
#!/usr/bin/env python3

import json
import glob
import os


rule_id = "java/potentially-weak-cryptographic-algorithm"
msg_substr = "Cryptographic algorithm [CFB](1)"
matching_substr = 'CFB'
validation_status = False  
uri_substr = ""
search_dir = "codeql/preprocessed-output"


def check_in_context_regions(alert, matching_substr):
    if "locations" in alert:
        for location in alert["locations"]:
            if "physicalLocation" in location:
                phys_loc = location["physicalLocation"]
                if "contextRegion" in phys_loc:
                    context = phys_loc["contextRegion"]
                    if "snippet" in context and "text" in context["snippet"]:
                        if matching_substr in context["snippet"]["text"]:
                            # print("----- "*10, context["snippet"]["text"])
                            return True
    
    if "relatedLocations" in alert:
        for rel_loc in alert["relatedLocations"]:
            if "physicalLocation" in rel_loc:
                phys_loc = rel_loc["physicalLocation"]
                if "contextRegion" in phys_loc:
                    context = phys_loc["contextRegion"]
                    if "snippet" in context and "text" in context["snippet"]:
                        if matching_substr in context["snippet"]["text"]:
                            return True
    
    if "codeFlows" in alert:
        for code_flow in alert["codeFlows"]:
            if "threadFlows" in code_flow:
                for thread_flow in code_flow["threadFlows"]:
                    if "locations" in thread_flow:
                        for loc in thread_flow["locations"]:
                            if "location" in loc:
                                if "physicalLocation" in loc["location"]:
                                    phys_loc = loc["location"]["physicalLocation"]
                                    if "contextRegion" in phys_loc:
                                        context = phys_loc["contextRegion"]
                                        if "snippet" in context and "text" in context["snippet"]:
                                            if matching_substr in context["snippet"]["text"]:
                                                return True
    
    return False


def check_in_uris(alert, uri_substr):
    if not uri_substr:
        return True

    if isinstance(alert, dict):
        for key, value in alert.items():
            if key == "uri" and isinstance(value, str):
                if uri_substr in value:
                    return True
            elif isinstance(value, (dict, list)) and check_in_uris(value, uri_substr):
                return True
    elif isinstance(alert, list):
        for item in alert:
            if check_in_uris(item, uri_substr):
                return True

    return False


def process_json_file(file_path, rule_id, msg_substr, matching_substr, validation_status):
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError:
        print(f"Skipping invalid JSON: {os.path.relpath(file_path, search_dir)}")
        return False, 0
    
    modified = False
    alerts_updated = 0
    
    if isinstance(data, list):
        for alert in data:
            if isinstance(alert, dict):
                if alert.get("ruleId") == rule_id:
                    if "message" in alert and "text" in alert["message"]:
                        if msg_substr in alert["message"]["text"]:
                            if check_in_context_regions(alert, matching_substr):
                                if check_in_uris(alert, uri_substr):
                                    if alert["validation_status"] == "":
                                        alert["validation_status"] = validation_status
                                        modified = True
                                        alerts_updated += 1
    
    if modified:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
    
    return modified, alerts_updated


def main():
    json_files = glob.glob(os.path.join(search_dir, "**/*.json"), recursive=True)
    json_files = sorted(json_files)
    
    total_files = len(json_files)
    modified_files = 0
    total_alerts_updated = 0
    
 
    print(f"Search Directory: {search_dir}")
    print(f"Rule ID: {rule_id}")
    print(f"Message Substring: {msg_substr}")
    print(f"Matching Substring: {matching_substr}")
    print(f"Validation Status Value: {validation_status}")
    print(f"Total JSON files to process: {total_files}\n")
    
    for file_path in json_files:
        was_modified, alerts_count = process_json_file(file_path, rule_id, msg_substr, matching_substr, validation_status)
        
        if was_modified:
            modified_files += 1
            total_alerts_updated += alerts_count
            rel_path = os.path.relpath(file_path, search_dir)
            print(f"{rel_path:<50} | Updated {alerts_count} alert(s)")
    
    print(f"\n{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}")
    print(f"Total files processed:    {total_files}")
    print(f"Files modified:           {modified_files}")
    print(f"Total alerts updated:     {total_alerts_updated}")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    main()






# #!/usr/bin/env python3
# import json
# import glob
# import os

# # ─────────────────────────────────────────────────────────────────────────────
# # Configure here
# # ─────────────────────────────────────────────────────────────────────────────

# rule_id           = "java/weak-cryptographic-algorithm"
# msg_substr        = "Cryptographic algorithm [AES/ECB/NOPADDING](1) is insecure"
# matching_substr   = "AES/ECB/NOPADDING"
# validation_status = True
# search_dir        = "codeql/preprocessed-output"


# # ─────────────────────────────────────────────────────────────────────────────
# # Search helpers
# # ─────────────────────────────────────────────────────────────────────────────

# def check_in_context_regions(alert, matching_substr):
#     """
#     Search contextRegion.snippet.text in:
#       - locations[]
#       - relatedLocations[]
#       - codeFlows[].threadFlows[].locations[].location
#     """
#     if "locations" in alert:
#         for location in alert["locations"]:
#             if "physicalLocation" in location:
#                 phys_loc = location["physicalLocation"]
#                 if "contextRegion" in phys_loc:
#                     context = phys_loc["contextRegion"]
#                     if "snippet" in context and "text" in context["snippet"]:
#                         if matching_substr in context["snippet"]["text"]:
#                             return True

#     if "relatedLocations" in alert:
#         for rel_loc in alert["relatedLocations"]:
#             if "physicalLocation" in rel_loc:
#                 phys_loc = rel_loc["physicalLocation"]
#                 if "contextRegion" in phys_loc:
#                     context = phys_loc["contextRegion"]
#                     if "snippet" in context and "text" in context["snippet"]:
#                         if matching_substr in context["snippet"]["text"]:
#                             return True

#     if "codeFlows" in alert:
#         for code_flow in alert["codeFlows"]:
#             if "threadFlows" in code_flow:
#                 for thread_flow in code_flow["threadFlows"]:
#                     if "locations" in thread_flow:
#                         for loc in thread_flow["locations"]:
#                             if "location" in loc:
#                                 if "physicalLocation" in loc["location"]:
#                                     phys_loc = loc["location"]["physicalLocation"]
#                                     if "contextRegion" in phys_loc:
#                                         context = phys_loc["contextRegion"]
#                                         if "snippet" in context and "text" in context["snippet"]:
#                                             if matching_substr in context["snippet"]["text"]:
#                                                 return True

#     return False


# def check_in_related_messages(alert, matching_substr):
#     """
#     Search relatedLocations[].message.text — needed for rules like
#     java/weak-cryptographic-algorithm where the algorithm name (e.g.
#     'AES/ECB/NOPADDING') appears only in the related location message,
#     not in any contextRegion snippet.
#     """
#     for rel_loc in alert.get("relatedLocations", []):
#         msg_text = rel_loc.get("message", {}).get("text", "")
#         if matching_substr in msg_text:
#             return True
#     return False


# def matches_alert(alert, matching_substr):
#     """
#     Returns True if matching_substr is found in ANY of:
#       1. contextRegion snippets (locations, relatedLocations, codeFlows)
#       2. relatedLocations message text
#     """
#     return (
#         check_in_context_regions(alert, matching_substr)
#         or check_in_related_messages(alert, matching_substr)
#     )


# # ─────────────────────────────────────────────────────────────────────────────
# # File processor
# # ─────────────────────────────────────────────────────────────────────────────

# def process_json_file(file_path, rule_id, msg_substr, matching_substr, validation_status):
#     with open(file_path, "r", encoding="utf-8") as f:
#         data = json.load(f)

#     modified      = False
#     alerts_updated = 0

#     if isinstance(data, list):
#         for alert in data:
#             if not isinstance(alert, dict):
#                 continue
#             if alert.get("ruleId") != rule_id:
#                 continue
#             if msg_substr not in alert.get("message", {}).get("text", ""):
#                 continue
#             if not matches_alert(alert, matching_substr):
#                 continue
#             if alert.get("validation_status") == "":
#                 alert["validation_status"] = validation_status
#                 modified       = True
#                 alerts_updated += 1

#     if modified:
#         with open(file_path, "w", encoding="utf-8") as f:
#             json.dump(data, f, indent=2)

#     return modified, alerts_updated


# # ─────────────────────────────────────────────────────────────────────────────
# # Main
# # ─────────────────────────────────────────────────────────────────────────────

# def main():
#     json_files = sorted(glob.glob(os.path.join(search_dir, "**/*.json"), recursive=True))

#     total_files          = len(json_files)
#     modified_files       = 0
#     total_alerts_updated = 0

#     print(f"Search Directory:        {search_dir}")
#     print(f"Rule ID:                 {rule_id}")
#     print(f"Message Substring:       {msg_substr}")
#     print(f"Matching Substring:      {matching_substr}")
#     print(f"Validation Status Value: {validation_status}")
#     print(f"Total JSON files:        {total_files}\n")

#     for file_path in json_files:
#         was_modified, alerts_count = process_json_file(
#             file_path, rule_id, msg_substr, matching_substr, validation_status
#         )
#         if was_modified:
#             modified_files       += 1
#             total_alerts_updated += alerts_count
#             rel_path = os.path.relpath(file_path, search_dir)
#             print(f"{rel_path:<50} | Updated {alerts_count} alert(s)")

#     print(f"\n{'='*70}")
#     print("SUMMARY")
#     print(f"{'='*70}")
#     print(f"Total files processed : {total_files}")
#     print(f"Files modified        : {modified_files}")
#     print(f"Total alerts updated  : {total_alerts_updated}")
#     print(f"{'='*70}\n")


# if __name__ == "__main__":
#     main()

