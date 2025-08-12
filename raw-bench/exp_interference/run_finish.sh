#!/bin/bash

# Check argument count
if [ "$#" -ne 4 ]; then
    echo "Usage: $0 <EXPERIMENT_NAME> <DEVICE_PATH>"
    echo "Example: $0 ZN540 /dev/nvme0n1"
    exit 1
fi

# Command-line arguments
EXPERIMENT_NAME="$1"
DEVICE_PATH="$2"
# Configuration
REQUEST_SIZE="$3"
ZONE_INCREMENT="$4"


RESULT_DIR="results"
PERCENTAGE=40

# Starting zone LBAs
FILL_ZONE_START=0
FINISH_ZONE_START=0
FIO_ZONE_START=30

# Prepare environment
mkdir -p "$RESULT_DIR"
gcc -o fill fill.c -lzbd -Wall

JOBS=(1 2 3 4 5 6 7)

for JOB in "${JOBS[@]}"; do

    # Fill the first JOB zones with $PERCENTAGE%
    for ((zone=0; zone<JOB; zone++)); do
        echo "Filling zone $FILL_ZONE_START to ${PERCENTAGE}%"
        ./fill "$DEVICE_PATH" "$REQUEST_SIZE" "$FILL_ZONE_START" "${RESULT_DIR}/${EXPERIMENT_NAME}_fill.txt" "$PERCENTAGE"
        FILL_ZONE_START=$((FILL_ZONE_START + 1))
    done

    for ((i=0; i<JOB; i++)); do
        echo "Running finish at LBA offset 0x$(printf '%X' "$FINISH_ZONE_START")..."
        sudo nvme zns finish-zone "$DEVICE_PATH" --start-lba="$FINISH_ZONE_START" &
        FINISH_ZONE_START=$((FINISH_ZONE_START + ZONE_INCREMENT))
    done

    JSON_OUTPUT="${RESULT_DIR}/${EXPERIMENT_NAME}_finish_${JOB}jobs.json"

    echo "Running fio with ${JOB} jobs starting at zone ${FIO_ZONE_START}..."
    sudo fio --name=write \
        --filename="$DEVICE_PATH" \
        --rw=write \
        --direct=1 \
        --ioengine=sync \
        --bs=16K \
        --size=1z \
        --offset="${FIO_ZONE_START}z" \
        --offset_increment=1z \
        --numjobs="$JOB" \
        --zonemode=zbd \
        --group_reporting \
        --output-format=json \
        --output="$JSON_OUTPUT"

    wait  # Wait for background 'finish' commands to complete
done

echo "All experiments completed. Fio results saved in ${RESULT_DIR}/"


