import os
import json
import re
import math
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import rcParams, colors
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.gridspec import GridSpec

# =========================
# Font and style settings
# =========================
rcParams["font.family"] = "Linux Libertine O"

LABEL_FONT_SIZE = 18
TICK_FONT_SIZE = 18
LINE_WIDTH = 1.5
MARKER_SIZE = 16
SPINE_WIDTH = 1.2
LEGEND_FONT_SIZE = 12
TITLE_FONT_SIZE = 15
ANNOT_FONT_SIZE = 20

# =========================
# Threads and request sizes
# =========================
THREAD_POINTS = [1, 2, 4, 8, 16, 32]
REQUEST_SIZES = ["4K", "8K", "16K", "32K", "64K", "128K"]

# =========================
# Paths
# =========================
RESULTS_DIR = "../exp_rw_bench/new_results"
OUTPUT_DIR = "plots"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# =========================
# Zone sizes (bytes)
# =========================
ZSIZE_32 = 33554432
ZSIZE_64 = 67108864
ZSIZE_128 = 134217728
ZSIZE_256 = 268435456

# =========================
# Geometries to plot
# Larger zone sizes first, then smaller
# =========================
PLOT_COMBOS = [
    (16, ZSIZE_256),
    (16, ZSIZE_128),
    (8, ZSIZE_128),
    (8, ZSIZE_64),
    (4, ZSIZE_64),
    (4, ZSIZE_32),
]

# =========================
# Colormap
# =========================
BLUE_WHITE_CMAP = LinearSegmentedColormap.from_list(
    "blue_white",
    ["#ffffff", "#deebf7", "#9ecae1", "#3182bd"]
)

# =========================
# Filename pattern
# =========================
pattern = re.compile(
    r"^(?P<expname>"
    r"vt-(?P<vt>\d+)[_-]chnk-(?P<chnk>\d+)[_-]maxc-(?P<maxc>\d+)[_-]minl-(?P<minl>\d+)[_-]"
    r"zsz-(?P<zsz>\d+)[_-]chnl-(?P<chnl>\d+)[_-]w-(?P<w>\d+)"
    r"(?:[_-]ssd-(?P<ssd>\d+))?"
    r")[_-]threads[_-](?P<threads>\d+)[_-]bs[_-](?P<bs>[A-Za-z0-9]+)\.json$"
)

# =========================
# Helpers
# =========================
def bytes_to_mib(nbytes: int) -> int:
    return int(nbytes // (1024 * 1024))

def combo_title(min_luns: int, zsz_bytes: int) -> str:
    return f"zone_parallelism {min_luns}, size {bytes_to_mib(zsz_bytes)} MiB"

def combo_short_title(min_luns: int, zsz_bytes: int) -> str:
    return f"P={min_luns}, S={bytes_to_mib(zsz_bytes)}MiB"

def combo_tag(min_luns: int, zsz_bytes: int) -> str:
    return f"minl-{min_luns}_zsz-{bytes_to_mib(zsz_bytes)}MiB"

def heatmap_output_path(metric_name: str, min_luns: int, zsz_bytes: int, config_tag: str) -> str:
    return os.path.join(
        OUTPUT_DIR,
        f"exp_rw-{metric_name}-{combo_tag(min_luns, zsz_bytes)}-{config_tag}-heatmap.pdf"
    )

def combined_output_path(config_tag: str) -> str:
    return os.path.join(
        OUTPUT_DIR,
        f"exp_rw-combined-{config_tag}-heatmaps.pdf"
    )

def config_label(vt: int, chnk: int, minl: int):
    if vt == 1 and chnk == 1:
        return "fixed"
    if vt == 4 and chnk == 1:
        return "stripe"
    if chnk == 1:
        if minl == 16 and vt == 2:
            return "block"
        if minl in (8, 4) and vt in (2, 3):
            return "block"
    if vt == 5 and chnk == 2:
        return "vchunk-2"
    if vt == 5 and chnk == 4:
        return "vchunk-4"
    if vt == 5 and chnk == 8:
        return "vchunk-8"
    return None

def style_axes(ax):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_linewidth(SPINE_WIDTH)
    ax.spines["bottom"].set_linewidth(SPINE_WIDTH)
    ax.grid(False)
    ax.tick_params(axis="both", labelsize=TICK_FONT_SIZE, width=SPINE_WIDTH)

def annotate_heatmap(ax, matrix, fmt="{:.0f}", fontsize=ANNOT_FONT_SIZE):
    valid = matrix[~np.isnan(matrix)]
    if valid.size == 0:
        return

    vmin = np.nanmin(valid)
    vmax = np.nanmax(valid)
    midpoint = (vmin + vmax) / 2.0

    for i in range(matrix.shape[0]):
        for j in range(matrix.shape[1]):
            value = matrix[i, j]
            if not np.isnan(value):
                color = "white" if value > midpoint else "black"
                ax.text(
                    j,
                    i,
                    fmt.format(value),
                    ha="center",
                    va="center",
                    fontsize=fontsize,
                    color=color
                )

def build_matrix(metric_dict):
    matrix = np.full((len(REQUEST_SIZES), len(THREAD_POINTS)), np.nan)
    for i, bs in enumerate(REQUEST_SIZES):
        for j, th in enumerate(THREAD_POINTS):
            if (bs, th) in metric_dict:
                matrix[i, j] = metric_dict[(bs, th)]
    return matrix

def make_norm(valid_values, use_log_scale):
    if valid_values.size == 0:
        return None, None, None

    if use_log_scale:
        positive_valid = valid_values[valid_values > 0]
        if positive_valid.size == 0:
            return None, None, None
        norm = colors.LogNorm(
            vmin=np.nanmin(positive_valid),
            vmax=np.nanmax(positive_valid)
        )
        return norm, None, None

    vmin = np.nanmin(valid_values)
    vmax = np.nanmax(valid_values)
    return None, vmin, vmax

def plot_heatmap(matrix, title, cbar_label, output_file, use_log_scale=False, annot_fmt="{:.0f}"):
    fig, ax = plt.subplots(figsize=(8.8, 6.2))

    valid = matrix[~np.isnan(matrix)]
    if valid.size == 0:
        print(f"⚠️ No valid data for plot: {title}")
        plt.close()
        return

    norm, vmin, vmax = make_norm(valid, use_log_scale)

    if use_log_scale:
        if norm is None:
            print(f"⚠️ No positive data for log-scale plot: {title}")
            plt.close()
            return
        im = ax.imshow(
            matrix,
            aspect="auto",
            origin="lower",
            cmap=BLUE_WHITE_CMAP,
            norm=norm
        )
    else:
        im = ax.imshow(
            matrix,
            aspect="auto",
            origin="lower",
            cmap=BLUE_WHITE_CMAP,
            vmin=vmin,
            vmax=vmax
        )

    ax.set_xticks(np.arange(len(THREAD_POINTS)))
    ax.set_xticklabels(THREAD_POINTS)
    ax.set_yticks(np.arange(len(REQUEST_SIZES)))
    ax.set_yticklabels(REQUEST_SIZES)

    ax.set_xlabel("Threads", fontsize=LABEL_FONT_SIZE)
    ax.set_ylabel("Request size", fontsize=LABEL_FONT_SIZE)
    ax.set_title(title, fontsize=TITLE_FONT_SIZE, pad=10)

    style_axes(ax)
    annotate_heatmap(ax, matrix, fmt=annot_fmt, fontsize=ANNOT_FONT_SIZE)

    cbar = fig.colorbar(im, ax=ax, shrink=0.92)
    cbar.ax.tick_params(labelsize=TICK_FONT_SIZE)
    cbar.set_label(cbar_label, fontsize=LABEL_FONT_SIZE)

    plt.tight_layout()
    plt.savefig(output_file, bbox_inches="tight")
    print(f"✅ Saved: {output_file}")
    plt.close()

def plot_combined_figure(
    config_tag,
    bw_matrices,
    lat_matrices,
    combos,
    output_file,
    use_log_scale_bw=True,
    use_log_scale_lat=True
):
    ncols = len(combos)
    combined_tick_size = 16
    combined_title_size = 18
    combined_annot_size = 16

    fig = plt.figure(figsize=(3.0 * ncols + 1.4, 5.8), constrained_layout=False)
    fig.patch.set_facecolor("white")

    gs = GridSpec(
        2, ncols + 1,
        figure=fig,
        width_ratios=[1] * ncols + [0.06],
        height_ratios=[1, 1],
        wspace=0.08,
        hspace=0.10
    )

    bw_all_valid = np.concatenate(
        [m[~np.isnan(m)] for m in bw_matrices if np.any(~np.isnan(m))]
    ) if any(np.any(~np.isnan(m)) for m in bw_matrices) else np.array([])

    lat_all_valid = np.concatenate(
        [m[~np.isnan(m)] for m in lat_matrices if np.any(~np.isnan(m))]
    ) if any(np.any(~np.isnan(m)) for m in lat_matrices) else np.array([])

    bw_norm, bw_vmin, bw_vmax = make_norm(bw_all_valid, use_log_scale_bw)
    lat_norm, lat_vmin, lat_vmax = make_norm(lat_all_valid, use_log_scale_lat)

    bw_axes = []
    lat_axes = []
    bw_last_im = None
    lat_last_im = None

    for col, (combo, bw_matrix, lat_matrix) in enumerate(zip(combos, bw_matrices, lat_matrices)):
        min_luns, zsz_bytes = combo

        # Top row: bandwidth
        ax_bw = fig.add_subplot(gs[0, col], sharey=bw_axes[0] if bw_axes else None)
        bw_axes.append(ax_bw)

        if use_log_scale_bw:
            bw_last_im = ax_bw.imshow(
                bw_matrix,
                aspect="auto",
                origin="lower",
                cmap=BLUE_WHITE_CMAP,
                norm=bw_norm
            )
        else:
            bw_last_im = ax_bw.imshow(
                bw_matrix,
                aspect="auto",
                origin="lower",
                cmap=BLUE_WHITE_CMAP,
                vmin=bw_vmin,
                vmax=bw_vmax
            )

        ax_bw.set_title(combo_short_title(min_luns, zsz_bytes), fontsize=combined_title_size, pad=3)
        ax_bw.set_xticks(np.arange(len(THREAD_POINTS)))
        ax_bw.set_xticklabels([])

        ax_bw.set_yticks(np.arange(len(REQUEST_SIZES)))
        style_axes(ax_bw)
        ax_bw.tick_params(axis="both", labelsize=combined_tick_size)

        if col == 0:
            ax_bw.set_yticklabels(REQUEST_SIZES, fontsize=combined_tick_size)
            ax_bw.tick_params(axis="y", which="both", labelleft=True, left=True, pad=3)
        else:
            ax_bw.tick_params(axis="y", which="both", labelleft=False, left=True)

        annotate_heatmap(ax_bw, bw_matrix, fmt="{:.0f}", fontsize=combined_annot_size)

        # Bottom row: latency
        ax_lat = fig.add_subplot(gs[1, col], sharey=lat_axes[0] if lat_axes else None)
        lat_axes.append(ax_lat)

        if use_log_scale_lat:
            lat_last_im = ax_lat.imshow(
                lat_matrix,
                aspect="auto",
                origin="lower",
                cmap=BLUE_WHITE_CMAP,
                norm=lat_norm
            )
        else:
            lat_last_im = ax_lat.imshow(
                lat_matrix,
                aspect="auto",
                origin="lower",
                cmap=BLUE_WHITE_CMAP,
                vmin=lat_vmin,
                vmax=lat_vmax
            )

        ax_lat.set_xticks(np.arange(len(THREAD_POINTS)))
        ax_lat.set_xticklabels(THREAD_POINTS, fontsize=combined_tick_size)

        ax_lat.set_yticks(np.arange(len(REQUEST_SIZES)))
        style_axes(ax_lat)
        ax_lat.tick_params(axis="both", labelsize=combined_tick_size)

        if col == 0:
            ax_lat.set_yticklabels(REQUEST_SIZES, fontsize=combined_tick_size)
            ax_lat.tick_params(axis="y", which="both", labelleft=True, left=True, pad=3)
        else:
            ax_lat.tick_params(axis="y", which="both", labelleft=False, left=True)

        annotate_heatmap(ax_lat, lat_matrix, fmt="{:.1f}", fontsize=combined_annot_size)

    cax_bw = fig.add_subplot(gs[0, -1])
    cax_lat = fig.add_subplot(gs[1, -1])

    cbar_bw = fig.colorbar(bw_last_im, cax=cax_bw)
    cbar_bw.ax.tick_params(labelsize=16)
    cbar_bw.set_label("Bandwidth (MiB/s)", fontsize=16)

    cbar_lat = fig.colorbar(lat_last_im, cax=cax_lat)
    cbar_lat.ax.tick_params(labelsize=16)
    cbar_lat.set_label("Latency (ms)", fontsize=16)

    # one combined bottom label
    fig.text(0.5, 0.04, "# concurrent zones", ha="center", va="center", fontsize=22)

    # one shared y-axis label
    fig.text(0.01, 0.5, "Request size", ha="center", va="center", rotation="vertical", fontsize=22)

    fig.subplots_adjust(left=0.05, right=0.96, top=0.92, bottom=0.12)

    plt.savefig(output_file, facecolor="white")
    print(f"✅ Saved combined figure: {output_file}")
    plt.close()

# =========================
# Storage structure
# =========================
results = {}
for combo in PLOT_COMBOS:
    results[combo] = {}

if not os.path.isdir(RESULTS_DIR):
    raise FileNotFoundError(f"RESULTS_DIR not found: {RESULTS_DIR}")

# =========================
# Load data and print values
# =========================
print("\n==================== READING EXPERIMENT FILES ====================\n")

for filename in sorted(os.listdir(RESULTS_DIR)):
    m = pattern.match(filename)
    if not m:
        continue

    vt = int(m.group("vt"))
    chnk = int(m.group("chnk"))
    maxc = int(m.group("maxc"))
    minl = int(m.group("minl"))
    zsz_bytes = int(m.group("zsz"))
    chnl = int(m.group("chnl"))
    w = int(m.group("w"))
    ssd = m.group("ssd")
    threads = int(m.group("threads"))
    bs = m.group("bs")

    combo = (minl, zsz_bytes)
    if combo not in results:
        continue
    if threads not in THREAD_POINTS:
        continue
    if bs not in REQUEST_SIZES:
        continue

    label = config_label(vt, chnk, minl)
    if label is None:
        continue

    if label not in results[combo]:
        results[combo][label] = {
            "bw": {(req, th): float("nan") for req in REQUEST_SIZES for th in THREAD_POINTS},
            "lat": {(req, th): float("nan") for req in REQUEST_SIZES for th in THREAD_POINTS},
        }

    filepath = os.path.join(RESULTS_DIR, filename)

    try:
        with open(filepath, "r") as f:
            data = json.load(f)

        job = data["jobs"][0]

        bw_bytes_s = float(job["write"]["bw_bytes"])
        bw_mib_s = bw_bytes_s / (1024.0 * 1024.0)

        lat_ns = float(job["write"]["lat_ns"]["mean"])
        lat_ms = lat_ns / 1_000_000.0

        results[combo][label]["bw"][(bs, threads)] = bw_mib_s
        results[combo][label]["lat"][(bs, threads)] = lat_ms

        zone_size_mib = bytes_to_mib(zsz_bytes)
        ssd_text = f", ssd={ssd}" if ssd is not None else ""

        print(
            f"Read file: {filename}\n"
            f"  config: vt={vt}, chnk={chnk}, maxc={maxc}, minl={minl}, "
            f"zsz={zone_size_mib} MiB, chnl={chnl}, w={w}{ssd_text}, label={label}\n"
            f"  threads={threads}, request_size={bs}\n"
            f"  bandwidth={bw_mib_s:,.2f} MiB/s, latency={lat_ms:,.2f} ms\n"
        )

    except Exception as e:
        print(f"⚠️ Skipping {filename}: {e}")

# =========================
# Print grouped values
# =========================
for combo in PLOT_COMBOS:
    min_luns, zsz = combo
    if not results[combo]:
        continue

    print(f"\n==================== {combo_title(min_luns, zsz)} ====================\n")

    for label in sorted(results[combo].keys()):
        print(f"--- {label} ---")

        print("Bandwidth (MiB/s):")
        for bs in REQUEST_SIZES:
            row_values = []
            for t in THREAD_POINTS:
                value = results[combo][label]["bw"][(bs, t)]
                row_values.append(f"T{t}=NaN" if math.isnan(value) else f"T{t}={value:,.2f}")
            print(f"  {bs:>5}: " + ", ".join(row_values))

        print("Latency (ms):")
        for bs in REQUEST_SIZES:
            row_values = []
            for t in THREAD_POINTS:
                value = results[combo][label]["lat"][(bs, t)]
                row_values.append(f"T{t}=NaN" if math.isnan(value) else f"T{t}={value:,.3f}")
            print(f"  {bs:>5}: " + ", ".join(row_values))

        print()

# =========================
# Separate heatmaps
# =========================
for combo in PLOT_COMBOS:
    min_luns, zsz_bytes = combo
    if not results[combo]:
        continue

    for label in sorted(results[combo].keys()):
        bw_matrix = build_matrix(results[combo][label]["bw"])
        lat_matrix = build_matrix(results[combo][label]["lat"])
        title_base = combo_title(min_luns, zsz_bytes)

        bw_output = heatmap_output_path("bandwidth", min_luns, zsz_bytes, label)
        lat_output = heatmap_output_path("latency", min_luns, zsz_bytes, label)

        plot_heatmap(
            bw_matrix,
            f"{title_base}, {label}",
            "Bandwidth (MiB/s)",
            bw_output,
            use_log_scale=True,
            annot_fmt="{:.0f}"
        )

        plot_heatmap(
            lat_matrix,
            f"{title_base}, {label}",
            "Latency (ms)",
            lat_output,
            use_log_scale=True,
            annot_fmt="{:.1f}"
        )

# =========================
# Combined figures
# =========================
all_labels = sorted({
    label
    for combo in PLOT_COMBOS
    for label in results[combo].keys()
})

for label in all_labels:
    combos_with_label = []
    bw_matrices = []
    lat_matrices = []

    for combo in PLOT_COMBOS:
        if label in results[combo]:
            combos_with_label.append(combo)
            bw_matrices.append(build_matrix(results[combo][label]["bw"]))
            lat_matrices.append(build_matrix(results[combo][label]["lat"]))

    if not combos_with_label:
        continue

    combined_path = combined_output_path(label)
    plot_combined_figure(
        config_tag=label,
        bw_matrices=bw_matrices,
        lat_matrices=lat_matrices,
        combos=combos_with_label,
        output_file=combined_path,
        use_log_scale_bw=True,
        use_log_scale_lat=True
    )