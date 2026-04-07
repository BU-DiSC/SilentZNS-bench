#!/bin/bash

#!/bin/bash
set -e

# Check arguments
if [ "$#" -ne 3 ]; then
    echo "Usage: $0 <EXPERIMENT_NAME> <DEVICE_PATH> <REQUEST_SIZE>"
    echo "Example: $0 ZN540 /dev/nvme0n1 4096"
    exit 1
fi

# Input arguments
EXPERIMENT_NAME="$1"
DEVICE_PATH="$2"

# Configuration
FIO_ZONE_START=0
RESULT_DIR="new_results"

# Block sizes to test: 4K -> 512K, doubling each time
BLOCK_SIZES=("4K" "8K" "16K" "32K" "64K" "128K")

# Create result directory if not present
mkdir -p "$RESULT_DIR"

# Run experiment for each block size
for BS in "${BLOCK_SIZES[@]}"; do
    JSON_OUTPUT="${RESULT_DIR}/${EXPERIMENT_NAME}_bs_${BS}.json"

    echo "Resetting all zones on $DEVICE_PATH..."
    sudo nvme zns reset-zone "$DEVICE_PATH" -a

    echo "Running fio with block size ${BS} on 1 zone using 1 thread..."

    sudo fio --name=write \
        --filename="$DEVICE_PATH" \
        --rw=write \
        --numjobs=1 \
        --job_max_open_zones=1 \
        --direct=1 \
        --buffered=0 \
        --ioengine=sync \
        --bs="$BS" \
        --size=1z \
        --offset="${FIO_ZONE_START}z" \
        --zonemode=zbd \
        --group_reporting \
        --output-format=json \
        --output="$JSON_OUTPUT"

    wait
done

echo "All experiments completed. Results saved in '${RESULT_DIR}/'"