import os
import json
import matplotlib.pyplot as plt
from matplotlib import rcParams

# === Font and style settings ===
rcParams["font.family"] = "Linux Libertine O"

# Font size settings (compact)
TITLE_FONT_SIZE = 18
LABEL_FONT_SIZE = 16
TICK_FONT_SIZE = 16
LEGEND_FONT_SIZE = 11

# Directories
BASELINE_DIR = "../exp_rw_bench/results"
INTERFERE_DIR = "../exp_interference/results"
OUTPUT_PATH = "results/exp_interference_iops_ratio.pdf"

THREAD_RANGE = list(range(1, 8))  # 1 to 7 threads

# Strategy mapping (used for filenames / internal keys)
strategies = {
    "1": "lazy",    # will be shown as confzns++
    "4": "stripe"   # will be shown as stripe
}

# Plot label mapping (ONLY affects what is shown on the plot + printed table)
plot_label_map = {
    "lazy": "confzns++",
    "stripe": "SilentZNS",
}

# Color map
color_map = {
    "stripe": "#6ca768",
    "lazy": "black",
}

# Marker and line styles
marker_map = {
    "stripe": "D",
    "lazy": "+",
}
linestyle_map = {
    "stripe": "-",
    "lazy": "-",
}

# ==============================
# Data collection
# ==============================
ratios_by_strategy = {label: [] for label in strategies.values()}

# NEW: store raw values for printing
raw_values = {label: [] for label in strategies.values()}

for strategy_key, label in strategies.items():
    for t in THREAD_RANGE:
        baseline_file = os.path.join(BASELINE_DIR, f"{strategy_key}_threads_{t}.json")
        interfere_file = os.path.join(INTERFERE_DIR, f"{strategy_key}_finish_{t}jobs.json")

        try:
            with open(baseline_file) as f:
                base_data = json.load(f)
                base_iops = float(base_data["jobs"][0]["write"]["iops"])
        except Exception as e:
            print(f"⚠️ Missing baseline file: {baseline_file} — {e}")
            base_iops = 0.0

        try:
            with open(interfere_file) as f:
                int_data = json.load(f)
                int_iops = float(int_data["jobs"][0]["write"]["iops"])
        except Exception as e:
            print(f"⚠️ Missing interference file: {interfere_file} — {e}")
            int_iops = 0.0

        ratio = base_iops / int_iops if (base_iops > 0 and int_iops > 0) else 0.0

        ratios_by_strategy[label].append(ratio)

        # Store raw values
        raw_values[label].append({
            "threads": t,
            "baseline_iops": base_iops,
            "interfere_iops": int_iops,
            "ratio": ratio,
            "baseline_file": baseline_file,
            "interfere_file": interfere_file,
        })

# ==============================
# Print RAW values used
# ==============================
print("\n🧾 Raw IOPS values used to compute interference ratios:\n")

for label in ["lazy", "stripe"]:
    disp = plot_label_map[label]
    print(f"🔹 {disp} ({label})")
    print("Threads  Baseline_IOPS    Interfere_IOPS   Ratio")
    print("-------  --------------  ---------------  ------")

    for entry in raw_values[label]:
        print(
            f"{entry['threads']:>7d}  "
            f"{entry['baseline_iops']:>14.2f}  "
            f"{entry['interfere_iops']:>15.2f}  "
            f"{entry['ratio']:>6.2f}"
        )

    print()

# ==============================
# Print ratio-only table (as before)
# ==============================
print("\n📊 Interference IOPS Ratios (baseline / interference):")
header = "Strategy       " + "  ".join([f"{t:>3d}T" for t in THREAD_RANGE])
print(header)
print("-" * len(header))

for label in ["lazy", "stripe"]:
    ratios = ratios_by_strategy[label]
    ratio_str = "  ".join(f"{r:.2f}" for r in ratios)
    disp = plot_label_map[label]
    print(f"{disp:<14s}{ratio_str}")

# ==============================
# Plotting
# ==============================
plt.figure(figsize=(4, 3))
ax = plt.gca()

for label in ["lazy", "stripe"]:
    ratios = ratios_by_strategy[label]
    ax.plot(
        THREAD_RANGE,
        ratios,
        label=plot_label_map[label],
        marker=marker_map[label],
        color=color_map[label],
        linestyle=linestyle_map[label],
        linewidth=1.5,
        markersize=6,
        markerfacecolor="none",
    )

# Axis formatting
ax.set_xlabel("Number of Threads", fontsize=LABEL_FONT_SIZE)
ax.set_ylabel("Finish Interference", fontsize=LABEL_FONT_SIZE)
ax.grid(False)
ax.set_xticks(THREAD_RANGE)
ax.set_xticklabels(THREAD_RANGE, fontsize=TICK_FONT_SIZE)
ax.tick_params(axis="y", labelsize=TICK_FONT_SIZE)
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)
ax.spines["left"].set_linewidth(1.2)
ax.spines["bottom"].set_linewidth(1.2)
ax.set_ylim(bottom=0)

# Legend
ax.legend(loc="lower right", fontsize=LEGEND_FONT_SIZE, frameon=False, ncol=1)

# Save
os.makedirs("results", exist_ok=True)
plt.tight_layout()
plt.savefig(OUTPUT_PATH)
plt.close()

print(f"\n✅ Interference IOPS ratio plot saved to {OUTPUT_PATH}")






# import os
# import json
# import matplotlib.pyplot as plt
# from matplotlib import rcParams

# # === Font and style settings ===
# rcParams["font.family"] = "Linux Libertine O"

# # Font size settings (compact)
# TITLE_FONT_SIZE = 18
# LABEL_FONT_SIZE = 16
# TICK_FONT_SIZE = 16
# LEGEND_FONT_SIZE = 11

# # Directories
# BASELINE_DIR = "../exp_rw_bench/results"
# INTERFERE_DIR = "../exp_interference/results"
# OUTPUT_PATH = "results/exp_interference_iops_ratio.pdf"

# THREAD_RANGE = list(range(1, 8))  # 1 to 7 threads

# # Strategy mapping
# strategies = {
#     "0": "direct",
#     "1": "lazy",
#     "2": "chunk-1",
#     "2-chnk-2-22": "chunk-2",
#     "2-chnk-11-22": "chunk-11",
#     "4": "stripe"
# }

# # Color map consistent with other plots
# color_map = {
#     "chunk-1": "#6b92b9",   # darker shade of #aec7e8
#     "chunk-2": "#6b92b9",   # same as chunk-1
#     "chunk-11": "#6b92b9",  # same as chunk-1
#     "stripe": "#6ca768",    # darker green of #b5e7a0
#     "lazy": "black",
#     "direct": "black"
# }


# # Marker and line styles
# marker_map = {
#     "chunk-1": "o",
#     "chunk-2": "s",
#     "chunk-11": "^",
#     "stripe": "D",
#     "lazy": "+",
#     "direct": "x"
# }
# linestyle_map = {
#     "chunk-1": "-",
#     "chunk-2": "--",
#     "chunk-11": ":",
#     "stripe": "-",
#     "lazy": "-",
#     "direct": "--"
# }



# # Data collection
# ratios_by_strategy = {label: [] for label in strategies.values()}

# for strategy_key, label in strategies.items():
#     for t in THREAD_RANGE:
#         baseline_file = os.path.join(BASELINE_DIR, f"{strategy_key}_threads_{t}.json")
#         interfere_file = os.path.join(INTERFERE_DIR, f"{strategy_key}_finish_{t}jobs.json")

#         try:
#             with open(baseline_file) as f:
#                 base_data = json.load(f)
#                 base_iops = float(base_data["jobs"][0]["write"]["iops"])
#         except Exception as e:
#             print(f"⚠️ Missing baseline file: {baseline_file} — {e}")
#             base_iops = 0

#         try:
#             with open(interfere_file) as f:
#                 int_data = json.load(f)
#                 int_iops = float(int_data["jobs"][0]["write"]["iops"])
#         except Exception as e:
#             print(f"⚠️ Missing interference file: {interfere_file} — {e}")
#             int_iops = 0

#         ratio = base_iops / int_iops if base_iops > 0 else 0
#         ratios_by_strategy[label].append(ratio)

# # ✅ Print interference ratios to terminal
# print("\n📊 Interference IOPS Ratios:")
# header = "Strategy     " + "  ".join([f"{t:>3d}T" for t in THREAD_RANGE])
# print(header)
# print("-" * len(header))
# for label in sorted(ratios_by_strategy.keys()):
#     ratios = ratios_by_strategy[label]
#     ratio_str = "  ".join(f"{r:.2f}" for r in ratios)
#     print(f"{label:<12s}{ratio_str}")


# # Plotting
# plt.figure(figsize=(4, 3))
# ax = plt.gca()

# for label in strategies.values():
#     ratios = ratios_by_strategy[label]
#     ax.plot(
#         THREAD_RANGE,
#         ratios,
#         label=label,
#         marker=marker_map[label],
#         color=color_map[label],
#         linestyle=linestyle_map[label],
#         linewidth=1.5,
#         markersize=6,
#         markerfacecolor="none", 
#     )

# # Axis formatting
# ax.set_xlabel("(a) Number of Threads", fontsize=LABEL_FONT_SIZE)
# ax.set_ylabel("Finish Interference", fontsize=LABEL_FONT_SIZE)
# ax.grid(False)
# ax.set_xticks(THREAD_RANGE)
# ax.set_xticklabels(THREAD_RANGE, fontsize=TICK_FONT_SIZE)
# ax.tick_params(axis='y', labelsize=TICK_FONT_SIZE)
# ax.spines['top'].set_visible(False)
# ax.spines['right'].set_visible(False)
# ax.spines['left'].set_linewidth(1.2)
# ax.spines['bottom'].set_linewidth(1.2)
# ax.set_ylim(bottom=0)

# # Legend
# ax.legend(loc="lower right", fontsize=LEGEND_FONT_SIZE, frameon=False, ncol=2)

# # Save
# os.makedirs("results", exist_ok=True)
# plt.tight_layout()
# plt.savefig(OUTPUT_PATH)
# plt.close()
# print(f"\n✅ Interference IOPS ratio plot saved to {OUTPUT_PATH}")
