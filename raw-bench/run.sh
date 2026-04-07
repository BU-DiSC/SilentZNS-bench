#!/bin/bash
set -e  # Exit on any error

# ============================================================
# USER-CONFIGURABLE SETTINGS
# Edit only this section when moving the script to another machine
# ============================================================

# ----- Experiment selection -----
EXP_ID=2        # 0: all, 1: interference, 2: occupancy, 3: write-scaling, 4: read-scaling, 5: queue depth, 6: allocation
SSD_ID=0        # SSD config selector
PARALLEL_ZONES=8

# ----- Device settings inside the VM -----
DEVICE_PATH="/dev/nvme0n1"

# ----- Host paths -----
# Set this to the root directory that contains both:
#   1. raw-bench
#   2. confznsplusplus
HOST_BASE_DIR="/path/to/CIDR"

HOST_RAW_BENCH="${HOST_BASE_DIR}/raw-bench"
VM_SCRIPT_PATH="${HOST_BASE_DIR}/confznsplusplus/build-femu"
VM_SCRIPT="${VM_SCRIPT_PATH}/run-zns-exp.sh"

# Experiment log/output base directories on host
HOST_OCCUPANCY_LOG="${HOST_RAW_BENCH}/exp_occupancy/new_results/finish-log"
HOST_ALLOCATION_LOG="${HOST_RAW_BENCH}/exp_allocation/new_results/allocation-log"

# Result directories to copy back from VM
RESULT_DIRS=(
  "exp_allocation/new_results"
  "exp_interference/results"
  "exp_occupancy/new_results"
  "exp_rw_bench/new_results"
)

# ----- VM / SSH settings -----
# Set these to match your guest VM setup
SSH_PORT=8080
VM_USER="your_vm_username"
VM_HOST="localhost"
VM_HOME="/home/${VM_USER}"
VM_RAW_BENCH="${VM_HOME}/raw-bench"

# Optional SSH options for easier reuse
# For local controlled experiments, StrictHostKeyChecking=no is convenient.
# Remove it if you want stricter SSH verification.
SSH_OPTS=(-p "${SSH_PORT}" -o ConnectTimeout=2 -o StrictHostKeyChecking=no)
RSYNC_SSH="ssh -p ${SSH_PORT} -o StrictHostKeyChecking=no"

# ============================================================
# SSD CONFIG SELECTOR
# ============================================================
set_ssd_config() {
  # Default SSD Geometry
  zns_channels=8
  zns_ways=2
  zns_dies_per_chip=1
  zns_planes_per_die=1
  zns_block_size_pages=2048

  # Default SSD Timing
  zns_page_write_latency=500000
  zns_page_read_latency=50000
  zns_channel_transfer_latency=25000
  zns_block_erasure_latency=5000000

  # Default device size in MB
  devsz_mb=$((1024*16))

  case "$SSD_ID" in
    # ------------------------------------------------------------
    # 128 MiB zone parallelism = 16
    # ------------------------------------------------------------
    0)
      zns_vtable_mode=1
      zns_chunk_size=1
      zns_channels_per_zone=8
      zns_ways_per_zone=2
      zns_min_luns=16
      zns_max_chunks_per_lun=1
      zns_zonesize=134217728
      zns_zonecap=134217728
      INCREMENT=262144
      REQUEST_SIZE=4096
      ;;
    1)
      zns_vtable_mode=4
      zns_chunk_size=1
      zns_channels_per_zone=8
      zns_ways_per_zone=2
      zns_min_luns=16
      zns_max_chunks_per_lun=1
      zns_zonesize=134217728
      zns_zonecap=134217728
      INCREMENT=262144
      REQUEST_SIZE=4096
      ;;
    2)
      zns_vtable_mode=2
      zns_chunk_size=1
      zns_channels_per_zone=8
      zns_ways_per_zone=2
      zns_min_luns=16
      zns_max_chunks_per_lun=1
      zns_zonesize=134217728
      zns_zonecap=134217728
      INCREMENT=262144
      REQUEST_SIZE=4096
      ;;
    3)
      zns_vtable_mode=5
      zns_chunk_size=2
      zns_channels_per_zone=8
      zns_ways_per_zone=2
      zns_min_luns=16
      zns_max_chunks_per_lun=1
      zns_zonesize=134217728
      zns_zonecap=134217728
      INCREMENT=262144
      REQUEST_SIZE=4096
      ;;
    4)
      zns_vtable_mode=5
      zns_chunk_size=4
      zns_channels_per_zone=8
      zns_ways_per_zone=2
      zns_min_luns=16
      zns_max_chunks_per_lun=1
      zns_zonesize=134217728
      zns_zonecap=134217728
      INCREMENT=262144
      REQUEST_SIZE=4096
      ;;

    # ------------------------------------------------------------
    # 256 MiB zone parallelism = 16
    # ------------------------------------------------------------
    5)
      zns_vtable_mode=1
      zns_chunk_size=1
      zns_channels_per_zone=8
      zns_ways_per_zone=2
      zns_min_luns=16
      zns_max_chunks_per_lun=1
      zns_zonesize=268435456
      zns_zonecap=268435456
      INCREMENT=524288
      REQUEST_SIZE=4096
      ;;
    6)
      zns_vtable_mode=4
      zns_chunk_size=1
      zns_channels_per_zone=8
      zns_ways_per_zone=2
      zns_min_luns=16
      zns_max_chunks_per_lun=1
      zns_zonesize=268435456
      zns_zonecap=268435456
      INCREMENT=524288
      REQUEST_SIZE=4096
      ;;
    7)
      zns_vtable_mode=2
      zns_chunk_size=1
      zns_channels_per_zone=8
      zns_ways_per_zone=2
      zns_min_luns=16
      zns_max_chunks_per_lun=2
      zns_zonesize=268435456
      zns_zonecap=268435456
      INCREMENT=524288
      REQUEST_SIZE=4096
      ;;
    8)
      zns_vtable_mode=5
      zns_chunk_size=2
      zns_channels_per_zone=8
      zns_ways_per_zone=2
      zns_min_luns=16
      zns_max_chunks_per_lun=2
      zns_zonesize=268435456
      zns_zonecap=268435456
      INCREMENT=524288
      REQUEST_SIZE=4096
      ;;
    9)
      zns_vtable_mode=5
      zns_chunk_size=4
      zns_channels_per_zone=8
      zns_ways_per_zone=2
      zns_min_luns=16
      zns_max_chunks_per_lun=2
      zns_zonesize=268435456
      zns_zonecap=268435456
      INCREMENT=524288
      REQUEST_SIZE=4096
      ;;

    # ------------------------------------------------------------
    # 64 MiB zone parallelism = 8
    # ------------------------------------------------------------
    10)
      zns_vtable_mode=1
      zns_chunk_size=1
      zns_channels_per_zone=8
      zns_ways_per_zone=1
      zns_min_luns=8
      zns_max_chunks_per_lun=1
      zns_zonesize=67108864
      zns_zonecap=67108864
      INCREMENT=131072
      REQUEST_SIZE=4096
      ;;
    11)
      zns_vtable_mode=2
      zns_chunk_size=1
      zns_channels_per_zone=8
      zns_ways_per_zone=1
      zns_min_luns=8
      zns_max_chunks_per_lun=1
      zns_zonesize=67108864
      zns_zonecap=67108864
      INCREMENT=131072
      REQUEST_SIZE=4096
      ;;
    12)
      zns_vtable_mode=5
      zns_chunk_size=2
      zns_channels_per_zone=8
      zns_ways_per_zone=1
      zns_min_luns=8
      zns_max_chunks_per_lun=1
      zns_zonesize=67108864
      zns_zonecap=67108864
      INCREMENT=131072
      REQUEST_SIZE=4096
      ;;
    13)
      zns_vtable_mode=5
      zns_chunk_size=4
      zns_channels_per_zone=8
      zns_ways_per_zone=1
      zns_min_luns=8
      zns_max_chunks_per_lun=1
      zns_zonesize=67108864
      zns_zonecap=67108864
      INCREMENT=131072
      REQUEST_SIZE=4096
      ;;

    # ------------------------------------------------------------
    # 128 MiB zone parallelism = 8
    # ------------------------------------------------------------
    14)
      zns_vtable_mode=1
      zns_chunk_size=1
      zns_channels_per_zone=8
      zns_ways_per_zone=1
      zns_min_luns=8
      zns_max_chunks_per_lun=1
      zns_zonesize=134217728
      zns_zonecap=134217728
      INCREMENT=262144
      REQUEST_SIZE=4096
      ;;
    15)
      zns_vtable_mode=2
      zns_chunk_size=1
      zns_channels_per_zone=8
      zns_ways_per_zone=1
      zns_min_luns=8
      zns_max_chunks_per_lun=2
      zns_zonesize=134217728
      zns_zonecap=134217728
      INCREMENT=262144
      REQUEST_SIZE=4096
      ;;
    16)
      zns_vtable_mode=5
      zns_chunk_size=2
      zns_channels_per_zone=8
      zns_ways_per_zone=1
      zns_min_luns=8
      zns_max_chunks_per_lun=2
      zns_zonesize=134217728
      zns_zonecap=134217728
      INCREMENT=262144
      REQUEST_SIZE=4096
      ;;
    17)
      zns_vtable_mode=5
      zns_chunk_size=4
      zns_channels_per_zone=8
      zns_ways_per_zone=1
      zns_min_luns=8
      zns_max_chunks_per_lun=2
      zns_zonesize=134217728
      zns_zonecap=134217728
      INCREMENT=262144
      REQUEST_SIZE=4096
      ;;

    # ------------------------------------------------------------
    # 32 MiB zone parallelism = 4
    # ------------------------------------------------------------
    18)
      zns_vtable_mode=1
      zns_chunk_size=1
      zns_channels_per_zone=4
      zns_ways_per_zone=1
      zns_min_luns=4
      zns_max_chunks_per_lun=1
      zns_zonesize=33554432
      zns_zonecap=33554432
      INCREMENT=65536
      REQUEST_SIZE=4096
      ;;
    19)
      zns_vtable_mode=2
      zns_chunk_size=1
      zns_channels_per_zone=4
      zns_ways_per_zone=1
      zns_min_luns=4
      zns_max_chunks_per_lun=1
      zns_zonesize=33554432
      zns_zonecap=33554432
      INCREMENT=65536
      REQUEST_SIZE=4096
      ;;
    20)
      zns_vtable_mode=5
      zns_chunk_size=2
      zns_channels_per_zone=4
      zns_ways_per_zone=1
      zns_min_luns=4
      zns_max_chunks_per_lun=1
      zns_zonesize=33554432
      zns_zonecap=33554432
      INCREMENT=65536
      REQUEST_SIZE=4096
      ;;
    21)
      zns_vtable_mode=5
      zns_chunk_size=4
      zns_channels_per_zone=4
      zns_ways_per_zone=1
      zns_min_luns=4
      zns_max_chunks_per_lun=1
      zns_zonesize=33554432
      zns_zonecap=33554432
      INCREMENT=65536
      REQUEST_SIZE=4096
      ;;

    # ------------------------------------------------------------
    # 64 MiB zone parallelism = 4
    # ------------------------------------------------------------
    22)
      zns_vtable_mode=1
      zns_chunk_size=1
      zns_channels_per_zone=4
      zns_ways_per_zone=1
      zns_min_luns=4
      zns_max_chunks_per_lun=1
      zns_zonesize=67108864
      zns_zonecap=67108864
      INCREMENT=131072
      REQUEST_SIZE=4096
      ;;
    23)
      zns_vtable_mode=2
      zns_chunk_size=1
      zns_channels_per_zone=4
      zns_ways_per_zone=1
      zns_min_luns=4
      zns_max_chunks_per_lun=2
      zns_zonesize=67108864
      zns_zonecap=67108864
      INCREMENT=131072
      REQUEST_SIZE=4096
      ;;
    24)
      zns_vtable_mode=5
      zns_chunk_size=2
      zns_channels_per_zone=4
      zns_ways_per_zone=1
      zns_min_luns=4
      zns_max_chunks_per_lun=2
      zns_zonesize=67108864
      zns_zonecap=67108864
      INCREMENT=131072
      REQUEST_SIZE=4096
      ;;
    25)
      zns_vtable_mode=5
      zns_chunk_size=4
      zns_channels_per_zone=4
      zns_ways_per_zone=1
      zns_min_luns=4
      zns_max_chunks_per_lun=2
      zns_zonesize=67108864
      zns_zonecap=67108864
      INCREMENT=131072
      REQUEST_SIZE=4096
      ;;

    # ------------------------------------------------------------
    # ConfZNS++
    # ------------------------------------------------------------
    26)
      zns_channels=4
      zns_ways=1
      zns_dies_per_chip=1
      zns_planes_per_die=1
      zns_block_size_pages=768

      zns_page_write_latency=700000
      zns_page_read_latency=60000
      zns_channel_transfer_latency=25000
      zns_block_erasure_latency=3500000

      devsz_mb=$((1024*8*12))

      zns_vtable_mode=1
      zns_chunk_size=1
      zns_channels_per_zone=4
      zns_ways_per_zone=1
      zns_min_luns=4
      zns_max_chunks_per_lun=1
      zns_zonesize=2147483648
      zns_zonecap=1107296256
      INCREMENT=4194304
      REQUEST_SIZE=16384
      ;;

    27)
      zns_channels=4
      zns_ways=1
      zns_dies_per_chip=1
      zns_planes_per_die=1
      zns_block_size_pages=768

      zns_page_write_latency=700000
      zns_page_read_latency=60000
      zns_channel_transfer_latency=25000
      zns_block_erasure_latency=3500000

      devsz_mb=$((1024*8*12))

      zns_vtable_mode=4
      zns_chunk_size=1
      zns_channels_per_zone=4
      zns_ways_per_zone=1
      zns_min_luns=4
      zns_max_chunks_per_lun=1
      zns_zonesize=2147483648
      zns_zonecap=1107296256
      INCREMENT=4194304
      REQUEST_SIZE=16384
      ;;

    # Hchunk config P = 16, S = 256
    28)
      zns_vtable_mode=2
      zns_chunk_size=2
      zns_channels_per_zone=8
      zns_ways_per_zone=2
      zns_min_luns=16
      zns_max_chunks_per_lun=1
      zns_zonesize=268435456
      zns_zonecap=268435456
      INCREMENT=524288
      REQUEST_SIZE=4096
      ;;

    # Hchunk config P = 8, S = 128
    29)
      zns_vtable_mode=2
      zns_chunk_size=2
      zns_channels_per_zone=8
      zns_ways_per_zone=1
      zns_min_luns=8
      zns_max_chunks_per_lun=1
      zns_zonesize=134217728
      zns_zonecap=134217728
      INCREMENT=262144
      REQUEST_SIZE=4096
      ;;

    # Hchunk config P = 4, S = 64
    30)
      zns_vtable_mode=2
      zns_chunk_size=2
      zns_channels_per_zone=4
      zns_ways_per_zone=1
      zns_min_luns=4
      zns_max_chunks_per_lun=1
      zns_zonesize=67108864
      zns_zonecap=67108864
      INCREMENT=131072
      REQUEST_SIZE=4096
      ;;

    *)
      echo "ERROR: Unknown SSD_ID='$SSD_ID'"
      echo "Valid SSD_IDs: 0-30"
      exit 1
      ;;
  esac
}

# ============================================================
# INITIALIZATION
# ============================================================
set_ssd_config

EXP_NAME="vt-${zns_vtable_mode}_chnk-${zns_chunk_size}_maxc-${zns_max_chunks_per_lun}_minl-${zns_min_luns}_zsz-${zns_zonesize}_chnl-${zns_channels_per_zone}_w-${zns_ways_per_zone}"

zns_log_path=""
zns_log_path_time=""

case "$EXP_ID" in
  2)
    zns_log_path="${HOST_OCCUPANCY_LOG}"
    echo "Log path set to: ${zns_log_path}"
    ;;
  6)
    zns_log_path_time="${HOST_ALLOCATION_LOG}"
    echo "Log path set to: ${zns_log_path_time}"
    ;;
esac

echo "Starting FEMU VM (vtable_mode=${zns_vtable_mode})"
echo "Experiment: EXP_ID=${EXP_ID}, REQUEST_SIZE=${REQUEST_SIZE}, INCREMENT=${INCREMENT}, PARALLEL_ZONES=${PARALLEL_ZONES}"
echo "Geometry: channels=${zns_channels}, ways=${zns_ways}, dies_per_chip=${zns_dies_per_chip}, planes_per_die=${zns_planes_per_die}, block_size_pages=${zns_block_size_pages}"
echo "Timing: page_write=${zns_page_write_latency}, page_read=${zns_page_read_latency}, transfer=${zns_channel_transfer_latency}, erase=${zns_block_erasure_latency}"
echo "Device size: devsz_mb=${devsz_mb}"

# ============================================================
# LAUNCH VM
# ============================================================
cd "${VM_SCRIPT_PATH}"

"${VM_SCRIPT}" \
  "${zns_vtable_mode}" \
  "${zns_chunk_size}" \
  "${zns_max_chunks_per_lun}" \
  "${zns_min_luns}" \
  "${zns_log_path}" \
  "${zns_log_path_time}" \
  "${zns_zonesize}" \
  "${zns_zonecap}" \
  "${zns_channels_per_zone}" \
  "${zns_ways_per_zone}" \
  "${zns_channels}" \
  "${zns_ways}" \
  "${zns_dies_per_chip}" \
  "${zns_planes_per_die}" \
  "${zns_block_size_pages}" \
  "${zns_page_write_latency}" \
  "${zns_page_read_latency}" \
  "${zns_channel_transfer_latency}" \
  "${zns_block_erasure_latency}" \
  "${devsz_mb}" &
FEMU_PID=$!

# ============================================================
# WAIT FOR SSH
# ============================================================
echo "Waiting for VM SSH to be reachable..."
until ssh "${SSH_OPTS[@]}" "${VM_USER}@${VM_HOST}" 'echo VM Ready' &>/dev/null; do
  sleep 2
done
echo "VM SSH is reachable."

# ============================================================
# PREPARE VM
# ============================================================
echo "Deleting previous raw-bench directory in VM..."
ssh "${SSH_OPTS[@]}" "${VM_USER}@${VM_HOST}" "rm -rf '${VM_RAW_BENCH}'"

echo "Copying raw-bench to VM (fresh source files)..."
rsync -avz -e "${RSYNC_SSH}" \
  --exclude '*/new_results/*' \
  --exclude '*/results/*' \
  "${HOST_RAW_BENCH}/" \
  "${VM_USER}@${VM_HOST}:${VM_RAW_BENCH}/"

echo "Compiling updated C tools inside the VM..."
ssh "${SSH_OPTS[@]}" "${VM_USER}@${VM_HOST}" "
  set -e
  cd '${VM_RAW_BENCH}'

  if [ -f 'exp_allocation/fill.c' ]; then
    echo '[VM] Building exp_allocation/fill ...'
    cd exp_allocation
    mkdir -p new_results
    gcc -O2 -o fill fill.c -lzbd -lm -lpthread -Wall
    cd ..
  fi
"

# ============================================================
# RUN EXPERIMENT
# ============================================================
echo "Running run_all.sh inside the VM..."
ssh "${SSH_OPTS[@]}" "${VM_USER}@${VM_HOST}" \
  "cd '${VM_RAW_BENCH}' && bash run_all.sh '${EXP_NAME}' '${DEVICE_PATH}' '${REQUEST_SIZE}' '${EXP_ID}' '${INCREMENT}' '${PARALLEL_ZONES}'"

# ============================================================
# COPY RESULTS BACK
# ============================================================
echo "Copying result files back from VM..."
for dir in "${RESULT_DIRS[@]}"; do
  LOCAL_RESULT_DIR="${HOST_RAW_BENCH}/${dir}"
  REMOTE_RESULT_DIR="${VM_RAW_BENCH}/${dir}"

  mkdir -p "${LOCAL_RESULT_DIR}"

  rsync -avz -e "${RSYNC_SSH}" \
    "${VM_USER}@${VM_HOST}:${REMOTE_RESULT_DIR}/" \
    "${LOCAL_RESULT_DIR}/"
done

# ============================================================
# SHUT DOWN VM
# ============================================================
echo "Shutting down the VM..."
ssh "${SSH_OPTS[@]}" "${VM_USER}@${VM_HOST}" "sudo /sbin/shutdown -h now"

wait "${FEMU_PID}"
echo "✅ VM shutdown complete. All experiments done."