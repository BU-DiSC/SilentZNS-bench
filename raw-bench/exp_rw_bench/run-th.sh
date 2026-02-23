#!/bin/bash

# Check arguments
if [ "$#" -ne 3 ]; then
    echo "Usage: $0 <EXPERIMENT_NAME> <DEVICE_PATH>"
    echo "Example: $0 ZN540 /dev/nvme0n1"
    exit 1
fi

# Input arguments
EXPERIMENT_NAME="$1"
DEVICE_PATH="$2"
REQUEST_SIZE="$3"

# Configuration
FIO_ZONE_START=0
RESULT_DIR="new_results"

# Create result directory if not present
mkdir -p "$RESULT_DIR"

# Reset the device
echo "Resetting all zones on $DEVICE_PATH..."
sudo nvme zns reset-zone "$DEVICE_PATH" -a

# Run experiment from 1 to 14 threads (jobs)
for JOB in 1, 2, 4, 8, 16, 32; do
    JSON_OUTPUT="${RESULT_DIR}/${EXPERIMENT_NAME}_threads_${JOB}.json"
    echo "Running fio with ${JOB} jobs (starting at zone ${FIO_ZONE_START})..."

    sudo fio --name=write \
        --filename="$DEVICE_PATH" \
        --rw=write \
        --direct=1 \
        --ioengine=sync \
        --bs=4K \
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

echo "All experiments completed. Results saved in '${RESULT_DIR}/'"
