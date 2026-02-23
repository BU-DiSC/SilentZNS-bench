#!/bin/bash
set -e  # Exit on any error

EXP_ID=3 # 0: all, 1: interference, 2: occupancy, 3: write-scaling, 4: read-scaling, 5: queue depth, 6: allocation
SSD_ID=10 # 0: lazy (size = 128MB), 1: stripe (size = 128MB) 2: full (chunk = 1, size = 128MB), 3: vchunk (chunk = 2, size = 128MB), 4: vchunk (chunk = 8, size = 128MB),
# 5: lazy (size = 512MB), 6: stripe (size = 256MB) 7: full (chunk = 1, size = 256MB), 8: vchunk (chunk = 2, size = 256MB), 9: vchunk (chunk = 8, size = 256MB),


# ------- adjust this to run new experiments ------

# ==========================
# SSD Config Selector
# ==========================
set_ssd_config() {
  zns_channels_per_zone=8
  zns_ways_per_zone=1
  REQUEST_SIZE=4096

  zns_max_chunks_per_lun=1
  zns_min_luns=64
  zns_chunk_size=1

  case "$SSD_ID" in
    # ------------------------------------------------------------
    # 128 MiB zone configs (zsz=134217728, cap=134217728, inc=262144)
    # ------------------------------------------------------------
    0)
      # lazy, chunk=1
      zns_vtable_mode=1
      zns_zonesize=134217728
      zns_zonecap=134217728
      INCREMENT=262144
      ;;
    1)
      # stripe
      zns_vtable_mode=4
      zns_zonesize=134217728
      zns_zonecap=134217728
      INCREMENT=262144
      ;;
    2)
      # full, chunk=1
      zns_vtable_mode=2
      zns_chunk_size=1
      zns_zonesize=134217728
      zns_zonecap=134217728
      INCREMENT=262144
      ;;
    3)
      # flexible (your "5") with chunk=2, min_luns=128
      zns_vtable_mode=5
      zns_chunk_size=2
      zns_min_luns=128
      zns_zonesize=134217728
      zns_zonecap=134217728
      INCREMENT=262144
      ;;
    4)
      # flexible (your "5") with chunk=8, min_luns=32
      zns_vtable_mode=5
      zns_chunk_size=8
      zns_min_luns=32
      zns_zonesize=134217728
      zns_zonecap=134217728
      INCREMENT=262144
      ;;

    # ------------------------------------------------------------
    # 256 MiB zone configs (zsz=268435456, cap=268435456, inc=524288)
    # Same “shapes” as above, but larger zones
    # ------------------------------------------------------------
    5)
      # lazy, chunk=1
      zns_vtable_mode=1
      zns_zonesize=536870912
      zns_zonecap=536870912
      INCREMENT=1048576
      ;;
    6)
      # stripe
      zns_vtable_mode=4
      zns_zonesize=268435456
      zns_zonecap=268435456
      INCREMENT=524288
      ;;
    7)
      # full, chunk=1
      zns_vtable_mode=2
      zns_chunk_size=1
      zns_zonesize=268435456
      zns_zonecap=268435456
      INCREMENT=524288
      ;;
    8)
      # flexible with chunk=2, min_luns=128
      zns_vtable_mode=5
      zns_chunk_size=2
      zns_min_luns=128
      zns_zonesize=268435456
      zns_zonecap=268435456
      INCREMENT=524288
      ;;
    9)
      # flexible with chunk=8, min_luns=32
      zns_vtable_mode=5
      zns_chunk_size=8
      zns_min_luns=32
      zns_zonesize=268435456
      zns_zonecap=268435456
      INCREMENT=524288
      ;;

    # ------------------------------------------------------------
    # 64 MiB zone config (zsz=67108864, cap=67108864, inc=131072)
    # ------------------------------------------------------------
    10)
      # lazy, chunk=1
      zns_vtable_mode=1
      zns_zonesize=67108864
      zns_zonecap=67108864
      INCREMENT=131072
      ;;

    *)
      echo "ERROR: Unknown SSD_ID='$SSD_ID'"
      echo "Valid SSD_IDs: 0-4 (128MiB zones), 5-9 (256MiB zones)"
      exit 1
      ;;
  esac
}

# Apply SSD config based on SSD_ID
set_ssd_config



# specify experiment config
PARALLEL_ZONES=32

# ----- following should stay the same --------
DEVICE_PATH="/dev/nvme0n1"

# Set EXP_NAME depending on whether chunk config is used
EXP_NAME="vt-${zns_vtable_mode}_chnk-${zns_chunk_size}_maxc-${zns_max_chunks_per_lun}_minl-${zns_min_luns}_zsz-${zns_zonesize}_chnl-${zns_channels_per_zone}_w-${zns_ways_per_zone}"

zns_log_path=""
zns_log_path_time=""

# Set log path based on EXP_ID
if [[ "$EXP_ID" -eq 2 ]]; then
    zns_log_path="/home/teona/CIDR/raw-bench/exp_occupancy/new_results/finish-log"
    echo "Log path set to: $zns_log_path"
elif [[ "$EXP_ID" -eq 6 ]]; then
    zns_log_path_time="/home/teona/CIDR/raw-bench/exp_allocation/new_results/allocation-log"
    echo "Log path set to: $zns_log_path_time"
fi

# Paths
VM_SCRIPT="./run-zns-exp.sh"
VM_SCRIPT_PATH="/home/teona/CIDR/confznsplusplus/build-femu"
SSH_PORT=8080
VM_USER="teona"
VM_HOME="/home/${VM_USER}"
VM_RAW_BENCH="${VM_HOME}/raw-bench"
HOST_RAW_BENCH="/home/teona/CIDR/raw-bench"
RESULT_DIRS=("exp_allocation/new_results" "exp_interference/results" "exp_occupancy/new_results" "exp_rw_bench/new_results")

echo "Starting FEMU VM (vtable_mode=${zns_vtable_mode})"
echo "Experiment: EXP_ID=${EXP_ID}, REQUEST_SIZE=${REQUEST_SIZE}, INCREMENT=${INCREMENT}, PARALLEL_ZONES=${PARALLEL_ZONES}"

# Change directory to actual VM script location
cd "$VM_SCRIPT_PATH"

# Launch VM with zns_vtable_mode and other args
"$VM_SCRIPT" "$zns_vtable_mode" "$zns_chunk_size" "$zns_max_chunks_per_lun" "$zns_min_luns" \
            "$zns_log_path" "$zns_log_path_time" "$zns_zonesize" "$zns_zonecap" \
            "$zns_channels_per_zone" "$zns_ways_per_zone" &
FEMU_PID=$!

# Wait until SSH is ready
echo "Waiting for VM SSH to be reachable..."
until ssh -p $SSH_PORT -o ConnectTimeout=2 -o StrictHostKeyChecking=no "${VM_USER}@localhost" 'echo VM Ready' &>/dev/null; do
    sleep 2
done
echo "VM SSH is reachable."

# Clean the raw-bench directory inside the guest before copying
echo "Deleting previous raw-bench directory in VM..."
ssh -p $SSH_PORT -o StrictHostKeyChecking=no "${VM_USER}@localhost" "rm -rf '${VM_RAW_BENCH}'"

# Copy raw-bench to VM, excluding result contents
# IMPORTANT: This copies your updated .c files into the VM every run.
echo "Copying raw-bench to VM (fresh source files)..."
rsync -avz -e "ssh -p $SSH_PORT -o StrictHostKeyChecking=no" \
  --exclude '*/new_results/*' \
  --exclude '*/results/*' \
  "$HOST_RAW_BENCH/" \
  "${VM_USER}@localhost:${VM_RAW_BENCH}/"

# Compile inside VM (so you never run stale binaries)
# We compile occupancy/fill because you changed it to use pthreads and extra arg.
echo "Compiling updated C tools inside the VM..."
ssh -p $SSH_PORT -o StrictHostKeyChecking=no "${VM_USER}@localhost" "
  set -e
  cd '${VM_RAW_BENCH}'

  # Compile occupancy fill tool (updated to use pthreads)
  if [ -f 'exp_allocation/fill.c' ]; then
    echo '[VM] Building exp_occupancy/fill ...'
    cd exp_allocation
    mkdir -p new_results
    gcc -O2 -o fill fill.c -lzbd -lm -lpthread -Wall
    cd ..
  fi
"

# Run experiment inside VM (pass PARALLEL_ZONES as 6th arg)
echo "Running run_all.sh inside the VM..."
ssh -p $SSH_PORT -o StrictHostKeyChecking=no "${VM_USER}@localhost" \
  "cd '${VM_RAW_BENCH}' && bash run_all.sh '${EXP_NAME}' '${DEVICE_PATH}' '${REQUEST_SIZE}' '${EXP_ID}' '${INCREMENT}' '${PARALLEL_ZONES}'"

# Copy result files back to host
echo "Copying result files back from VM..."
for dir in "${RESULT_DIRS[@]}"; do
    LOCAL_RESULT_DIR="${HOST_RAW_BENCH}/${dir}"
    REMOTE_RESULT_DIR="${VM_RAW_BENCH}/${dir}"

    mkdir -p "${LOCAL_RESULT_DIR}"

    rsync -avz -e "ssh -p $SSH_PORT -o StrictHostKeyChecking=no" \
      "${VM_USER}@localhost:${REMOTE_RESULT_DIR}/" \
      "${LOCAL_RESULT_DIR}/"
done

# Shutdown VM
echo "Shutting down the VM..."
ssh -p $SSH_PORT -o StrictHostKeyChecking=no "${VM_USER}@localhost" "sudo /sbin/shutdown -h now"

# Wait for FEMU to finish
wait $FEMU_PID
echo "✅ VM shutdown complete. All experiments done."
