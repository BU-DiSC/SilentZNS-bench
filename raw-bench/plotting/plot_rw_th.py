import os
import json
import re
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib import rcParams

# === Font and style settings ===
rcParams["font.family"] = "Linux Libertine O"
TITLE_FONT_SIZE = 18
LABEL_FONT_SIZE = 16
TICK_FONT_SIZE = 16
LEGEND_FONT_SIZE = 11
LINE_WIDTH = 1.5
MARKER_SIZE = 6
SPINE_WIDTH = 1.2

# === Paths ===
RESULTS_DIR = "../exp_rw_bench/results"
OUTPUT_DIR = "results"
os.makedirs(OUTPUT_DIR, exist_ok=True)
OUTPUT_IOPS = os.path.join(OUTPUT_DIR, "exp_rw-all-iops.pdf")
OUTPUT_BW = os.path.join(OUTPUT_DIR, "exp_rw-all-bw.pdf")

# === Strategy mapping ===
strategies = {
    "0": "direct",
    "1": "lazy",
    "2-chnk-1-22": "chunk-1",
    "2-chnk-2-22": "chunk-2",
    "2-chnk-11-22": "chunk-11",
    "4": "stripe"
}

# === Access-type color map (sharp shades) ===
access_color_map = {
    "read_seq":  "#cba6e3",  # deep purple
    "read_rand": "#5e3c99",  # same purple, will differ by linestyle
    "write":     "#000000"   # sharp coral red
}

# === Line style map per access type ===
access_linestyle_map = {
    "read_seq": "-",
    "read_rand": "-",  # dotted
    "write": ":"
}

# === Marker per strategy ===
marker_map = {
    "chunk-1": "o",
    "chunk-2": "s",
    "chunk-11": "^",
    "lazy": "+",
    "direct": "x",
    "stripe": "D"
}

# === Filename parser ===
pattern = re.compile(r"(?P<mode>[a-zA-Z0-9\-]+)_threads_(?P<threads>\d+)(?:_(?P<rwtype>read_(?:seq|rand)))?\.json")

# === Data collector ===
results = {}

for filename in os.listdir(RESULTS_DIR):
    match = pattern.match(filename)
    if not match:
        continue

    mode = match.group("mode")
    threads = int(match.group("threads"))
    rwtype = match.group("rwtype")
    access_type = "write" if rwtype is None else rwtype

    if mode not in strategies:
        continue

    label = strategies[mode]
    key = (label, access_type)
    filepath = os.path.join(RESULTS_DIR, filename)

    try:
        with open(filepath, "r") as f:
            data = json.load(f)
        job = data["jobs"][0]
        metric_key = "read" if access_type.startswith("read") else "write"
        iops = float(job[metric_key]["iops"]) / 1000.0
        bw = float(job[metric_key]["bw_bytes"]) / (1024 ** 2)

        if key not in results:
            results[key] = {"threads": [], "k_iops": [], "mb_bw": []}
        results[key]["threads"].append(threads)
        results[key]["k_iops"].append(iops)
        results[key]["mb_bw"].append(bw)

    except Exception as e:
        print(f"⚠️ Skipping {filename}: {e}")

# === Sort threads for each result key ===
for key in results:
    zipped = sorted(zip(results[key]["threads"],
                        results[key]["k_iops"],
                        results[key]["mb_bw"]))
    threads_sorted, iops_sorted, bw_sorted = zip(*zipped)
    results[key]["threads"] = threads_sorted
    results[key]["k_iops"] = iops_sorted
    results[key]["mb_bw"] = bw_sorted

# === Plotting function ===
def plot_combined_metric(metric_key, ylabel, output_file, title):
    plt.figure(figsize=(4, 3))
    ax = plt.gca()

    for (label, access_type), data in results.items():
        color = access_color_map[access_type]
        linestyle = access_linestyle_map[access_type]
        marker = marker_map[label]

        ax.plot(
            data["threads"],
            data[metric_key],
            label=label,
            marker=marker,
            linestyle=linestyle,
            color=color,
            markerfacecolor='none',
            markeredgewidth=1.5,
            linewidth=LINE_WIDTH,
            markersize=MARKER_SIZE
        )

    # === Access Type Legend (Top) ===
    color_legend = [
        Line2D([0], [0], color=access_color_map["read_seq"], lw=LINE_WIDTH, label="read_seq", linestyle=access_linestyle_map["read_seq"]),
        Line2D([0], [0], color=access_color_map["read_rand"], lw=LINE_WIDTH, label="read_rand", linestyle=access_linestyle_map["read_rand"]),
        Line2D([0], [0], color=access_color_map["write"], lw=LINE_WIDTH, label="write", linestyle=access_linestyle_map["write"]),
    ]
    access_legend = ax.legend(
        handles=color_legend,
        loc="center",
        bbox_to_anchor=(0.4, 1.14),
        ncol=3,
        fontsize=12,
        frameon=False,
        columnspacing=0.5
    )
    ax.add_artist(access_legend)

    # === Strategy Marker Legend (Bottom Left) ===
    strategy_legend = [
        Line2D([0], [0],
               color="black",
               marker=marker_map[label],
               linestyle="",
               markersize=MARKER_SIZE,
               label=label,
               markerfacecolor='none',
               markeredgewidth=1.5)
        for label in marker_map
    ]
    ax.legend(
        handles=strategy_legend,
        loc="upper left",
        bbox_to_anchor=(0.00, 1.1),
        fontsize=11,
        columnspacing=0.5,
        frameon=False,
        ncol=2
    )

    # === Axes & Style ===
    ax.set_xlabel("(b) Number of Threads", fontsize=LABEL_FONT_SIZE)
    ax.set_ylabel(ylabel, fontsize=LABEL_FONT_SIZE)
    ax.set_xticks(sorted({t for d in results.values() for t in d["threads"]}))
    ax.tick_params(axis='both', labelsize=TICK_FONT_SIZE)
    ax.set_ylim(0, 80)
    ax.set_xlim(left=0)
    ax.set_ylim(bottom=0)

    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_linewidth(SPINE_WIDTH)
    ax.spines['bottom'].set_linewidth(SPINE_WIDTH)
    ax.grid(False)

    if title:
        ax.set_title(title, fontsize=TITLE_FONT_SIZE)

    plt.tight_layout()
    plt.subplots_adjust(top=0.88)
    plt.savefig(output_file)
    print(f"✅ Saved: {output_file}")
    plt.close()

# === Generate plots ===
plot_combined_metric("k_iops", "Throughput (KIOps)", OUTPUT_IOPS, "")
plot_combined_metric("mb_bw", "Bandwidth (MB/s)", OUTPUT_BW, "")














# import os
# import json
# import re
# import matplotlib.pyplot as plt
# from matplotlib.lines import Line2D

# # Font size settings (optimized for 4 subfigures side-by-side)
# TITLE_FONT_SIZE = 12
# LABEL_FONT_SIZE = 11
# TICK_FONT_SIZE = 11
# LEGEND_FONT_SIZE = 7.5
# # Paths
# RESULTS_DIR = "../exp_rw_bench/results"
# OUTPUT_DIR = "results"
# os.makedirs(OUTPUT_DIR, exist_ok=True)

# # Output paths
# OUTPUT_IOPS = os.path.join(OUTPUT_DIR, "exp_rw-all-iops.pdf")
# OUTPUT_BW = os.path.join(OUTPUT_DIR, "exp_rw-all-bw.pdf")

# # Strategy mapping
# strategies = {
#     "0": "direct",
#     "1": "lazy",
#     "2-chnk-1-22": "chunk-1",
#     "2-chnk-2-22": "chunk-2",
#     "2-chnk-11-22": "chunk-11",
#     "4": "stripe"
# }

# # Fixed color by access type
# access_color_map = {
#     "read_seq": "#1f77b4",   # blue
#     "read_rand": "#9467bd",  # purple
#     "write": "#2ca02c"       # green
# }

# # Marker by strategy
# marker_map = {
#     "chunk-1": "o",
#     "chunk-2": "s",
#     "chunk-11": "^",
#     "lazy": "+",
#     "direct": "x",
#     "stripe": "o"
# }

# # Regex for parsing filenames
# pattern = re.compile(r"(?P<mode>[a-zA-Z0-9\-]+)_threads_(?P<threads>\d+)(?:_(?P<rwtype>read_(?:seq|rand)))?\.json")

# # Data collection
# results = {}

# for filename in os.listdir(RESULTS_DIR):
#     match = pattern.match(filename)
#     if not match:
#         continue

#     mode = match.group("mode")
#     threads = int(match.group("threads"))
#     rwtype = match.group("rwtype")
#     access_type = "write" if rwtype is None else rwtype

#     if mode not in strategies:
#         continue

#     label = strategies[mode]
#     key = (label, access_type)
#     filepath = os.path.join(RESULTS_DIR, filename)

#     try:
#         with open(filepath, "r") as f:
#             data = json.load(f)
#         job = data["jobs"][0]
#         metric_key = "read" if access_type.startswith("read") else "write"
#         iops = float(job[metric_key]["iops"]) / 1000.0
#         bw = float(job[metric_key]["bw_bytes"]) / (1024 ** 2)

#         if key not in results:
#             results[key] = {"threads": [], "k_iops": [], "mb_bw": []}
#         results[key]["threads"].append(threads)
#         results[key]["k_iops"].append(iops)
#         results[key]["mb_bw"].append(bw)

#     except Exception as e:
#         print(f"Skipping {filename}: {e}")

# # Sort thread results
# for key in results:
#     zipped = sorted(zip(results[key]["threads"],
#                         results[key]["k_iops"],
#                         results[key]["mb_bw"]))
#     threads_sorted, iops_sorted, bw_sorted = zip(*zipped)
#     results[key]["threads"] = threads_sorted
#     results[key]["k_iops"] = iops_sorted
#     results[key]["mb_bw"] = bw_sorted

# # Plotting function
# def plot_combined_metric(metric_key, ylabel, output_file, title):
#     plt.figure(figsize=(4, 3))
#     ax = plt.gca()

#     for (label, access_type), data in results.items():
#         color = access_color_map[access_type]
#         marker = marker_map[label]

#         if label == "stripe":
#             plt.plot(
#                 data["threads"],
#                 data[metric_key],
#                 color=color,
#                 marker=marker,
#                 linestyle="-",
#                 linewidth=1.5,
#                 markersize=6,
#                 markerfacecolor='none',
#                 markeredgewidth=1.5
#             )
#         else:
#             plt.plot(
#                 data["threads"],
#                 data[metric_key],
#                 color=color,
#                 marker=marker,
#                 linestyle="-",
#                 linewidth=1.5,
#                 markersize=6
#             )

#     # Access type legend (top horizontal)
#     color_legend = [
#         Line2D([0], [0], color=access_color_map["read_seq"], lw=1.5, label="read_seq"),
#         Line2D([0], [0], color=access_color_map["read_rand"], lw=1.5, label="read_rand"),
#         Line2D([0], [0], color=access_color_map["write"], lw=1.5, label="write"),
#     ]

#     access_legend = plt.legend(
#         handles=color_legend,
#         loc="center",
#         bbox_to_anchor=(0.5, 1.12),
#         ncol=3,
#         fontsize=LEGEND_FONT_SIZE,
#         frameon=False
#     )
#     plt.gca().add_artist(access_legend)

#     # Strategy legend (left)
#     strategy_legend = [
#         Line2D(
#             [0], [0],
#             color="black",
#             marker=marker_map[label],
#             linestyle="",
#             markersize=6,
#             label=label,
#             markerfacecolor='none' if label == "stripe" else "black",
#             markeredgewidth=1.5 if label == "stripe" else 1
#         )
#         for label in marker_map
#     ]

#     plt.legend(
#         handles=strategy_legend,
#         loc="upper left",
#         bbox_to_anchor=(0.01, 1.0),
#         fontsize=LEGEND_FONT_SIZE,
#         frameon=False,
#         ncol=2
#     )

#     # Axes and labels
#     plt.xlabel("Number of Threads", fontsize=LABEL_FONT_SIZE)
#     plt.ylabel(ylabel, fontsize=LABEL_FONT_SIZE)
#     if title:
#         plt.title(title, fontsize=TITLE_FONT_SIZE)

#     ax.tick_params(axis='both', labelsize=TICK_FONT_SIZE)
#     ax.spines['top'].set_visible(False)
#     ax.spines['right'].set_visible(False)
#     ax.spines['left'].set_linewidth(1.2)
#     ax.spines['bottom'].set_linewidth(1.2)
#     ax.yaxis.grid(True, linestyle='--', linewidth=0.4)
#     ax.xaxis.grid(False)

#     plt.xticks(sorted({t for d in results.values() for t in d["threads"]}))
#     plt.xlim(left=0)
#     plt.ylim(bottom=0)
#     plt.tight_layout()
#     plt.subplots_adjust(top=0.88)
#     plt.savefig(output_file)
#     print(f"Saved: {output_file}")
#     plt.close()

# # Generate plots
# plot_combined_metric("k_iops", "Throughput (KIOPS)", OUTPUT_IOPS, "")
# plot_combined_metric("mb_bw", "Bandwidth (MB/s)", OUTPUT_BW, "")
