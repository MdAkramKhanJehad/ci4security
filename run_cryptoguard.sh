#!/bin/bash

APK_ROOT="downloaded_apks"
OUTPUT_ROOT="cryptoguard_output"
FAILED_CSV="cryptoguard_failed.csv"
IN_PROGRESS="cryptoguard_in_progress.csv"


if [ ! -f "$FAILED_CSV" ]; then
    echo "apk_path" > "$FAILED_CSV"
fi

if [ ! -f "$IN_PROGRESS" ]; then
    echo "apk_path" > "$IN_PROGRESS"
fi

total=0
success=0
failed=0

while IFS= read -r apk; do
    rel_path="${apk#$APK_ROOT/}"
    apk_name=$(basename "$apk" .apk)
    subfolder=$(dirname "$rel_path")
    out_dir="$OUTPUT_ROOT/$subfolder"
    out_json="$out_dir/$apk_name.json"

    if [ -f "$out_json" ] || grep -Fxq "$apk" "$FAILED_CSV" || grep -Fxq "$apk" "$IN_PROGRESS"; then
        echo "Skipping: already processed/in-progress: $apk"
        continue
    fi

    echo "$apk" >> "$IN_PROGRESS"

    total=$((total+1))
    mkdir -p "$out_dir"
    echo "$total: Scanning: $apk"

    output=$(java -jar ../../tools/cryptoguard/cryptoguard.jar \
        -in apk -s "$apk" -m D -o "$out_json" 2>&1)

    if [ $? -ne 0 ] || echo "$output" | grep -qi "Exception" || echo "$output" | grep -qi "Error"; then
        echo "    -> FAILED"
        echo "---- OUTPUT BEGIN ----"
        echo "$output"
        echo "---- OUTPUT END ----"

        echo "$apk" >> "$FAILED_CSV"
        [ -f "$out_json" ] && rm "$out_json"
        failed=$((failed+1))
    else
        echo "    -> SUCCESS"
        echo "$output"
        success=$((success+1))
    fi

    tmp_file=$(mktemp)
    grep -Fxv "$apk" "$IN_PROGRESS" > "$tmp_file" && mv "$tmp_file" "$IN_PROGRESS"

done < <(find "$APK_ROOT" -type f -name "*.apk")

echo
echo "===== SUMMARY ====="
echo "Total analyzed : $total"
echo "Success        : $success"
echo "Failed         : $failed"
echo "Failed list saved in $FAILED_CSV"

