import statistics
import math
from collections import defaultdict

# ============================================================
# Input file
# ============================================================
INPUT_FILE = "../exp_allocation/new_results/allocation-log"

# ============================================================
# Helpers
# ============================================================
def bytes_to_mib(nbytes: int) -> int:
    return int(nbytes // (1024 * 1024))

def combo_title(minl: int, zsz: int) -> str:
    return f"P={minl}, S={bytes_to_mib(zsz)} MiB"

def config_label(mode: int, chnk: int):
    if mode == 1:
        return "fixed"
    if mode == 4:
        return "superblock"
    if mode == 2:
        if chnk == 1:
            return "block"
        if chnk == 2:
            return "hchunk-2"
        return None
    if mode == 5:
        return f"vchunk-{chnk}"
    return None

# ============================================================
# Data structure
# ============================================================
latencies = defaultdict(lambda: defaultdict(list))

# ============================================================
# Step 1: Parse file
# ============================================================
with open(INPUT_FILE, "r") as f:
    for line in f:
        line = line.strip()
        if not line:
            continue

        parts = line.split(",")

        if len(parts) % 2 != 0:
            continue

        entry = {parts[i]: parts[i + 1] for i in range(0, len(parts), 2)}

        try:
            mode = int(entry["vt"])
            chnk = int(entry["chnk"])
            minl = int(entry["minl"])
            zsz = int(entry["zsz"])
            time_ns = int(entry["time_ns"])
        except (KeyError, ValueError):
            continue

        label = config_label(mode, chnk)
        if label is None:
            continue

        combo = (minl, zsz)
        latencies[combo][label].append(time_ns)

# ============================================================
# Step 2: Compute medians and apply rounding rule
# ============================================================
CONFIG_ORDER = ["fixed", "superblock", "block", "hchunk-2", "vchunk-2", "vchunk-4"]

results = defaultdict(dict)

for combo in latencies:
    for label in latencies[combo]:
        values_ns = latencies[combo][label]

        median_ns = statistics.median(values_ns)
        median_us = median_ns / 1000.0

        if label == "fixed":
            final_val = round(median_us, 1)   # keep decimal
        else:
            final_val = math.ceil(median_us)  # round UP

        results[combo][label] = final_val

# ============================================================
# Step 3: Print output
# ============================================================
print("\n==================== MEDIAN ALLOCATION LATENCY ====================\n")

for combo in sorted(results.keys()):
    minl, zsz = combo
    print(combo_title(minl, zsz))

    for label in CONFIG_ORDER:
        if label not in results[combo]:
            continue

        val = results[combo][label]

        if label == "fixed":
            print(f"  {label}: {val:.1f} µs")
        else:
            print(f"  {label}: {int(val)} µs")

    print()