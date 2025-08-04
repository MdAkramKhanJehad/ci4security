#!/bin/bash

APK_ROOT="../downloaded_apks"
OUTPUT_ROOT="argus_output"
RESULT_JSON="argus_results.json"
ANALYZED_LIST="argus_analyzed.txt"


if [ ! -f "$RESULT_JSON" ]; then
    echo "[]" > "$RESULT_JSON"
fi

if [ ! -f "$ANALYZED_LIST" ]; then
    touch "$ANALYZED_LIST"
fi

total=0
skipped=0

while IFS= read -r apk; do
    rel_path="${apk#$APK_ROOT/}"
    apk_name=$(basename "$apk")
    subfolder=$(dirname "$rel_path")
    out_dir="$OUTPUT_ROOT/$subfolder/$apk_name"

    if grep -Fxq "$apk" "$ANALYZED_LIST"; then
        echo "[SKIP] Already analyzed: $apk"
        skipped=$((skipped+1))
        continue
    fi

    total=$((total+1))
    mkdir -p "$out_dir"
    echo "[$total] Scanning: $apk"

    output=$(java -jar ~/tools/argus-saf/argus-saf-3.2.1-SNAPSHOT-assembly.jar a -d "$apk" -o "$out_dir" 2>&1)

    findings=$(echo "$output" | awk '/CryptographicMisuse:/,/Debug info/' | sed '1d;$d')


    if [ -z "$findings" ] || echo "$findings" | grep -q "No misuse"; then
        result="No misuse."
    else
        result=$(echo "$findings")
    fi

    tmp_file=$(mktemp)
    jq --arg apk "$apk_name" --arg folder "$subfolder" --arg res "$result" \
       '. += [{"apk":$apk, "subfolder":$folder, "result":$res}]' \
       "$RESULT_JSON" > "$tmp_file" && mv "$tmp_file" "$RESULT_JSON"

    echo "$apk" >> "$ANALYZED_LIST"

done < <(find "$APK_ROOT" -type f -name "*.apk")

echo
echo "-------------------Done--------------------"
echo "Newly analyzed : $total"
echo "Skipped (already done): $skipped"
echo "Results saved in $RESULT_JSON"
