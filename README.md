# 🚀 Running the Experiments

## Step 1 — Clone the Repository (with Submodules)

This project depends on `confznsplusplus`, which is included as a Git submodule.

Clone the repository with:

```
git clone --recurse-submodules <your-repo-url>
cd SilentZNS-bench
```

If you already cloned without submodules, run:

```
git submodule update --init --recursive
```

## Step 2 — Build ConfZNS++ / FEMU

Navigate to the FEMU build directory:

cd confznsplusplus/build-femu

Build FEMU (if not already built):

```
./femu-compile.sh
```

## Step 3 — VM Requirements

Ensure:

SSH access to VM and host is configured

## Step 4 — Experiment Configuration

Edit the top section of the script:

```
EXP_ID=2
SSD_ID=0
PARALLEL_ZONES=8
DEVICE_PATH="/dev/nvme0n1"

HOST_BASE_DIR="/path/to/VLDB"

SSH_PORT=8080
VM_USER="your_vm_username"
VM_HOST="localhost"
```

### Parameters:
EXP_ID: experiment type
0 = all
1 = interference
2 = occupancy
6 = allocation
SSD_ID: selects SSD configuration (defined in script)
DEVICE_PATH: NVMe device inside VM
Example: /dev/nvme0n1

HOST_BASE_DIR: root directory containing:

```
raw-bench/
confznsplusplus/
```

VM_USER, SSH_PORT: VM access credentials


## Step 5 — Run Experiments

```
chmod +x run.sh
./run.sh
```

### Results

Results are copied back to:

```
raw-bench/
├── exp_allocation/new_results/
├── exp_interference/results/
├── exp_occupancy/new_results/
└── exp_rw_bench/new_results/
```