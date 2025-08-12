import os
import re
import json
import matplotlib.pyplot as plt

# Directory with JSON files
RESULTS_DIR = "../exp_rw_bench/results"
OUTPUT_PATH = "results/mode3_chnk1_maxchunks_plot.pdf"

# Patterns
pattern_chunked = re.compile(r"3-chnk-1-(\d+)_threads_(\d+)\.json")
pattern_full = re.compile(r"2_threads_(\d+)\.json")

# Store results by maxchunks: {maxchunks: {threads: iops}}
chunk_grouped_results = {}

# Store "full" configuration: {threads: iops}
full_iops_results = {}

# Parse all files
for fname in os.listdir(RESULTS_DIR):
    fpath = os.path.join(RESULTS_DIR, fname)

    chunked_match = pattern_chunked.match(fname)
    full_match = pattern_full.match(fname)

    try:
        with open(fpath) as f:
            data = json.load(f)
            iops = float(data["jobs"][0]["write"]["iops"]) / 1000.0  # KIOPS

            if chunked_match:
                maxchunks = int(chunked_match.group(1))
                thread_count = int(chunked_match.group(2))

                if maxchunks not in chunk_grouped_results:
                    chunk_grouped_results[maxchunks] = {}
                chunk_grouped_results[maxchunks][thread_count] = iops

            elif full_match:
                thread_count = int(full_match.group(1))
                full_iops_results[thread_count] = iops

    except Exception as e:
        print(f"⚠️ Failed to read {fname}: {e}")

# --- Plotting ---
plt.figure(figsize=(10, 7))

# Plot chunked configurations
for maxchunks in sorted(chunk_grouped_results.keys()):
    thread_iops_map = chunk_grouped_results[maxchunks]
    threads = sorted(thread_iops_map.keys())
    iops_vals = [thread_iops_map[t] for t in threads]

    plt.plot(
        threads,
        iops_vals,
        marker='o',
        linewidth=2,
        markersize=6,
        label=f"maxchunks={maxchunks}"
    )

# Plot "full" configuration
if full_iops_results:
    full_threads = sorted(full_iops_results.keys())
    full_iops_vals = [full_iops_results[t] for t in full_threads]

    plt.plot(
        full_threads,
        full_iops_vals,
        marker='s',
        linestyle='--',
        linewidth=2,
        markersize=6,
        color='gray',
        label="full"
    )

# --- Formatting ---
plt.xlabel("Number of Threads", fontsize=14)
plt.ylabel("IOPS (KIOPS)", fontsize=14)
plt.title("Mode 3 with 1 Chunk – Varying Max Chunks per LUN", fontsize=16)
plt.grid(True, linestyle='--', linewidth=0.5)
plt.xticks(sorted(set().union(*[set(d.keys()) for d in chunk_grouped_results.values()])))
plt.ylim(bottom=0)
plt.legend(title="Configuration", fontsize=12, title_fontsize=13)

plt.tight_layout()
os.makedirs("results", exist_ok=True)
plt.savefig(OUTPUT_PATH)
print(f"✅ Saved plot to: {OUTPUT_PATH}")
