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

## Step 2 — Install and Configure MOSEK

MOSEK is required for building the allocation components.

### 2.1 Download MOSEK

Download MOSEK from:
https://www.mosek.com/downloads/

Extract it to a location of your choice, for example: `/path/to/mosek`

### 2.2 Set Environment Variables

Add the following to your shell (or `.bashrc`):

```
export MOSEK_ROOT="/path/to/mosek"
export MOSEK_PLATFORM="$MOSEK_ROOT/11.0/tools/platform/linux64x86"

export MOSEKLM_LICENSE_FILE="/path/to/mosek/license/mosek.lic"
export LD_LIBRARY_PATH="$MOSEK_PLATFORM/bin:$LD_LIBRARY_PATH"
```

### 2.3 Verify Installation

Run: `ls $MOSEK_PLATFORM/bin`

## Step 3 — Build ConfZNS++ / FEMU

Navigate to the FEMU build directory:

cd confznsplusplus/build-femu

Build FEMU (if not already built):

```
./femu-compile.sh
```

## Step 4 — VM Requirements

Ensure:

SSH access to VM and host is configured

## Step 5 — Experiment Configuration

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
```
EXP_ID: experiment type
0 = all
1 = interference
2 = occupancy
6 = allocation
SSD_ID: selects SSD configuration (defined in script)
DEVICE_PATH: NVMe device inside VM
Example: /dev/nvme0n1
```

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