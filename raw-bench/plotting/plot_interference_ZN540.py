import os
import re
import json
import math
import matplotlib.pyplot as plt
from collections import defaultdict
from matplotlib import rcParams

# ============================================================
# Style settings (same spirit as occupancy plot)
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
RESULT_DIR = "../exp_interference/results"
OUT_DIR = "plots"
os.makedirs(OUT_DIR, exist_ok=True)

OUTPUT_PATH = os.path.join(OUT_DIR, "interference_factor_two_configs.pdf")

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

def parse_filename(fname: str):
    """
    Expected forms:
      vt-1_chnk-1_maxc-1_minl-16_zsz-134217728_chnl-8_w-2_8jobs.json
      vt-1_chnk-1_maxc-1_minl-16_zsz-134217728_chnl-8_w-2_8jobs_finish.json
    """
    pattern = re.compile(
        r"^vt-(?P<mode>\d+)"
        r"_chnk-(?P<chnk>\d+)"
        r"_maxc-(?P<maxc>\d+)"
        r"_minl-(?P<minl>\d+)"
        r"_zsz-(?P<zsz>\d+)"
        r"_chnl-(?P<chnl>\d+)"
        r"_w-(?P<w>\d+)"
        r"_(?P<jobs>\d+)jobs"
        r"(?P<finish>_finish)?\.json$"
    )

    m = pattern.match(fname)
    if not m:
        return None

    return {
        "mode": int(m.group("mode")),
        "chnk": int(m.group("chnk")),
        "maxc": int(m.group("maxc")),
        "minl": int(m.group("minl")),
        "zsz": int(m.group("zsz")),
        "chnl": int(m.group("chnl")),
        "w": int(m.group("w")),
        "jobs": int(m.group("jobs")),
        "is_finish": m.group("finish") is not None,
    }

def build_key(meta: dict):
    """
    Match Baseline and finish files using all config fields except finish flag.
    """
    return (
        meta["mode"],
        meta["chnk"],
        meta["maxc"],
        meta["minl"],
        meta["zsz"],
        meta["chnl"],
        meta["w"],
        meta["jobs"],
    )

def extract_bw_from_fio_json(path: str) -> float:
    """
    Extract aggregate write bandwidth from fio JSON.
    fio 'bw' is in KiB/s. Ratio cancels units anyway.
    """
    with open(path, "r") as f:
        data = json.load(f)

    jobs = data.get("jobs", [])
    if not jobs:
        raise RuntimeError(f"No 'jobs' found in {path}")

    bw_sum = 0.0
    found = False

    for job in jobs:
        write_obj = job.get("write", {})
        if "bw" in write_obj:
            bw_sum += float(write_obj["bw"])
            found = True

    if found:
        return bw_sum

    for job in jobs:
        if "bw" in job:
            bw_sum += float(job["bw"])
            found = True

    if found:
        return bw_sum

    raise RuntimeError(f"Could not find bandwidth field in {path}")

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
# Step 1: Scan directory and collect Baseline/finish pairs
# ============================================================
all_files = sorted(os.listdir(RESULT_DIR))

Baseline_files = {}
finish_files = {}

for fname in all_files:
    if not fname.endswith(".json"):
        continue

    meta = parse_filename(fname)
    if meta is None:
        continue

    # only keep vtable 1 and 4
    if meta["mode"] not in (1, 4):
        continue

    key = build_key(meta)
    full_path = os.path.join(RESULT_DIR, fname)

    if meta["is_finish"]:
        finish_files[key] = (fname, full_path, meta)
    else:
        Baseline_files[key] = (fname, full_path, meta)

# ============================================================
# Step 2: Compute interference factor
#
# Since you said there are no zone geometries anymore for plotting,
# we aggregate by config label only.
#
# interference_all[label] = [{"jobs": ..., "interference": ..., ...}, ...]
# ============================================================
interference_all = defaultdict(list)

all_keys = sorted(set(Baseline_files.keys()) | set(finish_files.keys()))

print("\n==================== INTERFERENCE FACTORS ====================\n")

for key in all_keys:
    if key not in Baseline_files:
        print(f"⚠️ Missing Baseline file for key={key}")
        continue
    if key not in finish_files:
        print(f"⚠️ Missing finish file for key={key}")
        continue

    base_fname, base_path, base_meta = Baseline_files[key]
    fin_fname, fin_path, fin_meta = finish_files[key]

    mode = base_meta["mode"]
    jobs = base_meta["jobs"]

    label = config_label(mode)
    if label is None:
        continue

    bw_Baseline = extract_bw_from_fio_json(base_path)
    bw_finish = extract_bw_from_fio_json(fin_path)

    if bw_finish <= 0:
        interference = float("inf")
    else:
        interference = bw_Baseline / bw_finish

    interference_all[label].append({
        "jobs": jobs,
        "Baseline_bw_kib_s": bw_Baseline,
        "finish_bw_kib_s": bw_finish,
        "interference": interference,
        "Baseline_file": base_fname,
        "finish_file": fin_fname,
    })

    print(
        f"{label}: jobs={jobs:<3} | "
        f"Baseline_bw={bw_Baseline:.0f} KiB/s | "
        f"finish_bw={bw_finish:.0f} KiB/s | "
        f"interference={interference:.6f}"
    )

# ============================================================
# Step 3: Sort by jobs and print exact arrays used for plotting
# ============================================================
print("\n==================== FINAL ARRAYS PASSED TO PLOT ====================\n")

for label in CONFIG_ORDER:
    if label not in interference_all:
        continue

    interference_all[label] = sorted(interference_all[label], key=lambda x: x["jobs"])

    x_vals = [e["jobs"] for e in interference_all[label]]
    y_vals = [e["interference"] for e in interference_all[label]]

    print(f"{label}:")
    print(f"  X (Jobs): {x_vals}")
    print(f"  Y (Interference): {[f'{y:.6f}' for y in y_vals]}")
    print()

# ============================================================
# Step 4: Axis limits
# ============================================================
all_jobs = []
all_interference = []

for label in CONFIG_ORDER:
    if label not in interference_all:
        continue

    all_jobs.extend([e["jobs"] for e in interference_all[label]])
    all_interference.extend(
        [e["interference"] for e in interference_all[label]
         if not math.isnan(e["interference"]) and not math.isinf(e["interference"])]
    )

if not all_jobs:
    raise RuntimeError("No valid job counts found for plotting.")

if not all_interference:
    raise RuntimeError("No valid interference-factor values found for plotting.")

xmin = min(all_jobs)
xmax = max(all_jobs)
xpad = max(0.5, 0.05 * (xmax - xmin if xmax > xmin else 1))

ymin = 0
ymax = max(all_interference) * 1.08

# ============================================================
# Step 5: Plot interference factor vs number of jobs
# ============================================================
plt.figure(figsize=(4, 3))
ax = plt.gca()

for label in CONFIG_ORDER:
    if label not in interference_all:
        continue

    x_vals = [e["jobs"] for e in interference_all[label]]
    y_vals = [e["interference"] for e in interference_all[label]]
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

ax.set_xlabel("(d) Finish Concurrency", fontsize=LABEL_FONT_SIZE)
ax.set_ylabel("Interference", fontsize=LABEL_FONT_SIZE)
ax.set_title("", fontsize=TITLE_FONT_SIZE, pad=4)

ax.set_xlim(xmin - xpad, xmax + xpad)
ax.set_ylim(ymin, ymax)

job_ticks = sorted(set(all_jobs))
ax.set_xticks(job_ticks)
ax.set_xticklabels([str(x) for x in job_ticks])

style_axes(ax)

ax.legend(
    loc="lower left",
    fontsize=LEGEND_FONT_SIZE,
    frameon=False,
)

plt.tight_layout()
plt.savefig(OUTPUT_PATH, bbox_inches="tight", pad_inches=0.01)
plt.close()

print(f"✅ Saved interference-factor plot: {OUTPUT_PATH}")

# ============================================================
# Final summary
# ============================================================
print("\n==================== SAVED PLOT ====================\n")
print(f"  - {OUTPUT_PATH}")

# ============================================================
# Step 6: Compute percentage decrease (Baseline → SilentZNS)
# ============================================================
print("\n==================== PERCENTAGE DECREASE ====================\n")

if "Baseline" in interference_all and "SilentZNS" in interference_all:
    conf_entries = {e["jobs"]: e["interference"] for e in interference_all["Baseline"]}
    silent_entries = {e["jobs"]: e["interference"] for e in interference_all["SilentZNS"]}

    common_jobs = sorted(set(conf_entries.keys()) & set(silent_entries.keys()))

    if not common_jobs:
        print("⚠️ No common job counts found between Baseline and SilentZNS")
    else:
        decreases = []

        print("Per-job percentage decrease in interference:\n")

        for jobs in common_jobs:
            conf_val = conf_entries[jobs]
            silent_val = silent_entries[jobs]

            if conf_val > 0:
                decrease = ((conf_val - silent_val) / conf_val) * 100.0
                decreases.append(decrease)

                print(
                    f"Jobs {jobs:>3} | "
                    f"Baseline: {conf_val:.6f} | "
                    f"SilentZNS: {silent_val:.6f} | "
                    f"Decrease: {decrease:6.2f}%"
                )
            else:
                print(
                    f"Jobs {jobs:>3} | "
                    f"Baseline interference is non-positive, skipping"
                )

        if decreases:
            avg_decrease = sum(decreases) / len(decreases)
            print(f"\nAverage interference decrease: {avg_decrease:.2f}%")
else:
    print("⚠️ Missing one of the configs (Baseline or SilentZNS)")