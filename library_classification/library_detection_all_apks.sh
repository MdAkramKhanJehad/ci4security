#!/bin/bash

LIBSCOUT_JAR="LibScout-2.3.2/build/libs/LibScout-2.3.2.jar"
ANDROID_JAR="../../android_cmd_tools/platforms/android-33/android.jar"
CONFIG_FILE="LibScout-2.3.2/config/LibScout.toml"
PROFILES_DIR="LibScout-Profiles/profiles"
APK_SOURCE_DIR="../downloaded_apks"
OUTPUT_DIR="library_detection"

echo "Creating output directory at: $OUTPUT_DIR"
mkdir -p "$OUTPUT_DIR"

total_apks=$(find "$APK_SOURCE_DIR" -type f -name "*.apk" | wc -l)
count=1
echo "Starting LibScout analysis on all APKs in '$APK_SOURCE_DIR'..."

find "$APK_SOURCE_DIR" -type f -name "*.apk" | while read apk_file; do
    if [ -f "$apk_file" ]; then
        apk_basename=$(basename "$apk_file")
        echo "Processing APK $count of $total_apks: $apk_basename"        
        count=$((count + 1))
        
        java -jar "$LIBSCOUT_JAR" \
            -o match \
            -a "$ANDROID_JAR" \
            -c "$CONFIG_FILE" \
            -p "$PROFILES_DIR" \
            -j "$OUTPUT_DIR" \
            "$apk_file"
    fi
    
done

echo "---------------------------------------------"
echo "Analysis complete."
