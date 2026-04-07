#!/bin/bash
set -e

# Check arguments
if [ "$#" -ne 3 ]; then
    echo "Usage: $0 <EXPERIMENT_NAME> <DEVICE_PATH> <REQUEST_SIZE>"
    echo "Example: $0 ZN540 /dev/nvme0n1 4096"
    echo "Note: REQUEST_SIZE parameter is ignored - all block sizes will be tested"
    exit 1
fi

# Input arguments
EXPERIMENT_NAME="$1"
DEVICE_PATH="$2"

# Configuration
FIO_ZONE_START=0
RESULT_DIR="new_results"

# Thread counts to test
THREAD_COUNTS=(1 2 4 8 16 32)

# Block sizes to test: 4K -> 512K, doubling each time
BLOCK_SIZES=("4K" "8K" "16K" "32K" "64K" "128K")

# Create result directory if not present
mkdir -p "$RESULT_DIR"

# Run experiment for each thread count and block size combination
for JOB in "${THREAD_COUNTS[@]}"; do
    for BS in "${BLOCK_SIZES[@]}"; do
        JSON_OUTPUT="${RESULT_DIR}/${EXPERIMENT_NAME}_threads_${JOB}_bs_${BS}.json"
        
        echo "Resetting all zones on $DEVICE_PATH..."
        sudo nvme zns reset-zone "$DEVICE_PATH" -a

        echo "Running fio with ${JOB} jobs and block size ${BS}..."

        sudo fio --name=write \
            --filename="$DEVICE_PATH" \
            --rw=write \
            --direct=1 \
            --ioengine=sync \
            --bs="$BS" \
            --size=1z \
            --offset="${FIO_ZONE_START}z" \
            --offset_increment=1z \
            --numjobs="$JOB" \
            --zonemode=zbd \
            --group_reporting \
            --output-format=json \
            --output="$JSON_OUTPUT"
        wait
    done
done

echo "All experiments completed. Results saved in '${RESULT_DIR}/'"
echo "Total experiments run: $((${#THREAD_COUNTS[@]} * ${#BLOCK_SIZES[@]}))"

