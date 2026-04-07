import os
import math
import matplotlib.pyplot as plt
from collections import defaultdict
from matplotlib import rcParams

# ============================================================
# Style settings
# ============================================================
rcParams["font.family"] = "Linux Libertine O"
rcParams["pdf.fonttype"] = 42
rcParams["ps.fonttype"] = 42

LABEL_FONT_SIZE = 18
TICK_FONT_SIZE = 18
LINE_WIDTH = 1.8
MARKER_SIZE = 10
MARKER_EDGE_WIDTH = 1.4
SPINE_WIDTH = 1.2
LEGEND_FONT_SIZE = 12
TITLE_FONT_SIZE = 15

BAR_EDGE_WIDTH = 0.8

# ============================================================
# Input / Output
# ============================================================
input_path = "../exp_occupancy/new_results/finish-log"
out_dir = "results_zn540"
os.makedirs(out_dir, exist_ok=True)

pages_output = os.path.join(out_dir, "pages_finished_two_configs_10_to_90.pdf")
dlwa_output = os.path.join(out_dir, "dlwa_two_configs_10_to_90.pdf")

# ============================================================
# Occupancy percentages in the log, in order
# Full list in the log
# We will only plot 10% to 90%
# ============================================================
PERCENTAGES = [0.01, 10, 20, 30, 40, 50, 60, 70, 80, 90, 99.99]
NUM_PERCENTAGES = len(PERCENTAGES)

START_IDX = 1   # 10%
END_IDX = 10    # up to 90%, python slice excludes index 10

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

def config_label(mode: int):
    if mode == 1:
        return "Baseline"
    if mode == 4:
        return "SilentZNS"
    return None

def compute_host_pages(zone_slba: int, wptr: int) -> float:
    return (wptr - zone_slba) / 32.0

def compute_dlwa(host_pages: float, device_pages: float) -> float:
    if host_pages <= 0:
        return float("nan")
    return (host_pages + device_pages) / host_pages

# ============================================================
# Plot styles for the two configs
# ============================================================
CONFIG_STYLES = {
    "Baseline": {
        "marker": "o",
        "linestyle": ":",
    },
    "SilentZNS": {
        "marker": "s",
        "linestyle": "-",
    },
}

CONFIG_ORDER = ["Baseline", "SilentZNS"]

# ============================================================
# Data structures
# We aggregate across all lines for each mode only.
# ============================================================
pages_finished_all = defaultdict(list)
dlwa_all = defaultdict(list)
extra_info_all = defaultdict(list)

# ============================================================
# Step 1: Parse log
# ============================================================
print("\n==================== PARSING FINISH LOG ====================\n")

with open(input_path, "r") as f:
    for line in f:
        line = line.strip()
        if not line or not line.startswith("mode"):
            continue

        parts = line.split(",")
        if len(parts) % 2 != 0:
            print("⚠️ Malformed line skipped:", line)
            continue

        entry = {parts[i]: parts[i + 1] for i in range(0, len(parts), 2)}

        try:
            mode = int(entry["mode"])
            pf = int(entry["pages_finished"])
            zone_slba = int(entry.get("zone_slba", "-1"))
            wptr = int(entry.get("wptr", "-1"))
            nep = int(entry.get("num_extra_pages", "-1"))
            max_pages = int(entry.get("max_pages", "-1"))
        except (KeyError, ValueError):
            print("⚠️ Skipping line due to missing/invalid fields:", entry)
            continue

        label = config_label(mode)
        if label is None:
            continue

        # Keep only the first NUM_PERCENTAGES entries for each config
        if len(pages_finished_all[label]) >= NUM_PERCENTAGES:
            continue

        host_pages = compute_host_pages(zone_slba, wptr)
        dlwa = compute_dlwa(host_pages, pf)

        occ_idx = len(pages_finished_all[label])
        occ = PERCENTAGES[occ_idx]

        pages_finished_all[label].append(pf)
        dlwa_all[label].append(dlwa)
        extra_info_all[label].append({
            "occ": occ,
            "mode": mode,
            "zone_slba": zone_slba,
            "wptr": wptr,
            "num_extra_pages": nep,
            "pages_finished": pf,
            "max_pages": max_pages,
            "host_pages": host_pages,
            "device_pages": pf,
            "dlwa": dlwa,
        })

        print(
            f"✅ {label}: "
            f"{len(pages_finished_all[label])}/{NUM_PERCENTAGES} "
            f"(occupancy={occ}%) "
            f"host_pages={host_pages:.2f}, device_pages={pf}, dlwa={dlwa:.6f}"
        )

# ============================================================
# Step 2: Validate and print all values
# ============================================================
print("\n==================== FULL DATA USED FOR PLOTTING ====================\n")

for label in CONFIG_ORDER:
    if label not in pages_finished_all:
        continue

    pf_values = pages_finished_all[label]
    dlwa_values = dlwa_all[label]
    extra = extra_info_all[label]

    if len(pf_values) != NUM_PERCENTAGES:
        raise RuntimeError(
            f"Incomplete pages-finished data for {label}. "
            f"Expected {NUM_PERCENTAGES} entries, got {len(pf_values)}."
        )

    if len(dlwa_values) != NUM_PERCENTAGES:
        raise RuntimeError(
            f"Incomplete DLWA data for {label}. "
            f"Expected {NUM_PERCENTAGES} entries, got {len(dlwa_values)}."
        )

    print(f"--- {label} ---\n")
    for info in extra:
        print(
            f"Occupancy: {info['occ']:>6}% | "
            f"SLBA: {info['zone_slba']:<10} | "
            f"WPTR: {info['wptr']:<10} | "
            f"HostPages (Wh): {info['host_pages']:>10.2f} | "
            f"DevicePages (Wd): {info['device_pages']:>8} | "
            f"PagesFinished: {info['pages_finished']:>8} | "
            f"ExtraPages: {info['num_extra_pages']:>6} | "
            f"MaxPages: {info['max_pages']:>6} | "
            f"DLWA: {info['dlwa']:.6f}"
        )
    print()

# ============================================================
# Step 3: Print exact arrays used for plotting (10% to 90%)
# ============================================================
print("\n==================== FINAL ARRAYS PASSED TO PLOTS ====================\n")

for label in CONFIG_ORDER:
    if label not in pages_finished_all:
        continue

    pf_plot = pages_finished_all[label][START_IDX:END_IDX]
    dlwa_plot = dlwa_all[label][START_IDX:END_IDX]

    print(f"{label}:")
    print(f"  X (Occupancy): {PLOT_PERCENTAGES}")
    print(f"  Y (PagesFinished): {pf_plot}")
    print(f"  Y (DLWA): {[f'{x:.6f}' for x in dlwa_plot]}")
    print()

# ============================================================
# Step 4: Shared axis limits using only plotted range (10% to 90%)
# ============================================================
all_pf_values = []
all_dlwa_values = []

for label in pages_finished_all:
    all_pf_values.extend(pages_finished_all[label][START_IDX:END_IDX])

for label in dlwa_all:
    for v in dlwa_all[label][START_IDX:END_IDX]:
        if not math.isnan(v) and not math.isinf(v):
            all_dlwa_values.append(v)

if not all_pf_values:
    raise RuntimeError("No valid pages-finished data found in the plotted range.")

if not all_dlwa_values:
    raise RuntimeError("No valid DLWA data found in the plotted range.")

global_pf_ymax = max(all_pf_values) * 1.08
global_dlwa_ymax = max(all_dlwa_values) * 1.08
global_dlwa_ymax = max(all_dlwa_values) * 1.08

dlwa_ymin = 0
dlwa_ymax = global_dlwa_ymax

xmin = PLOT_PERCENTAGES[0]
xmax = PLOT_PERCENTAGES[-1]
xpad = 0.04 * (xmax - xmin)

# ============================================================
# Step 5: Plot raw pages-finished (10% to 90%)
# ============================================================
plt.figure(figsize=(4, 3))
ax = plt.gca()

for label in CONFIG_ORDER:
    if label not in pages_finished_all:
        continue

    x_vals = PLOT_PERCENTAGES
    y_vals = pages_finished_all[label][START_IDX:END_IDX]
    style = CONFIG_STYLES[label]

    ax.plot(
        x_vals,
        y_vals,
        linestyle=style["linestyle"],
        linewidth=LINE_WIDTH,
        marker=style["marker"],
        markersize=MARKER_SIZE,
        color="black",
        markerfacecolor="none",
        markeredgecolor="black",
        markeredgewidth=BAR_EDGE_WIDTH,
        label=label,
    )

ax.set_xlabel("(a) Occupancy (%)", fontsize=LABEL_FONT_SIZE)
ax.set_ylabel("Extra Device-side Writes", fontsize=LABEL_FONT_SIZE)
ax.set_title("Pages Finished", fontsize=TITLE_FONT_SIZE, pad=4)

ax.set_xlim(xmin - xpad, xmax + xpad)
ax.set_ylim(0, global_pf_ymax)

ax.set_xticks(PLOT_PERCENTAGES)
ax.set_xticklabels([str(p) for p in PLOT_PERCENTAGES], rotation=0, ha="right")

style_axes(ax)

ax.legend(
    loc="upper right",
    fontsize=LEGEND_FONT_SIZE,
    frameon=False,
)

plt.tight_layout()
plt.savefig(pages_output, bbox_inches="tight", pad_inches=0.01)
plt.close()
print(f"✅ Saved pages-finished plot: {pages_output}")

# ============================================================
# Step 6: Plot DLWA (linear scale, 10% to 90%)
# ============================================================
plt.figure(figsize=(4, 3))
ax = plt.gca()

for label in CONFIG_ORDER:
    if label not in dlwa_all:
        continue

    x_vals = PLOT_PERCENTAGES
    y_vals = dlwa_all[label][START_IDX:END_IDX]
    style = CONFIG_STYLES[label]

    ax.plot(
        x_vals,
        y_vals,
        linestyle=style["linestyle"],
        linewidth=LINE_WIDTH,
        marker=style["marker"],
        markersize=MARKER_SIZE,
        color="black",
        markerfacecolor="none",
        markeredgecolor="black",
        markeredgewidth=BAR_EDGE_WIDTH,
        label=label,
    )

ax.set_xlabel("(a) Occupancy (%)", fontsize=LABEL_FONT_SIZE)
ax.set_ylabel("DLWA", fontsize=LABEL_FONT_SIZE)
ax.set_title("", fontsize=TITLE_FONT_SIZE, pad=4)

ax.set_xlim(xmin - xpad, xmax + xpad)
ax.set_ylim(dlwa_ymin, dlwa_ymax)

ax.set_xticks(PLOT_PERCENTAGES)
ax.set_xticklabels([str(p) for p in PLOT_PERCENTAGES], rotation=0, ha="right")

style_axes(ax)

ax.legend(
    loc="upper right",
    fontsize=LEGEND_FONT_SIZE,
    frameon=False,
)

plt.tight_layout()
plt.savefig(dlwa_output, bbox_inches="tight", pad_inches=0.01)
plt.close()
print(f"✅ Saved DLWA plot: {dlwa_output}")

# ============================================================
# Final summary
# ============================================================
print("\n==================== SAVED PLOTS ====================\n")
print(f"  - {pages_output}")
print(f"  - {dlwa_output}")

# ============================================================
# Step 7: Compute percentage decrease (Baseline → SilentZNS)
# ============================================================
print("\n==================== PERCENTAGE DECREASE ====================\n")

if "Baseline" in pages_finished_all and "SilentZNS" in pages_finished_all:

    conf_pf = pages_finished_all["Baseline"][START_IDX:END_IDX]
    silent_pf = pages_finished_all["SilentZNS"][START_IDX:END_IDX]

    conf_dlwa = dlwa_all["Baseline"][START_IDX:END_IDX]
    silent_dlwa = dlwa_all["SilentZNS"][START_IDX:END_IDX]

    print("Per-occupancy percentage decrease:\n")

    for i, occ in enumerate(PLOT_PERCENTAGES):
        # Pages Finished
        if conf_pf[i] > 0:
            pf_decrease = ((conf_pf[i] - silent_pf[i]) / conf_pf[i]) * 100
        else:
            pf_decrease = float("nan")

        # DLWA
        if conf_dlwa[i] > 0:
            dlwa_decrease = ((conf_dlwa[i] - silent_dlwa[i]) / conf_dlwa[i]) * 100
        else:
            dlwa_decrease = float("nan")

        print(
            f"Occupancy {occ:>6}% | "
            f"PagesFinished ↓: {pf_decrease:6.2f}% | "
            f"DLWA ↓: {dlwa_decrease:6.2f}%"
        )

    # ========================================================
    # Averages (nice for paper)
    # ========================================================
    valid_pf = [
        ((c - s) / c) * 100
        for c, s in zip(conf_pf, silent_pf)
        if c > 0
    ]

    valid_dlwa = [
        ((c - s) / c) * 100
        for c, s in zip(conf_dlwa, silent_dlwa)
        if c > 0
    ]

    if valid_pf:
        avg_pf = sum(valid_pf) / len(valid_pf)
        print(f"\nAverage PagesFinished decrease: {avg_pf:.2f}%")

    if valid_dlwa:
        avg_dlwa = sum(valid_dlwa) / len(valid_dlwa)
        print(f"Average DLWA decrease: {avg_dlwa:.2f}%")

else:
    print("⚠️ Missing one of the configs (Baseline or SilentZNS)")



# import os
# import math
# import numpy as np
# import matplotlib.pyplot as plt
# from collections import defaultdict
# from matplotlib import rcParams

# # Try to use a smooth monotonic interpolator
# try:
#     from scipy.interpolate import PchipInterpolator
#     HAS_PCHIP = True
# except ImportError:
#     HAS_PCHIP = False

# # ============================================================
# # Style settings
# # ============================================================
# rcParams["font.family"] = "Linux Libertine O"
# rcParams["pdf.fonttype"] = 42
# rcParams["ps.fonttype"] = 42

# LABEL_FONT_SIZE = 18
# TICK_FONT_SIZE = 18
# LINE_WIDTH = 1.8
# SPINE_WIDTH = 1.2
# LEGEND_FONT_SIZE = 12

# # ============================================================
# # Input / Output
# # ============================================================
# input_path = "../exp_occupancy/new_results/finish-log"
# out_dir = "results_zn540"
# os.makedirs(out_dir, exist_ok=True)

# dlwa_output = os.path.join(out_dir, "dlwa_Baseline_vs_ideal_smoothed.pdf")

# # ============================================================
# # Occupancy percentages
# # ============================================================
# PERCENTAGES = [0.01, 10, 20, 30, 40, 50, 60, 70, 80, 90, 99.99]
# START_IDX = 1
# END_IDX = 10
# PLOT_PERCENTAGES = PERCENTAGES[START_IDX:END_IDX]

# # ============================================================
# # Helpers
# # ============================================================
# def style_axes(ax):
#     ax.grid(False)
#     ax.spines["top"].set_visible(False)
#     ax.spines["right"].set_visible(False)
#     ax.spines["left"].set_linewidth(SPINE_WIDTH)
#     ax.spines["bottom"].set_linewidth(SPINE_WIDTH)
#     ax.tick_params(axis="both", labelsize=TICK_FONT_SIZE, width=SPINE_WIDTH, length=3)

# def compute_host_pages(zone_slba, wptr):
#     return (wptr - zone_slba) / 32.0

# def compute_dlwa(host_pages, device_pages):
#     if host_pages <= 0:
#         return float("nan")
#     return (host_pages + device_pages) / host_pages

# def smooth_curve(x, y, num_points=300):
#     """
#     Return smoothed x/y arrays.
#     Uses PCHIP if available; otherwise falls back to dense linear interpolation.
#     """
#     x = np.array(x, dtype=float)
#     y = np.array(y, dtype=float)

#     x_dense = np.linspace(x.min(), x.max(), num_points)

#     if HAS_PCHIP and len(x) >= 2:
#         interpolator = PchipInterpolator(x, y)
#         y_dense = interpolator(x_dense)
#     else:
#         y_dense = np.interp(x_dense, x, y)

#     return x_dense, y_dense

# # ============================================================
# # Parse log
# # ============================================================
# dlwa_all = defaultdict(list)

# with open(input_path, "r") as f:
#     for line in f:
#         if not line.startswith("mode"):
#             continue

#         parts = line.strip().split(",")
#         if len(parts) % 2 != 0:
#             continue

#         entry = {parts[i]: parts[i + 1] for i in range(0, len(parts), 2)}

#         try:
#             mode = int(entry["mode"])
#             if mode != 1:   # Baseline only
#                 continue

#             pf = int(entry["pages_finished"])
#             zone_slba = int(entry["zone_slba"])
#             wptr = int(entry["wptr"])
#         except (KeyError, ValueError):
#             continue

#         host_pages = compute_host_pages(zone_slba, wptr)
#         dlwa = compute_dlwa(host_pages, pf)

#         if len(dlwa_all["Baseline"]) < len(PERCENTAGES):
#             dlwa_all["Baseline"].append(dlwa)

# # ============================================================
# # Extract plotting values
# # ============================================================
# if "Baseline" not in dlwa_all:
#     raise RuntimeError("No Baseline data found in finish log.")

# Baseline_dlwa = dlwa_all["Baseline"][START_IDX:END_IDX]

# if len(Baseline_dlwa) != len(PLOT_PERCENTAGES):
#     raise RuntimeError(
#         f"Expected {len(PLOT_PERCENTAGES)} Baseline points, got {len(Baseline_dlwa)}."
#     )

# # ============================================================
# # Axis limits
# # ============================================================
# valid_vals = [v for v in Baseline_dlwa if not math.isnan(v) and not math.isinf(v)]
# if not valid_vals:
#     raise RuntimeError("No valid DLWA values found.")

# dlwa_ymin = 0
# dlwa_ymax = max(max(valid_vals), 1.0) * 1.08

# xmin = PLOT_PERCENTAGES[0]
# xmax = PLOT_PERCENTAGES[-1]
# xpad = 0.04 * (xmax - xmin)

# # ============================================================
# # Build smooth trend line
# # ============================================================
# x_smooth, y_smooth = smooth_curve(PLOT_PERCENTAGES, Baseline_dlwa, num_points=300)

# # ============================================================
# # Plot
# # ============================================================
# plt.figure(figsize=(4, 3))
# ax = plt.gca()

# # Baseline smoothed curve
# ax.plot(
#     x_smooth,
#     y_smooth,
#     linestyle="-",
#     linewidth=LINE_WIDTH,
#     color="black",
#     label="Baseline",
# )

# # Ideal line at y = 1
# ax.plot(
#     [xmin, xmax],
#     [1.0, 1.0],
#     linestyle="--",
#     linewidth=LINE_WIDTH,
#     color="blue",
#     label="ideal",
# )

# # Axis titles
# ax.set_xlabel("Occupancy (%)", fontsize=LABEL_FONT_SIZE)
# ax.set_ylabel("DLWA", fontsize=LABEL_FONT_SIZE)

# # X-axis ticks and labels kept
# ax.set_xticks(PLOT_PERCENTAGES)
# ax.set_xticklabels([str(p) for p in PLOT_PERCENTAGES], rotation=0, ha="right")

# # Remove Y-axis ticks and numbers, keep title/spine
# ax.set_yticks([1])
# ax.set_yticklabels(["1"])

# ax.set_xlim(xmin - xpad, xmax + xpad)
# ax.set_ylim(dlwa_ymin, dlwa_ymax)

# style_axes(ax)

# ax.legend(
#     loc="upper right",
#     fontsize=LEGEND_FONT_SIZE,
#     frameon=False,
# )

# plt.tight_layout()
# plt.savefig(dlwa_output, bbox_inches="tight", pad_inches=0.01)
# plt.close()

# print(f"✅ Saved plot: {dlwa_output}")