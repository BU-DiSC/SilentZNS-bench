#!/bin/bash

# Check argument count
if [ "$#" -ne 3 ]; then
    echo "Usage: $0 <EXPERIMENT_NAME> <DEVICE_PATH> <REQUEST_SIZE>"
    echo "Example: $0 ZN540 /dev/nvme0n1 4096"
    exit 1
fi

# Inputs
EXPERIMENT_NAME="$1"
DEVICE_PATH="$2"
REQUEST_SIZE="$3"

# Fill percentages to test
PERCENTAGES=(99)

# Output directory and log file
RESULT_DIR="results"
RESULT_FILE="${RESULT_DIR}/${EXPERIMENT_NAME}_fill.txt"

# Build
mkdir -p "$RESULT_DIR"
gcc -o fill fill.c -lzbd -lm -Wall
if [ $? -ne 0 ]; then
    echo "Compilation failed. Aborting."
    exit 1
fi

# Run fill for each percentage
for PCT in "${PERCENTAGES[@]}"; do
    echo "▶️  Running fill for ${PCT}%"
    ./fill "$DEVICE_PATH" "$REQUEST_SIZE" "$RESULT_FILE" "$PCT"
    if [ $? -ne 0 ]; then
        echo "Fill failed at ${PCT}%"
    fi
done

echo "✅ All fill runs complete. Results saved in $RESULT_FILE"
