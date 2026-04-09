import os
import math
import matplotlib.pyplot as plt
from collections import defaultdict
from matplotlib import rcParams
from matplotlib.gridspec import GridSpec

# ============================================================
# Font and style settings
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

# Individual plot size
FIG_W = 3.3
FIG_H = 2.6

# Combined 6-panel size
COMBINED_FIG_W = 18.5
COMBINED_FIG_H = 4.5

# Whether to use log scale for DLWA plots
USE_LOG_SCALE_DLWA = True

# ============================================================
# Input / Output
# ============================================================
input_path = "../exp_occupancy/new_results/finish-log"

out_dir = "plots"
os.makedirs(out_dir, exist_ok=True)

# ============================================================
# Occupancy percentages in the log, in order
# ============================================================
PERCENTAGES = [0.01, 10, 20, 30, 40, 50, 60, 70, 80, 90, 99.99]
NUM_PERCENTAGES = len(PERCENTAGES)

# ============================================================
# Geometry order for the combined 6-panel figures
# Larger zone sizes first, then smaller
# ============================================================
PLOT_COMBOS = [
    (16, 268435456),  # P=16, S=256 MiB
    (16, 134217728),  # P=16, S=128 MiB
    (8,  134217728),  # P=8,  S=128 MiB
    (8,   67108864),  # P=8,  S=64 MiB
    (4,   67108864),  # P=4,  S=64 MiB
    (4,   33554432),  # P=4,  S=32 MiB
]

# ============================================================
# Helpers
# ============================================================
def bytes_to_mib(nbytes: int) -> int:
    return int(nbytes // (1024 * 1024))

def combo_title(min_luns: int, zsz_bytes: int) -> str:
    return f"P={min_luns}, S={bytes_to_mib(zsz_bytes)} MiB"

def combo_short_title(min_luns: int, zsz_bytes: int) -> str:
    return f"P={min_luns}, S={bytes_to_mib(zsz_bytes)}MiB"

def combo_tag(min_luns: int, zsz_bytes: int) -> str:
    return f"minl-{min_luns}_zsz-{bytes_to_mib(zsz_bytes)}MiB"

def output_path_pages(min_luns: int, zsz_bytes: int) -> str:
    return os.path.join(
        out_dir,
        f"exp_occupancy_pages_finished_raw_{combo_tag(min_luns, zsz_bytes)}.pdf"
    )

def output_path_dlwa(min_luns: int, zsz_bytes: int) -> str:
    return os.path.join(
        out_dir,
        f"exp_occupancy_dlwa_{combo_tag(min_luns, zsz_bytes)}.pdf"
    )

def combined_output_path_pages() -> str:
    return os.path.join(out_dir, "exp_occupancy_pages_finished_combined_6panel.pdf")

def combined_output_path_dlwa() -> str:
    return os.path.join(out_dir, "exp_occupancy_dlwa_combined_6panel.pdf")

def style_axes(ax):
    ax.grid(False)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_linewidth(SPINE_WIDTH)
    ax.spines["bottom"].set_linewidth(SPINE_WIDTH)
    ax.tick_params(axis="both", labelsize=TICK_FONT_SIZE, width=SPINE_WIDTH, length=3)

def config_label(mode: int, chnk: int):
    """
    Map mode/chunk to readable labels.

    mode 1 -> fixed
    mode 4 -> superblock
    mode 2, chnk 1 -> block
    mode 2, chnk 2 -> hchunk-2
    mode 5 -> vchunk-<chnk>
    """
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

def compute_host_pages(zone_slba: int, wptr: int) -> float:
    """
    Host-issued writes in pages:
      Wh = (wptr - zone_slba) / 8
    """
    return (wptr - zone_slba) / 8.0

def compute_dlwa(host_pages: float, device_pages: float) -> float:
    """
    DLWA = (Wh + Wd) / Wh
    """
    if host_pages <= 0:
        return float("nan")
    return (host_pages + device_pages) / host_pages

# ============================================================
# Marker styles
# ============================================================
CONFIG_STYLES = {
    "fixed": {
        "marker": "o",
        "linestyle": ":",
    },
    "superblock": {
        "marker": "^",
        "linestyle": ":",
    },
    "block": {
        "marker": "v",
        "linestyle": ":",
    },
    "hchunk-2": {
        "marker": "s",
        "linestyle": ":",
    },
    "vchunk-2": {
        "marker": "D",
        "linestyle": ":",
    },
    "vchunk-4": {
        "marker": "P",
        "linestyle": ":",
    },
}

CONFIG_ORDER = [
    "fixed",
    "superblock",
    "block",
    "hchunk-2",
    "vchunk-2",
    "vchunk-4",
]

# ============================================================
# Data structures
# ============================================================
pages_finished_all = defaultdict(lambda: defaultdict(list))
dlwa_all = defaultdict(lambda: defaultdict(list))
extra_info_all = defaultdict(lambda: defaultdict(list))

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
            chnk = int(entry.get("chnk", "1"))
            minl = int(entry["minl"])
            zsz = int(entry["zsz"])
            pf = int(entry["pages_finished"])
            zone_slba = int(entry.get("zone_slba", "-1"))
            wptr = int(entry.get("wptr", "-1"))
            nep = int(entry.get("num_extra_pages", "-1"))
            max_pages = int(entry.get("max_pages", "-1"))
        except (KeyError, ValueError):
            print("⚠️ Skipping line due to missing/invalid fields:", entry)
            continue

        label = config_label(mode, chnk)
        if label is None:
            continue

        combo = (minl, zsz)

        if len(pages_finished_all[combo][label]) >= NUM_PERCENTAGES:
            continue

        host_pages = compute_host_pages(zone_slba, wptr)
        dlwa = compute_dlwa(host_pages, pf)

        occ_idx = len(pages_finished_all[combo][label])
        occ = PERCENTAGES[occ_idx]

        pages_finished_all[combo][label].append(pf)
        dlwa_all[combo][label].append(dlwa)
        extra_info_all[combo][label].append({
            "occ": occ,
            "mode": mode,
            "chnk": chnk,
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
            f"✅ {combo_title(minl, zsz)} / {label}: "
            f"{len(pages_finished_all[combo][label])}/{NUM_PERCENTAGES} "
            f"(occupancy={occ}%) "
            f"host_pages={host_pages:.2f}, device_pages={pf}, dlwa={dlwa:.6f}"
        )

# ============================================================
# Step 2: Validate and print ALL values used for plotting
# ============================================================
print("\n==================== FULL DATA USED FOR PLOTTING ====================\n")

for combo in sorted(pages_finished_all.keys()):
    minl, zsz = combo

    print("\n============================================================")
    print(f"CONFIGURATION: {combo_title(minl, zsz)}")
    print("============================================================\n")

    for label in CONFIG_ORDER:
        if label not in pages_finished_all[combo]:
            continue

        pf_values = pages_finished_all[combo][label]
        dlwa_values = dlwa_all[combo][label]
        extra = extra_info_all[combo][label]

        if len(pf_values) != NUM_PERCENTAGES:
            raise RuntimeError(
                f"Incomplete pages_finished data for {combo_title(minl, zsz)} / {label}. "
                f"Expected {NUM_PERCENTAGES} entries, got {len(pf_values)}."
            )

        if len(dlwa_values) != NUM_PERCENTAGES:
            raise RuntimeError(
                f"Incomplete DLWA data for {combo_title(minl, zsz)} / {label}. "
                f"Expected {NUM_PERCENTAGES} entries, got {len(dlwa_values)}."
            )

        print(f"--- {label} ---\n")

        for i in range(NUM_PERCENTAGES):
            info = extra[i]

            occ = info["occ"]
            zone_slba = info["zone_slba"]
            wptr = info["wptr"]
            host_pages = info["host_pages"]
            device_pages = info["device_pages"]
            pages_finished = info["pages_finished"]
            extra_pages = info["num_extra_pages"]
            max_pages = info["max_pages"]
            dlwa = info["dlwa"]

            print(
                f"Occupancy: {occ:>6}% | "
                f"SLBA: {zone_slba:<10} | "
                f"WPTR: {wptr:<10} | "
                f"HostPages (Wh): {host_pages:>10.2f} | "
                f"DevicePages (Wd): {device_pages:>8} | "
                f"PagesFinished: {pages_finished:>8} | "
                f"ExtraPages: {extra_pages:>6} | "
                f"MaxPages: {max_pages:>6} | "
                f"DLWA: {dlwa:.6f}"
            )

        print()

# ============================================================
# Step 3: Print final arrays exactly as plotted
# ============================================================
print("\n==================== FINAL ARRAYS PASSED TO PLOTS ====================\n")

for combo in sorted(pages_finished_all.keys()):
    minl, zsz = combo

    print(f"\n>>> {combo_title(minl, zsz)}\n")

    for label in CONFIG_ORDER:
        if label not in pages_finished_all[combo]:
            continue

        pf_values = pages_finished_all[combo][label]
        dlwa_values = dlwa_all[combo][label]

        print(f"{label}:")
        print(f"  X (Occupancy): {PERCENTAGES}")
        print(f"  Y (PagesFinished): {pf_values}")
        print(f"  Y (DLWA): {[f'{x:.6f}' for x in dlwa_values]}")
        print()

# ============================================================
# Step 4: Compute shared y-axis limits
# ============================================================
all_pf_values = []
all_dlwa_values = []

for combo in pages_finished_all:
    for label in pages_finished_all[combo]:
        all_pf_values.extend(pages_finished_all[combo][label])

for combo in dlwa_all:
    for label in dlwa_all[combo]:
        for v in dlwa_all[combo][label]:
            if not math.isnan(v) and not math.isinf(v):
                all_dlwa_values.append(v)

if not all_pf_values:
    raise RuntimeError("No valid pages_finished data found in the input log.")

if not all_dlwa_values:
    raise RuntimeError("No valid DLWA data found in the input log.")

global_pf_ymax = max(all_pf_values) * 1.08

if USE_LOG_SCALE_DLWA:
    valid_dlwa = [v for v in all_dlwa_values if v > 0]
    if not valid_dlwa:
        raise RuntimeError("No positive DLWA values available for log-scale plotting.")

    dlwa_ymin = min(valid_dlwa) / 1.10
    dlwa_ymax = max(valid_dlwa) * 1.10
else:
    global_dlwa_ymax = max(all_dlwa_values)
    global_dlwa_ymin = min(all_dlwa_values)
    dlwa_ymin = min(1.0, global_dlwa_ymin)
    dlwa_ymax = global_dlwa_ymax * 1.08

xmin = min(PERCENTAGES)
xmax = max(PERCENTAGES)
xpad = 0.04 * (xmax - xmin)

# ============================================================
# Step 5: Individual figures
# ============================================================
saved_paths = []

for combo in sorted(pages_finished_all.keys()):
    minl, zsz = combo

    fig, ax = plt.subplots(figsize=(FIG_W, FIG_H))

    for label in CONFIG_ORDER:
        if label not in pages_finished_all[combo]:
            continue

        x_vals = PERCENTAGES
        y_vals = pages_finished_all[combo][label]
        style = CONFIG_STYLES.get(label, {"marker": "o", "linestyle": ":"})

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
            markeredgewidth=MARKER_EDGE_WIDTH,
            label=label,
        )

    ax.set_xlabel("Occupancy (%)", fontsize=LABEL_FONT_SIZE)
    ax.set_ylabel("Unnecessary Page Writes", fontsize=LABEL_FONT_SIZE)
    ax.set_title(combo_title(minl, zsz), fontsize=TITLE_FONT_SIZE, pad=4)

    ax.set_xlim(xmin - xpad, xmax + xpad)
    ax.set_ylim(0, global_pf_ymax)

    ax.set_xticks(PERCENTAGES)
    ax.set_xticklabels([str(p) for p in PERCENTAGES], rotation=45, ha="right")

    style_axes(ax)

    ax.legend(
        loc="upper right",
        fontsize=LEGEND_FONT_SIZE,
        frameon=False,
        ncol=1,
        handlelength=1.4,
        borderpad=0.2,
        labelspacing=0.2,
    )

    plt.tight_layout(pad=0.3)

    out_path = output_path_pages(minl, zsz)
    plt.savefig(out_path, bbox_inches="tight", pad_inches=0.01)
    plt.close(fig)

    saved_paths.append(out_path)
    print(f"✅ Saved pages_finished plot: {out_path}")

for combo in sorted(dlwa_all.keys()):
    minl, zsz = combo

    fig, ax = plt.subplots(figsize=(FIG_W, FIG_H))

    for label in CONFIG_ORDER:
        if label not in dlwa_all[combo]:
            continue

        x_vals = PERCENTAGES
        y_vals = dlwa_all[combo][label]
        style = CONFIG_STYLES.get(label, {"marker": "o", "linestyle": ":"})

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
            markeredgewidth=MARKER_EDGE_WIDTH,
            label=label,
        )

    ax.set_xlabel("Occupancy (%)", fontsize=LABEL_FONT_SIZE)
    ax.set_ylabel("DLWA (log scale)" if USE_LOG_SCALE_DLWA else "DLWA", fontsize=LABEL_FONT_SIZE)
    ax.set_title(combo_title(minl, zsz), fontsize=TITLE_FONT_SIZE, pad=4)

    ax.set_xlim(xmin - xpad, xmax + xpad)
    ax.set_ylim(dlwa_ymin, dlwa_ymax)

    if USE_LOG_SCALE_DLWA:
        ax.set_yscale("log")

    ax.set_xticks(PERCENTAGES)
    ax.set_xticklabels([str(p) for p in PERCENTAGES], rotation=45, ha="right")

    style_axes(ax)

    ax.legend(
        loc="upper right",
        fontsize=LEGEND_FONT_SIZE,
        frameon=False,
        ncol=1,
        handlelength=1.4,
        borderpad=0.2,
        labelspacing=0.2,
    )

    plt.tight_layout(pad=0.3)

    out_path = output_path_dlwa(minl, zsz)
    plt.savefig(out_path, bbox_inches="tight", pad_inches=0.01)
    plt.close(fig)

    saved_paths.append(out_path)
    print(f"✅ Saved DLWA plot: {out_path}")

# ============================================================
# Step 6: Combined plotting helper
# ============================================================
def plot_combined_line_figure(metric_name, data_all, combos, output_file, y_label, ymin, ymax):
    fig = plt.figure(figsize=(COMBINED_FIG_W, COMBINED_FIG_H), constrained_layout=False)
    fig.patch.set_facecolor("white")

    gs = GridSpec(
        1, len(combos),
        figure=fig,
        width_ratios=[1] * len(combos),
        wspace=0.08
    )

    axes = []

    for col, combo in enumerate(combos):
        minl, zsz = combo

        ax = fig.add_subplot(gs[0, col], sharey=axes[0] if axes else None)
        axes.append(ax)

        if combo not in data_all:
            ax.set_visible(False)
            continue

        for label in CONFIG_ORDER:
            if label not in data_all[combo]:
                continue

            x_vals = PERCENTAGES
            y_vals = data_all[combo][label]
            style = CONFIG_STYLES.get(label, {"marker": "o", "linestyle": ":"})

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
                markeredgewidth=MARKER_EDGE_WIDTH,
                label=label,
            )

        ax.set_title(combo_short_title(minl, zsz), fontsize=TITLE_FONT_SIZE, pad=3)
        ax.set_xlim(xmin - xpad, xmax + xpad)
        ax.set_ylim(ymin, ymax)

        if metric_name == "DLWA" and USE_LOG_SCALE_DLWA:
            ax.set_yscale("log")

        ax.set_xticks(PERCENTAGES)
        ax.set_xticklabels([str(p) for p in PERCENTAGES], rotation=45, ha="right", fontsize=TICK_FONT_SIZE)

        style_axes(ax)

        if col == 0:
            ax.set_ylabel(y_label, fontsize=LABEL_FONT_SIZE)
            ax.tick_params(axis="y", which="both", labelleft=True, left=True, pad=3)
        else:
            ax.tick_params(axis="y", which="both", labelleft=False, left=True)

    fig.text(0.5, 0.08, "Occupancy (%)", ha="center", va="center", fontsize=LABEL_FONT_SIZE)

    handles = []
    labels = []
    if axes:
        handles, labels = axes[0].get_legend_handles_labels()

    if handles:
        fig.legend(
            handles,
            labels,
            loc="upper center",
            bbox_to_anchor=(0.5, 0.95),
            ncol=len(labels),
            frameon=False,
            fontsize=LEGEND_FONT_SIZE,
            handlelength=1.6,
            columnspacing=1.0,
        )

    fig.subplots_adjust(left=0.06, right=0.995, top=0.78, bottom=0.26)

    plt.savefig(output_file, facecolor="white", bbox_inches="tight", pad_inches=0.01)
    print(f"✅ Saved combined {metric_name} figure: {output_file}")
    plt.close(fig)

# ============================================================
# Step 7: Combined 6-panel pages-finished figure
# ============================================================
plot_combined_line_figure(
    metric_name="pages_finished",
    data_all=pages_finished_all,
    combos=PLOT_COMBOS,
    output_file=combined_output_path_pages(),
    y_label="Extra Device-side Writes",
    ymin=0,
    ymax=global_pf_ymax,
)

saved_paths.append(combined_output_path_pages())

# ============================================================
# Step 8: Combined 6-panel DLWA figure
# ============================================================
plot_combined_line_figure(
    metric_name="DLWA",
    data_all=dlwa_all,
    combos=PLOT_COMBOS,
    output_file=combined_output_path_dlwa(),
    y_label="DLWA (log scale)" if USE_LOG_SCALE_DLWA else "DLWA",
    ymin=dlwa_ymin,
    ymax=dlwa_ymax,
)

saved_paths.append(combined_output_path_dlwa())

# ============================================================
# Final summary
# ============================================================
print("\n==================== SAVED PLOTS ====================\n")
for p in saved_paths:
    print(f"  - {p}")