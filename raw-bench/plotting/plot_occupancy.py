import os
import matplotlib.pyplot as plt
from collections import defaultdict
import matplotlib.ticker as mticker
import numpy as np
from matplotlib import rcParams

# === Font and style settings ===
rcParams["font.family"] = "Linux Libertine O"
# Font size settings (to match other plots)
TITLE_FONT_SIZE = 18
LABEL_FONT_SIZE = 16
TICK_FONT_SIZE = 16
LEGEND_FONT_SIZE = 11

# Path to results
input_path = "../exp_occupancy/results/finish-log-new"
output_path = "results/exp_occupancy_dlwa_barplot.pdf"

# Updated percentages (removed 0.001)
percentages = [10, 25, 50, 75, 95]
num_percentages = len(percentages)

# Mode to label mapping
mode_labels = {
    "0_0": "direct",
    "1_0": "lazy",
    "4_0": "stripe",
    "2_1": "chunk-1",
    "2_2": "chunk-2",
    "2_11": "chunk-11"
}

# Color & hatch map
color_map = {
    "chunk-1": "#aec7e8",
    "chunk-2": "#aec7e8",
    "chunk-11": "#aec7e8",
    "stripe": "#b5e7a0",
    "lazy": "#b0b0b0",
    "direct": "#b0b0b0"
}
hatch_map = {
    "chunk-1": None,
    "chunk-2": "///",
    "chunk-11": "xxx",
    "stripe": None,
    "lazy": None,
    "direct": "..."
}

# Step 1: Parse log and compute DLWA
raw_wa = defaultdict(list)

print("\n🔍 Parsing DLWA values:")
with open(input_path, 'r') as f:
    for line in f:
        line = line.strip()
        if not line or not line.startswith("mode"):
            continue

        parts = line.split(',')
        if len(parts) % 2 != 0:
            print("⚠️ Malformed line skipped:", line)
            continue

        entry = {parts[i]: parts[i+1] for i in range(0, len(parts) - 1, 2)}
        mode = entry.get("mode")
        chunk = entry.get("chunk_size")
        zone_slba = entry.get("zone_slba")
        wptr = entry.get("wptr")
        pages_finished = entry.get("pages_finished")

        if not all([mode, chunk, zone_slba, wptr, pages_finished]):
            print("⚠️ Missing values in line:", entry)
            continue

        key = f"{mode}_{chunk}"
        label = mode_labels.get(key)
        if label is None:
            print("⚠️ Unknown key skipped:", key)
            continue

        try:
            zone_slba = int(zone_slba)
            wptr = int(wptr)
            pages_finished = int(pages_finished)
            pages_written = (wptr - zone_slba) / 32

            if pages_written == 0:
                dlwa = 0
            else:
                dlwa = (pages_written + pages_finished) / pages_written

            if len(raw_wa[label]) < num_percentages:
                raw_wa[label].append(dlwa)
                print(f"  ✅ {label}: {len(raw_wa[label])}/{num_percentages} entries (DLWA = {dlwa:.3f})", flush=True)
            else:
                print(f"  ⚠️ Extra entry for {label} skipped (already has {num_percentages})")

        except ValueError:
            print(f"⚠️ Skipping invalid values in entry: {entry}")
            continue

# Step 2: Validate number of entries
for label in raw_wa:
    if len(raw_wa[label]) != num_percentages:
        print(f"⚠️ {label} has {len(raw_wa[label])} values, expected {num_percentages}")

# Step 3: Labels to plot
labels_to_plot = ["chunk-1", "chunk-2", "chunk-11", "stripe", "lazy", "direct"]

# Step 3.5: Compare DLWA reduction vs. direct for each percentage
print("\n📉 DLWA Reduction Compared to 'direct' (per occupancy level):")
baseline = raw_wa["direct"]

for label in ["chunk-1", "chunk-2", "chunk-11", "stripe"]:
    values = raw_wa[label]
    if len(values) != len(baseline):
        print(f"  ⚠️ Skipping {label} due to unequal number of entries.")
        continue

    print(f"\n  🔹 {label}:")
    for i, (b, v) in enumerate(zip(baseline, values)):
        if b == 0:
            reduction = 0.0
        else:
            reduction = 100 * (b - v) / b
        print(f"    - At {percentages[i]}% occupancy: {reduction:.2f}% lower DLWA than direct")



# Step 4: Plotting
plt.figure(figsize=(4, 3))
ax = plt.gca()
bar_width = 0.15
x = np.arange(len(percentages))
n = len(labels_to_plot)
offsets = np.linspace(-bar_width * (n - 1) / 2, bar_width * (n - 1) / 2, n)

for i, label in enumerate(labels_to_plot):
    values = raw_wa[label]
    ax.bar(
        x + offsets[i],
        values,
        width=bar_width,
        label=label,
        color=color_map[label],
        hatch=hatch_map[label],
        edgecolor="black",
        linewidth=0.8
    )

# Axis styling
ax.set_xticks(x)
ax.set_xticklabels([f"{p}%" for p in percentages], fontsize=TICK_FONT_SIZE)
ax.set_xlabel("(a) Zone Occupancy (%)", fontsize=LABEL_FONT_SIZE)
ax.set_ylabel("Write Amplification", fontsize=LABEL_FONT_SIZE)
ax.tick_params(axis='y', labelsize=TICK_FONT_SIZE)
ax.yaxis.grid(False)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.spines['left'].set_linewidth(1.2)
ax.spines['bottom'].set_linewidth(1.2)

# Legend (compact top-centered)
# Legend (top right inside plot)
ax.legend(
    loc="upper right",
    fontsize=LEGEND_FONT_SIZE,
    frameon=False,
    ncol=1
)


# Save and finish
plt.tight_layout()
plt.savefig(output_path)
plt.close()
print(f"\n✅ DLWA barplot saved to {output_path}")
