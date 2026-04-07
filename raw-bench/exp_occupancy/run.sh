#!/bin/bash

#!/bin/bash

# Accept 3 args, optionally 4th (PARALLEL_ZONES)
if [ "$#" -lt 3 ]; then
    echo "Usage: $0 <EXPERIMENT_NAME> <DEVICE_PATH> <REQUEST_SIZE> [PARALLEL_ZONES]"
    echo "Example: $0 ZN540 /dev/nvme0n1 4096 64"
    exit 1
fi

EXPERIMENT_NAME="$1"
DEVICE_PATH="$2"
REQUEST_SIZE="$3"
PARALLEL_ZONES="${4:-1}"   # default to 1 if not provided


RESULT_FILE="new_results/${EXPERIMENT_NAME}-time"
PERCENTAGES=(0.01 10 20 30 40 50 60 70 80 90 99.99)

# Reset all zones
echo "Resetting all zones on ${DEVICE_PATH}..."
sudo nvme zns reset-zone "$DEVICE_PATH" -a

# Build fill tool (uses libzbd and handles everything inside)
gcc -o fill fill.c -lzbd -O2 -Wall

# Run the fill experiment
./fill "$DEVICE_PATH" "$REQUEST_SIZE" "$RESULT_FILE" "${PERCENTAGES[@]}"

echo "🎉 All experiments completed. Results saved in ${RESULT_FILE}"
