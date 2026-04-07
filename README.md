# 🚀 Running the Experiments

## Setup

Ensure the following are available:

- `confznsplusplus/build-femu/run-zns-exp.sh`
- `raw-bench/` with `run_all.sh`
- Working FEMU VM with SSH access
- Required tools in VM (e.g., `gcc`, `libzbd`)

---

## Configuration

Edit the **top section of the script**:

```bash
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
- EXP_ID: experiment type
- (0=all, 1=interference, 2=occupancy, 6=allocation)
- SSD_ID: selects SSD configuration (defined in script)
- DEVICE_PATH: NVMe device inside VM
- HOST_BASE_DIR: root directory containing:
   - raw-bench/
   - confznsplusplus/
- VM_USER, SSH_PORT: VM access credentials

### Run
```
chmod +x run_vm_experiment.sh
./run_vm_experiment.sh
```

Results are copied back to:

```
raw-bench/
├── exp_allocation/new_results/
├── exp_interference/results/
├── exp_occupancy/new_results/
└── exp_rw_bench/new_results/
```