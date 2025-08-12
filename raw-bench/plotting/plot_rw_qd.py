import os
import json
import re
import matplotlib.pyplot as plt

# Directory where result JSON files are stored
RESULTS_DIR = "../exp_rw_bench/results"

# Output plot paths
OUTPUT_IOPS = "results/rw-qd-io.pdf"
OUTPUT_BW   = "results/rw-qd-bw.pdf"

qdepths = []
k_iops = []
mb_bw = []

# Pattern: ZN540_qd_<depth>.json
pattern = re.compile(r"ZN540_qd_(\d+)\.json")

for filename in sorted(os.listdir(RESULTS_DIR)):
    match = pattern.match(filename)
    if not match:
        continue

    qd = int(match.group(1))
    filepath = os.path.join(RESULTS_DIR, filename)

    try:
        with open(filepath, "r") as f:
            data = json.load(f)

        job = data["jobs"][0]
        iops = float(job["write"]["iops"])
        bw_bytes = float(job["write"]["bw_bytes"])

        qdepths.append(qd)
        k_iops.append(iops / 1000.0)         # Convert to KIOPS
        mb_bw.append(bw_bytes / (1024 ** 2)) # Convert to MB/s

    except Exception as e:
        print(f"Skipping {filename}: {e}")

# Sort all metrics by queue depth
sorted_all = sorted(zip(qdepths, k_iops, mb_bw))
qd_sorted, k_iops_sorted, mb_bw_sorted = zip(*sorted_all)


def minimalist_plot(x, y, xlabel, ylabel, title, save_path):
    plt.figure(figsize=(8, 6))
    plt.plot(x, y, marker='o', linewidth=2)

    plt.xlabel(xlabel, fontsize=14)
    plt.ylabel(ylabel, fontsize=14)
    plt.title(title, fontsize=16)

    # Remove top and right spines
    ax = plt.gca()
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['bottom'].set_linewidth(1.5)
    ax.spines['left'].set_linewidth(1.5)

    # Keep only left and bottom ticks
    ax.yaxis.set_ticks_position('left')
    ax.xaxis.set_ticks_position('bottom')

    # Enable only horizontal grid lines
    ax.yaxis.grid(True, linestyle='--', linewidth=0.5)
    ax.xaxis.grid(False)

    plt.xticks(x)
    plt.xlim(left=0)
    plt.ylim(bottom=0)
    plt.tight_layout()
    plt.savefig(save_path)
    print(f"Plot saved to: {save_path}")


# Plot IOPS
minimalist_plot(
    qd_sorted, k_iops_sorted,
    xlabel="Queue Depth",
    ylabel="Throughput (KIOPS)",
    title="Fio 16k write",
    save_path=OUTPUT_IOPS
)

# Plot Bandwidth
minimalist_plot(
    qd_sorted, mb_bw_sorted,
    xlabel="Queue Depth",
    ylabel="Bandwidth (MB/s)",
    title="Fio 16k write",
    save_path=OUTPUT_BW
)
