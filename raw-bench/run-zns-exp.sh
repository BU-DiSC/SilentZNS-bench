#!/bin/bash
set -e

# Image directory
OSIMGF=/home/teona/femu.qcow2

if [ $# -ne 10 ]; then
    echo "Usage: $0 <VTABLE_MODE>"
    echo "Example: $0 2   # 0=direct, 1=lazy, 2=full, 3=flexible, 4=stripe"
    exit 1
fi

zns_vtable_mode="$1" # 0: direct, 1: lazy, 2: full, 3: flexible, 4: stripe
zns_chunk_size="$2" # set chunk_size to integer greater than 1 for chunk allocation scheme. For now this is used for modes 2 and 3 and ignored for the rest
# Config parallelism for mode 3, ignored for the other modes
zns_max_chunks_per_lun="$3"
zns_min_luns="$4"
zns_log_path="$5"
zns_log_path_time="$6"
zns_zonesize="$7"
zns_zonecap="$8"
zns_channels_per_zone="$9"
zns_ways_per_zone="${10}"

if [[ ! -e "$OSIMGF" ]]; then
    echo ""
    echo "VM disk image couldn't be found ..."
    echo "Please prepare a usable VM image and place it as $OSIMGF"
    echo "Once VM disk image is ready, please rerun this script again"
    echo ""
    exit
fi

# devsz_mb=$((1024*64))
devsz_mb=$((1024*16))
femu_mode=3 # use 3 for ZNS mode
queues=64

# SSD Geometry
zns_channels=8
zns_ways=1
zns_dies_per_chip=1
zns_planes_per_die=2
zns_block_size_pages=2048

# SSD Timing
zns_page_write_latency=500000
zns_page_read_latency=50000
zns_channel_transfer_latency=25000
zns_block_erasure_latency=5000000

# ZNS specific config
zns_allow_partial_resets=1 # relevant for mode 0 and 1, other modes use partial reset by default
zns_asynchronous_resets=1 # relevant only for modes 0 and 1

zns_debug=1

# QEMU Launch
sudo x86_64-softmmu/qemu-system-x86_64 \
    -name "FEMU-ZNSSD" \
    -enable-kvm \
    -cpu host \
    -smp 20 \
    -m 64G \
    -device virtio-scsi-pci,id=scsi0 \
    -device scsi-hd,drive=hd0 \
    -drive file=$OSIMGF,if=none,aio=native,cache=none,format=qcow2,id=hd0 \
    -device femu,devsz_mb=${devsz_mb},id=nvme0,femu_mode=${femu_mode},queues=${queues},\
zns_zonesize=${zns_zonesize},zns_zonecap=${zns_zonecap},\
zns_channels=${zns_channels},zns_channels_per_zone=${zns_channels_per_zone},\
zns_ways=${zns_ways},zns_ways_per_zone=${zns_ways_per_zone},\
zns_dies_per_chip=${zns_dies_per_chip},zns_planes_per_die=${zns_planes_per_die},\
zns_page_write_latency=${zns_page_write_latency},zns_page_read_latency=${zns_page_read_latency},\
zns_channel_transfer_latency=${zns_channel_transfer_latency},zns_block_erasure_latency=${zns_block_erasure_latency},\
zns_allow_partial_resets=${zns_allow_partial_resets},zns_asynchronous_resets=${zns_asynchronous_resets},\
zns_vtable_mode=${zns_vtable_mode},zns_block_size_pages=${zns_block_size_pages},\
zns_chunk_size=${zns_chunk_size},zns_max_chunks_per_lun=${zns_max_chunks_per_lun},zns_min_luns=${zns_min_luns},zns_debug=${zns_debug},zns_log_path=${zns_log_path},zns_log_path_time=${zns_log_path_time} \
    -net user,hostfwd=tcp::8080-:22 \
    -net nic,model=virtio \
    -nographic \
    -qmp unix:./qmp-sock,server,nowait 2>&1 | tee log


