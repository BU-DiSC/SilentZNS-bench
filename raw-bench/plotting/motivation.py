import os
import re
import json
import math
import numpy as np
import matplotlib.pyplot as plt
from collections import defaultdict
from matplotlib import rcParams

# Try smooth interpolation
try:
    from scipy.interpolate import PchipInterpolator
    HAS_PCHIP = True
except ImportError:
    HAS_PCHIP = False

# ============================================================
# Style settings
# ============================================================
rcParams["font.family"] = "Linux Libertine O"
rcParams["pdf.fonttype"] = 42
rcParams["ps.fonttype"] = 42

LABEL_FONT_SIZE = 18
TICK_FONT_SIZE = 18
LINE_WIDTH = 1.8
SPINE_WIDTH = 1.2
LEGEND_FONT_SIZE = 12

# ============================================================
# Paths
# ============================================================
INTERFERENCE_RESULT_DIR = "../exp_interference/results"
DLWA_INPUT_PATH = "../exp_occupancy/new_results/finish-log"

OUT_DIR = "results_zn540"
os.makedirs(OUT_DIR, exist_ok=True)

OUTPUT_PATH = os.path.join(OUT_DIR, "combined_dlwa_interference.pdf")

# ============================================================
# Occupancy
# ============================================================
PERCENTAGES = [0.01, 10, 20, 30, 40, 50, 60, 70, 80, 90, 99.99]
START_IDX = 1
END_IDX = 10
PLOT_PERCENTAGES = PERCENTAGES[START_IDX:END_IDX]

# ============================================================
# Helpers
# ============================================================
def style_axes(ax):
    ax.grid(False)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_linewidth(SPINE_WIDTH)
    ax.spines["bottom"].set_linewidth(SPINE_WIDTH)
    ax.tick_params(axis="both", labelsize=TICK_FONT_SIZE, width=SPINE_WIDTH, length=3)

def smooth_curve(x, y, num_points=300):
    x = np.array(x, dtype=float)
    y = np.array(y, dtype=float)

    x_dense = np.linspace(x.min(), x.max(), num_points)

    if HAS_PCHIP and len(x) >= 2:
        interpolator = PchipInterpolator(x, y)
        y_dense = interpolator(x_dense)
    else:
        y_dense = np.interp(x_dense, x, y)

    return x_dense, y_dense

# ============================================================
# -------- DLWA DATA --------
# ============================================================
dlwa_all = defaultdict(list)

with open(DLWA_INPUT_PATH, "r") as f:
    for line in f:
        if not line.startswith("mode"):
            continue

        parts = line.strip().split(",")
        entry = {parts[i]: parts[i + 1] for i in range(0, len(parts), 2)}

        try:
            if int(entry["mode"]) != 1:
                continue

            pf = int(entry["pages_finished"])
            zone_slba = int(entry["zone_slba"])
            wptr = int(entry["wptr"])
        except:
            continue

        host_pages = (wptr - zone_slba) / 32.0
        dlwa = (host_pages + pf) / host_pages if host_pages > 0 else np.nan

        if len(dlwa_all["baseline"]) < len(PERCENTAGES):
            dlwa_all["baseline"].append(dlwa)

baseline_dlwa = dlwa_all["baseline"][START_IDX:END_IDX]

x_smooth_dlwa, y_smooth_dlwa = smooth_curve(PLOT_PERCENTAGES, baseline_dlwa)

xmin_dlwa, xmax_dlwa = PLOT_PERCENTAGES[0], PLOT_PERCENTAGES[-1]
xpad_dlwa = 0.04 * (xmax_dlwa - xmin_dlwa)

dlwa_ymin = 0
dlwa_ymax = max(baseline_dlwa) * 1.08

# ============================================================
# -------- INTERFERENCE DATA --------
# ============================================================
def parse_filename(fname):
    pattern = re.compile(r"vt-(\d+).*_(\d+)jobs(_finish)?\.json")
    m = pattern.match(fname)
    if not m:
        return None
    return int(m.group(1)), int(m.group(2)), m.group(3) is not None

baseline = {}
finish = {}

for fname in os.listdir(INTERFERENCE_RESULT_DIR):
    if not fname.endswith(".json"):
        continue

    parsed = parse_filename(fname)
    if parsed is None:
        continue

    mode, jobs, is_finish = parsed
    if mode != 1:
        continue

    path = os.path.join(INTERFERENCE_RESULT_DIR, fname)

    def bw(p):
        with open(p) as f:
            data = json.load(f)
        return sum(job["write"]["bw"] for job in data["jobs"])

    if is_finish:
        finish[jobs] = bw(path)
    else:
        baseline[jobs] = bw(path)

jobs_sorted = sorted(baseline.keys())

x_vals_interference = []
y_vals_interference = []

for j in jobs_sorted:
    if j in finish:
        x_vals_interference.append(j)
        y_vals_interference.append(baseline[j] / finish[j])

x_smooth_interference, y_smooth_interference = smooth_curve(
    x_vals_interference, y_vals_interference
)

xmin_i, xmax_i = min(x_vals_interference), max(x_vals_interference)
xpad_i = 0.05 * (xmax_i - xmin_i)

ymin_i = 0
ymax_i = max(y_vals_interference) * 1.08

# ============================================================
# -------- PLOT --------
# ============================================================
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(8, 3))

# ---------------- DLWA (LEFT)
ax1.plot(x_smooth_dlwa, y_smooth_dlwa, color="black", linewidth=LINE_WIDTH, label="baseline")
ax1.plot([xmin_dlwa, xmax_dlwa], [1, 1], "--", color="blue", linewidth=LINE_WIDTH, label="ideal")

ax1.set_xlabel("(a) Occupancy (%)", fontsize=LABEL_FONT_SIZE)
ax1.set_ylabel("DLWA", fontsize=LABEL_FONT_SIZE)

ax1.set_xticks(PLOT_PERCENTAGES)
ax1.set_xticklabels([str(p) for p in PLOT_PERCENTAGES], rotation=0, ha="right")

ax1.set_yticks([1])
ax1.set_yticklabels(["1"])

ax1.set_xlim(xmin_dlwa - xpad_dlwa, xmax_dlwa + xpad_dlwa)
ax1.set_ylim(dlwa_ymin, dlwa_ymax)

style_axes(ax1)
ax1.legend(loc="upper right", fontsize=LEGEND_FONT_SIZE, frameon=False)

# ---------------- INTERFERENCE (RIGHT)
ax2.plot(x_smooth_interference, y_smooth_interference, color="black", linewidth=LINE_WIDTH, label="baseline")
ax2.plot([xmin_i, xmax_i], [1, 1], "--", color="blue", linewidth=LINE_WIDTH, label="ideal")

ax2.set_xlabel("(b) Finish Concurrency", fontsize=LABEL_FONT_SIZE)
ax2.set_ylabel("Interference", fontsize=LABEL_FONT_SIZE)

# ✅ FIX: show job numbers now
ax2.set_xticks(x_vals_interference)
ax2.set_xticklabels([str(x) for x in x_vals_interference])

ax2.set_yticks([1])
ax2.set_yticklabels(["1"])

ax2.set_xlim(xmin_i - xpad_i, xmax_i + xpad_i)
ax2.set_ylim(ymin_i, ymax_i)

style_axes(ax2)
ax2.legend(loc="lower left", fontsize=LEGEND_FONT_SIZE, frameon=False)

# ============================================================
# SAVE
# ============================================================
plt.tight_layout(w_pad=1.0)
plt.savefig(OUTPUT_PATH, bbox_inches="tight", pad_inches=0.01)
plt.close()

print("✅ Saved:", OUTPUT_PATH)