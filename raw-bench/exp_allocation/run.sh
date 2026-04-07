#!/bin/bash
set -e

# Check arguments
if [ "$#" -ne 4 ]; then
    echo "Usage: $0 <EXPERIMENT_NAME> <DEVICE_PATH> <REQUEST_SIZE> <PARALLEL_ZONES>"
    echo "Example: $0 ZN540 /dev/nvme0n1 4096 8"
    exit 1
fi

# Input arguments
EXPERIMENT_NAME="$1"
DEVICE_PATH="$2"
REQUEST_SIZE="$3"
PARALLEL_ZONES="$4"

# Configuration
FIO_ZONE_START=0
RESULT_DIR="new_results"

# Create result directory if not present
mkdir -p "$RESULT_DIR"

# Reset the device
echo "Resetting all zones on $DEVICE_PATH..."
sudo nvme zns reset-zone "$DEVICE_PATH" -a

# Run fio with PARALLEL_ZONES jobs
JOB="$PARALLEL_ZONES"
echo "Running fio with ${JOB} jobs (starting at zone ${FIO_ZONE_START})..."

sudo fio --name=write \
    --filename="$DEVICE_PATH" \
    --rw=write \
    --direct=1 \
    --ioengine=sync \
    --bs="${REQUEST_SIZE}" \
    --size=1z \
    --offset="${FIO_ZONE_START}z" \
    --offset_increment=1z \
    --numjobs="$JOB" \
    --zonemode=zbd

echo "✅ fio run complete."
echo "Results (fio stdout) printed above. (No JSON output configured in this script.)"
