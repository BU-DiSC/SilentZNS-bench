import os
import re
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import rcParams
from matplotlib.lines import Line2D

# =========================
# Font and style settings
# =========================
rcParams["font.family"] = "Linux Libertine O"

TITLE_FONT_SIZE  = 18
LABEL_FONT_SIZE  = 16
TICK_FONT_SIZE   = 16
SPINE_WIDTH      = 1.2
LEGEND_FONT_SIZE = 9

# =========================
# Input / Output
# =========================
LOG_FILE = "../exp_allocation/new_results/allocation-log"   # <-- adjust if needed

OUTPUT_DIR = "new_results"
os.makedirs(OUTPUT_DIR, exist_ok=True)

OUTPUT_PDF_RAW = os.path.join(OUTPUT_DIR, "exp_allocation-latency-avg-bar-raw.pdf")
OUTPUT_PDF_LOG = os.path.join(OUTPUT_DIR, "exp_allocation-latency-avg-bar-log.pdf")

# =========================
# Zone sizes + REQUIRED colors
# =========================
ZSIZE_128 = 134217728   # 128 MiB
ZSIZE_256 = 268435456   # 256 MiB

ZSIZE_COLOR = {
    ZSIZE_128: "#000000",  # black
    ZSIZE_256: "#1f77b4",  # blue
}

# =========================
# Expected configs (8 total)
# - stripe (vt=4) MUST be at the end
# =========================
EXPECTED_CONFIGS = [
    (2, 1, ZSIZE_128),  # F-128
    (2, 1, ZSIZE_256),  # F-256

    (5, 2, ZSIZE_128),  # V2-128
    (5, 2, ZSIZE_256),  # V2-256

    (5, 4, ZSIZE_128),  # V8-128
    (5, 4, ZSIZE_256),  # V8-256

    (4, 1, ZSIZE_128),  # S-128 (stripe)
    (4, 1, ZSIZE_256),  # S-256 (stripe)
]

# =========================
# Parsing
# =========================
LINE_RE = re.compile(
    r"vt,(?P<vt>\d+),"
    r"chnk,(?P<chnk>\d+),"
    r"maxc,(?P<maxc>\d+),"
    r"minl,(?P<minl>\d+),"
    r"zsz,(?P<zsz>\d+),"
    r"chnl,(?P<chnl>\d+),"
    r"w,(?P<w>\d+),"
    r"time_us,(?P<time_us>\d+)"
)

# =========================
# Legend naming (match your occupancy abbreviations)
#   vt=4 -> S (stripe)
#   vt=2 -> F (full)
#   vt=5 -> V{chnk}
# =========================
def series_abbrev(vt: int, chnk: int) -> str:
    if vt == 4:
        return "S"
    if vt == 2:
        return "F"
    if vt == 5:
        return f"V{chnk}"
    return f"vt-{vt}-chnk-{chnk}"  # fallback

def size_suffix(zsz: int) -> str:
    if zsz == ZSIZE_128:
        return "128"
    if zsz == ZSIZE_256:
        return "256"
    return str(zsz // (1024 * 1024))

# X-axis label style like your occupancy plots: "F-128", "V2-256", ...
def x_label(vt: int, chnk: int, zsz: int) -> str:
    return f"{series_abbrev(vt, chnk)}-{size_suffix(zsz)}"

# =========================
# Load + group times
# =========================
if not os.path.isfile(LOG_FILE):
    raise FileNotFoundError(f"Allocation log not found: {LOG_FILE}")

times_by_cfg = {}  # (vt, chnk, zsz) -> list[time_us]

with open(LOG_FILE, "r") as f:
    for line_no, line in enumerate(f, start=1):
        line = line.strip()
        if not line:
            continue

        m = LINE_RE.search(line)
        if not m:
            continue

        vt   = int(m.group("vt"))
        chnk = int(m.group("chnk"))
        zsz  = int(m.group("zsz"))
        t_us = int(m.group("time_us"))

        key = (vt, chnk, zsz)
        times_by_cfg.setdefault(key, []).append(t_us)

# =========================
# Compute average per config (in EXPECTED order)
# =========================
labels = []
avg_ms = []
counts = []
bar_colors = []

missing = []
for cfg in EXPECTED_CONFIGS:
    vt, chnk, zsz = cfg
    labels.append(x_label(vt, chnk, zsz))
    bar_colors.append(ZSIZE_COLOR.get(zsz, "#000000"))

    ts = times_by_cfg.get(cfg, [])
    n = len(ts)
    counts.append(n)

    if n == 0:
        missing.append(cfg)
        avg_ms.append(0.0)
    else:
        avg_ms.append(float(np.mean(ts)) / 1000.0)  # us -> ms

if missing:
    print("⚠️ Missing configs (no lines found in log) for:")
    for (vt, chnk, zsz) in missing:
        print(f"  vt={vt}, chnk={chnk}, zsz={zsz}")

# =========================
# Plot helpers
# =========================
def style_axes(ax):
    ax.yaxis.grid(False)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_linewidth(SPINE_WIDTH)
    ax.spines["bottom"].set_linewidth(SPINE_WIDTH)
    ax.tick_params(axis="both", labelsize=TICK_FONT_SIZE)
    ax.grid(False)

def add_size_legend(ax, loc="upper right"):
    # Legend should include color info about sizes (like your rw code)
    size_handles = [
        Line2D([0], [0], color=ZSIZE_COLOR[ZSIZE_128], linewidth=2.5, linestyle="-"),
        Line2D([0], [0], color=ZSIZE_COLOR[ZSIZE_256], linewidth=2.5, linestyle="-"),
    ]
    size_labels = ["128 MiB", "256 MiB"]

    ax.legend(
        size_handles,
        size_labels,
        loc=loc,
        fontsize=LEGEND_FONT_SIZE,
        frameon=False,
        ncol=1,
        handletextpad=0.6,
        borderaxespad=0.3,
        labelspacing=0.3,
    )

def make_avg_barplot(out_pdf, use_log=False):
    plt.figure(figsize=(9.0, 3.6))
    ax = plt.gca()

    x = np.arange(len(labels))

    if use_log:
        # log scale: hide zeros
        y_plot = [np.nan if v <= 0 else v for v in avg_ms]
        bars = ax.bar(
            x, y_plot,
            color=bar_colors,
            edgecolor="black",
            linewidth=0.8,
        )
        ax.set_yscale("log")
    else:
        bars = ax.bar(
            x, avg_ms,
            color=bar_colors,
            edgecolor="black",
            linewidth=0.8,
        )
        ax.set_ylim(bottom=0)

    ax.set_xlabel("SSD Config", fontsize=LABEL_FONT_SIZE)
    ax.set_ylabel("Allocation Latency (ms)", fontsize=LABEL_FONT_SIZE)
    ax.set_title(
        "Allocation Latency (Average)" if use_log else "Allocation Latency (Average)",
        fontsize=TITLE_FONT_SIZE
    )

    # X axis marked like occupancy abbreviations
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=TICK_FONT_SIZE)

    style_axes(ax)

    # Legend with size color info (match your other plots)
    add_size_legend(ax, loc="upper right")

    # annotate n above each bar (optional but useful; keeps same color)
    finite_vals = [v for v in avg_ms if v > 0]
    max_v = max(finite_vals) if finite_vals else 1.0

    for i, (rect, n, v) in enumerate(zip(bars, counts, avg_ms)):
        if use_log:
            if v <= 0:
                ax.text(i, 1.0, "n=0", ha="center", va="bottom", fontsize=10)
            else:
                ax.text(
                    rect.get_x() + rect.get_width() / 2,
                    rect.get_height() * 1.12,
                    f"n={n}",
                    ha="center",
                    va="bottom",
                    fontsize=10,
                )
        else:
            y = (v + 0.02 * max_v) if v > 0 else (0.02 * max_v)
            ax.text(
                rect.get_x() + rect.get_width() / 2,
                y,
                f"n={n}",
                ha="center",
                va="bottom",
                fontsize=10,
            )

    plt.tight_layout()
    plt.savefig(out_pdf)
    plt.close()
    print(f"✅ Saved: {out_pdf}")

# =========================
# Generate BOTH plots (raw + log-y)
# =========================
make_avg_barplot(OUTPUT_PDF_RAW, use_log=False)
make_avg_barplot(OUTPUT_PDF_LOG, use_log=True)
