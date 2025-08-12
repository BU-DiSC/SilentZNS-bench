#!/bin/bash

# Check argument count
if [ "$#" -ne 3 ]; then
    echo "Usage: $0 <EXPERIMENT_NAME> <DEVICE_PATH>"
    echo "Example: $0 ZN540 /dev/nvme0n1"
    exit 1
fi

# Command-line arguments
EXPERIMENT_NAME="$1"
DEVICE_PATH="$2"
REQUEST_SIZE="$3"

# Configuration
FIO_ZONE_START=0
RESULT_DIR="results"

# Prepare result directory
mkdir -p "$RESULT_DIR"

# Reset the device
echo "Resetting all zones on $DEVICE_PATH..."
sudo nvme zns reset-zone "$DEVICE_PATH" -a

# Run experiment for each queue depth
for QD in 2 4 8 16 32 64; do
    JSON_OUTPUT="${RESULT_DIR}/${EXPERIMENT_NAME}_qd_${QD}.json"
    echo "Running fio with qdepth=${QD} on 1 job (zone ${FIO_ZONE_START})..."

    fio --name=write \
        --filename="$DEVICE_PATH" \
        --rw=write \
        --direct=1 \
        --ioengine=libaio \
        --bs=16K \
        --size=1z \
        --offset="${FIO_ZONE_START}z" \
        --numjobs=1 \
        --iodepth="${QD}" \
        --zonemode=zbd \
        --group_reporting \
        --output-format=json \
        --output="$JSON_OUTPUT"

    wait
done

echo "All experiments completed. Results saved in '${RESULT_DIR}/'"
