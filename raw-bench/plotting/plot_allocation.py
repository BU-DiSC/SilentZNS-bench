import os
import matplotlib.pyplot as plt
from collections import defaultdict
import numpy as np
from matplotlib import rcParams

# === Font and style settings ===
rcParams["font.family"] = "Linux Libertine O"
TITLE_FONT_SIZE = 18
LABEL_FONT_SIZE = 16
TICK_FONT_SIZE = 16
LEGEND_FONT_SIZE = 11
LINE_WIDTH = 1.8
MARKER_SIZE = 10
SPINE_WIDTH = 1.2

# === File paths ===
input_path = "../exp_allocation/results/allocation-log"
output_path = "results/exp_allocation_latency_means.pdf"

# === Mode → label mapping ===
mode_labels = {
    "1_1": "lazy",
    "2_1": "chunk-1",
    "2_2": "chunk-2",
    "2_11": "chunk-11",
    "4_1": "stripe"
}

# === Sharp color and hatch mappings ===
color_map = {
    "chunk-1": "#aec7e8",
    "chunk-2": "#aec7e8",
    "chunk-11": "#aec7e8",
    "stripe": "#b5e7a0",
    "lazy": "black",
    "direct": "black"
}

hatch_map = {
    "chunk-1": None,
    "chunk-2": "///",
    "chunk-11": "xxx",
    "stripe": None,
}

# === Step 1: Parse log file and collect latencies ===
latencies_by_label = defaultdict(list)

with open(input_path, 'r') as f:
    for line in f:
        line = line.strip()
        if not line.startswith("mode"):
            continue

        parts = line.split(',')
        if len(parts) < 6:
            continue

        mode = parts[1]
        chunk = parts[3]
        time_us = parts[5]

        if mode == "0":
            continue  # skip direct

        key = f"{mode}_{chunk}"
        label = mode_labels.get(key)
        if not label:
            continue

        try:
            latency = int(time_us.replace("(us)", "")) / 1000  # µs → ms
            latencies_by_label[label].append(latency)
        except ValueError:
            continue

# === Step 2: Compute means ===
mean_latencies = {label: np.mean(latencies) for label, latencies in latencies_by_label.items()}

# === Step 3: Print all means (incl. lazy) ===
print("\n📊 (d) Allocation Latency (ms):")
for label, mean in sorted(mean_latencies.items()):
    print(f"  {label:10s} : {mean:.3f} ms")

# === Step 4: Filter for plotting (exclude lazy) ===
plot_labels = [label for label in mean_latencies if label != "lazy"]
means = [mean_latencies[label] for label in plot_labels]
positions = np.arange(len(plot_labels))

# === Step 5: Define short labels for legend/x-axis ===
short_label_map = {
    "chunk-1": "ch1",
    "chunk-2": "ch2",
    "chunk-11": "ch11",
    "stripe": "stripe"
}
short_labels = [short_label_map[label] for label in plot_labels]

# === Step 6: Plot ===
plt.figure(figsize=(4, 3))
ax = plt.gca()

bars = ax.bar(
    positions,
    means,
    color=[color_map[lbl] for lbl in plot_labels],
    edgecolor="black",
    width=0.5,
    linewidth=1.2
)

# === Apply hatches ===
for bar, label in zip(bars, plot_labels):
    hatch = hatch_map.get(label)
    if hatch:
        bar.set_hatch(hatch)

# === Axes styling ===
ax.set_ylabel("Allocation Latency (ms)", fontsize=LABEL_FONT_SIZE)
ax.set_xlabel("(d) Mapping Strategy", fontsize=LABEL_FONT_SIZE)
ax.set_xticks(positions)
ax.set_xticklabels(short_labels, fontsize=TICK_FONT_SIZE, ha="center")
ax.tick_params(axis='y', labelsize=TICK_FONT_SIZE)
ax.set_ylim(bottom=0)
ax.grid(False)  # Disable grid
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.spines['left'].set_linewidth(SPINE_WIDTH)
ax.spines['bottom'].set_linewidth(SPINE_WIDTH)

# === Save ===
plt.tight_layout()
os.makedirs("results", exist_ok=True)
plt.savefig(output_path)
plt.close()
print(f"\n✅ Mean latency barplot saved to {output_path}")
