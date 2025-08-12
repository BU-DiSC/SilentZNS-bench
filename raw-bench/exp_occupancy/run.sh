#!/bin/bash

# Check arguments
if [ "$#" -ne 3 ]; then
    echo "Usage: $0 <EXPERIMENT_NAME> <DEVICE_PATH>"
    echo "Example: $0 ZN540 /dev/nvme0n1"
    exit 1
fi

EXPERIMENT_NAME="$1"
DEVICE_PATH="$2"
REQUEST_SIZE="$3"

RESULT_FILE="results/${EXPERIMENT_NAME}-time"
PERCENTAGES=(10 25 50 75 95)

# Reset all zones
echo "Resetting all zones on ${DEVICE_PATH}..."
sudo nvme zns reset-zone "$DEVICE_PATH" -a

# Build fill tool (uses libzbd and handles everything inside)
gcc -o fill fill.c -lzbd -O2 -Wall

# Run the fill experiment
./fill "$DEVICE_PATH" "$REQUEST_SIZE" "$RESULT_FILE" "${PERCENTAGES[@]}"

echo "🎉 All experiments completed. Results saved in ${RESULT_FILE}"
