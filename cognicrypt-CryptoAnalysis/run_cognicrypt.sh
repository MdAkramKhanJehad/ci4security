#!/bin/bash

BASE_DIR=~/Desktop/ci4security
APK_ROOT="$BASE_DIR/downloaded_apks"
SCRIPT_DIR="$BASE_DIR/cognicrypt-CryptoAnalysis"
COGNICRYPT_JAR="/home/mkhan04/tools/cognicrypt/HeadlessAndroidScanner-5.0.1-SNAPSHOT-jar-with-dependencies.jar"
RULES_ZIP="/home/mkhan04/tools/cognicrypt/JavaCryptographicArchitecture.zip"
OUT_DIR="$SCRIPT_DIR/out_reports"
ANDROID_PLATFORMS="$ANDROID_SDK_HOME/platforms"

QUEUE_FILE="$SCRIPT_DIR/apk_queue.txt"
CURRENT_FILE="$SCRIPT_DIR/currently_analyzing.txt"
LOCK_FILE="$SCRIPT_DIR/lockfile.lock"
COUNTER=0

mkdir -p "$OUT_DIR"
touch "$CURRENT_FILE"

if [ ! -f "$QUEUE_FILE" ]; then
    find "$APK_ROOT" -type f -name "*.apk" | sort > "$QUEUE_FILE"
fi

while true; do
    {
        flock -x 200

        APK=$(head -n 1 "$QUEUE_FILE")
        if [ -z "$APK" ]; then
            echo "No more APKs to process. Exiting."
            exit 0
        fi

        REL_PATH="${APK#$APK_ROOT/}" 
        REPORT_DIR="$OUT_DIR/$(dirname "$REL_PATH")"
        REPORT_FILE="$REPORT_DIR/$(basename "$REL_PATH" .apk).json"

        if [ -f "$REPORT_FILE" ]; then
            tail -n +2 "$QUEUE_FILE" > "$QUEUE_FILE.tmp" && mv "$QUEUE_FILE.tmp" "$QUEUE_FILE"
            echo "Skipping (already analyzed): $APK"
            continue
        fi

        tail -n +2 "$QUEUE_FILE" > "$QUEUE_FILE.tmp" && mv "$QUEUE_FILE.tmp" "$QUEUE_FILE"
        echo "$APK" >> "$CURRENT_FILE"
        COUNTER=$((COUNTER + 1))

    } 200>"$LOCK_FILE"

#    REL_PATH="${APK#$APK_ROOT/}" 
#    REPORT_DIR="$OUT_DIR/$(dirname "$REL_PATH")"
    mkdir -p "$REPORT_DIR"
#    REPORT_FILE="$REPORT_DIR/$(basename "$REL_PATH" .apk).json"

    echo "$COUNTER: Analyzing: $APK"

    LOG_FILE=$(mktemp)
    TMP_REPORT_DIR=$(mktemp -d)

    timeout --foreground 5h java -Xms64g -Xmx256g -Xss16m -jar "$COGNICRYPT_JAR" \
        --rulesDir "$RULES_ZIP" \
        --apkFile "$APK" \
        --platformDirectory "$ANDROID_PLATFORMS" \
        --reportPath "$TMP_REPORT_DIR" \
        --reportFormat SARIF \
        --cg SPARK >"$LOG_FILE" 2>&1

    STATUS=$?

    if [ -f "$TMP_REPORT_DIR/CryptoAnalysis-Report.sarif.json" ]; then
        mv "$TMP_REPORT_DIR/CryptoAnalysis-Report.sarif.json" "$REPORT_FILE"
    fi
    rm -rf "$TMP_REPORT_DIR"

    {
        flock -x 200
        grep -Fxv "$APK" "$CURRENT_FILE" > "$CURRENT_FILE.tmp" && mv "$CURRENT_FILE.tmp" "$CURRENT_FILE"
    } 200>"$LOCK_FILE"

    if [ $STATUS -eq 0 ]; then
        echo "Success: $APK"
    else
        echo "Failed: $APK"
        echo "------------ Exception/Error Output ------------"
        cat "$LOG_FILE"
        echo "--------------------------------------------------"
    fi

    rm -f "$LOG_FILE"
done
