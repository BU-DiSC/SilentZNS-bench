#!/bin/bash
set -e  # Exit on any error

if [ "$#" -lt 3 ]; then
    echo "Usage: $0 <EXPERIMENT_NAME> <DEVICE_PATH> <REQUEST_SIZE> [EXPERIMENT_ID] [ZONE_INCREMENT] [PARALLEL_ZONES]"
    echo "Example: $0 ZN540 /dev/nvme1n2 4096 1 0x80000 8"
    echo
    echo "Experiment ID (optional):"
    echo "  0 = all"
    echo "  1 = interference only"
    echo "  2 = occupancy only"
    echo "  3 = write-threads only"
    echo "  4 = read-threads only"
    echo "  5 = queue-depth only"
    echo "  6 = allocation only"
    echo
    echo "ZONE_INCREMENT (optional): only used for interference experiment (default 0x80000)"
    echo "PARALLEL_ZONES (optional): used by occupancy/fill tools that open zones in parallel (default 1)"
    exit 1
fi

EXPERIMENT_NAME="$1"
DEVICE_PATH="$2"
REQUEST_SIZE="$3"
EXPERIMENT_ID="${4:-0}"              # Default to 0 (all)
ZONE_INCREMENT="${5:-0x80000}"       # Only used for interference experiment
PARALLEL_ZONES="${6:-1}"             # Used by occupancy/fill scripts (default 1)

echo "Starting selected experiments for ${EXPERIMENT_NAME} on ${DEVICE_PATH}..."
echo "  REQUEST_SIZE=${REQUEST_SIZE}"
echo "  EXPERIMENT_ID=${EXPERIMENT_ID}"
echo "  ZONE_INCREMENT=${ZONE_INCREMENT}"
echo "  PARALLEL_ZONES=${PARALLEL_ZONES}"

run_in_dir () {
  local dir="$1"; shift
  echo "▶️  (cd ${dir}) $*"
  (cd "${dir}" && bash "$@")
}

case "$EXPERIMENT_ID" in
  0)
    echo "Running all experiments"

    echo "interference"
    run_in_dir "exp_interference" "run_finish.sh" \
      "$EXPERIMENT_NAME" "$DEVICE_PATH" "$REQUEST_SIZE" "$ZONE_INCREMENT"

    echo "occupancy"
    run_in_dir "exp_occupancy" "run.sh" \
      "$EXPERIMENT_NAME" "$DEVICE_PATH" "$REQUEST_SIZE" "$PARALLEL_ZONES"

    echo "thread-scaling"
    run_in_dir "exp_rw_bench" "run-th.sh" \
      "$EXPERIMENT_NAME" "$DEVICE_PATH" "$REQUEST_SIZE"

    echo "queue-depth"
    run_in_dir "exp_rw_bench" "run-qd.sh" \
      "$EXPERIMENT_NAME" "$DEVICE_PATH"

    echo "allocation"

    run_in_dir "exp_allocation" "run.sh" \
      "$EXPERIMENT_NAME" "$DEVICE_PATH" "$REQUEST_SIZE" "$PARALLEL_ZONES"
    ;;
  1)
    echo "Running interference experiment only"
    run_in_dir "exp_interference" "run_finish.sh" \
      "$EXPERIMENT_NAME" "$DEVICE_PATH" "$REQUEST_SIZE" "$ZONE_INCREMENT"
    ;;
  2)
    echo "Running occupancy experiment only"
    run_in_dir "exp_occupancy" "run.sh" \
      "$EXPERIMENT_NAME" "$DEVICE_PATH" "$REQUEST_SIZE" "$PARALLEL_ZONES"
    ;;
  3)
    echo "Running write-scaling experiment only"
    run_in_dir "exp_rw_bench" "run-th.sh" \
      "$EXPERIMENT_NAME" "$DEVICE_PATH" "$REQUEST_SIZE"
    ;;
  4)
    echo "Running read-scaling experiment only"
    run_in_dir "exp_rw_bench" "run-th-read.sh" \
      "$EXPERIMENT_NAME" "$DEVICE_PATH" "$REQUEST_SIZE"
    ;;
  5)
    echo "Running queue-depth experiment only"
    run_in_dir "exp_rw_bench" "run-qd.sh" \
      "$EXPERIMENT_NAME" "$DEVICE_PATH" "$REQUEST_SIZE"
    ;;
  6)
    echo "Running allocation experiment only"
    run_in_dir "exp_allocation" "run.sh" \
      "$EXPERIMENT_NAME" "$DEVICE_PATH" "$REQUEST_SIZE" "$PARALLEL_ZONES"
    ;;
  *)
    echo "Invalid experiment ID: $EXPERIMENT_ID"
    exit 1
    ;;
esac

echo "All selected experiments completed."
