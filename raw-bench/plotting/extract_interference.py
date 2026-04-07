import os
import re
import json
from collections import defaultdict

# ============================================================
# Input directory
# Change this to your interference-results directory
# ============================================================
RESULT_DIR = "../exp_interference/results"

# ============================================================
# Helpers
# ============================================================
def bytes_to_mib(nbytes: int) -> int:
    return int(nbytes // (1024 * 1024))

def combo_title(min_luns: int, zsz_bytes: int) -> str:
    return f"P={min_luns}, S={bytes_to_mib(zsz_bytes)} MiB"

def config_label(mode: int, chnk: int) -> str | None:
    """
    Same mapping style as your previous code:
      mode 1 -> fixed
      mode 4 -> superblock
      mode 2 -> block
      mode 5 -> vchunk-<chnk>
    """
    if mode == 1:
        return "fixed"
    if mode == 4:
        return "superblock"
    if mode == 2:
        return "block"
    if mode == 5:
        return f"vchunk-{chnk}"
    return None

def parse_filename(fname: str):
    """
    Expected forms:
      vt-1_chnk-1_maxc-1_minl-16_zsz-134217728_chnl-8_w-2_8jobs.json
      vt-1_chnk-1_maxc-1_minl-16_zsz-134217728_chnl-8_w-2_8jobs_finish.json

    Returns:
      {
        "mode": int,
        "chnk": int,
        "maxc": int,
        "minl": int,
        "zsz": int,
        "chnl": int,
        "w": int,
        "jobs": int,
        "is_finish": bool,
      }
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

def extract_bw_from_fio_json(path: str) -> float:
    """
    Extract aggregate write bandwidth from fio JSON.
    fio's 'bw' is in KiB/s.
    We only need ratios, so units cancel out.

    Tries:
      1) jobs[0]["write"]["bw"]
      2) if multiple jobs, sum all jobs' write.bw
      3) fallback to jobs[0]["bw"] if needed
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

    # fallback
    for job in jobs:
        if "bw" in job:
            bw_sum += float(job["bw"])
            found = True

    if found:
        return bw_sum

    raise RuntimeError(f"Could not find bandwidth field in {path}")

def build_key(meta: dict):
    """
    Match baseline and finish files using all config fields except finish flag.
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

# ============================================================
# Step 1: Scan directory and collect baseline/finish pairs
# ============================================================
all_files = sorted(os.listdir(RESULT_DIR))

baseline_files = {}
finish_files = {}

for fname in all_files:
    if not fname.endswith(".json"):
        continue

    meta = parse_filename(fname)
    if meta is None:
        continue

    key = build_key(meta)
    full_path = os.path.join(RESULT_DIR, fname)

    if meta["is_finish"]:
        finish_files[key] = (fname, full_path, meta)
    else:
        baseline_files[key] = (fname, full_path, meta)

# ============================================================
# Step 2: Compute interference factors
# ============================================================
# results[(minl, zsz)][label] = list of dicts
results = defaultdict(lambda: defaultdict(list))

all_keys = sorted(set(baseline_files.keys()) | set(finish_files.keys()))

for key in all_keys:
    if key not in baseline_files:
        print(f"⚠️ Missing baseline file for key={key}")
        continue
    if key not in finish_files:
        print(f"⚠️ Missing finish file for key={key}")
        continue

    base_fname, base_path, base_meta = baseline_files[key]
    fin_fname, fin_path, fin_meta = finish_files[key]

    mode = base_meta["mode"]
    chnk = base_meta["chnk"]
    minl = base_meta["minl"]
    zsz = base_meta["zsz"]
    jobs = base_meta["jobs"]

    label = config_label(mode, chnk)
    if label is None:
        print(f"⚠️ Skipping unsupported mode/chunk in {base_fname}")
        continue

    combo = (minl, zsz)

    bw_baseline = extract_bw_from_fio_json(base_path)
    bw_finish = extract_bw_from_fio_json(fin_path)

    if bw_finish <= 0:
        interference = float("inf")
    else:
        interference = bw_baseline / bw_finish

    results[combo][label].append({
        "jobs": jobs,
        "baseline_bw_kib_s": bw_baseline,
        "finish_bw_kib_s": bw_finish,
        "interference": interference,
        "baseline_file": base_fname,
        "finish_file": fin_fname,
    })

# ============================================================
# Step 3: Print raw values
# ============================================================
CONFIG_ORDER = [
    "fixed",
    "superblock",
    "block",
    "vchunk-2",
    "vchunk-4",
    "vchunk-8",
]

print("\n==================== INTERFERENCE FACTORS ====================\n")

for combo in sorted(results.keys()):
    minl, zsz = combo
    print("============================================================")
    print(f"ZONE GEOMETRY: {combo_title(minl, zsz)}")
    print("============================================================")

    for label in CONFIG_ORDER:
        if label not in results[combo]:
            continue

        entries = sorted(results[combo][label], key=lambda x: x["jobs"])

        print(f"\n--- {label} ---")
        for entry in entries:
            jobs = entry["jobs"]
            bw_base = entry["baseline_bw_kib_s"]
            bw_fin = entry["finish_bw_kib_s"]
            interf = entry["interference"]

            print(
                f"jobs={jobs:<3} | "
                f"baseline_bw={bw_base:.0f} KiB/s | "
                f"finish_bw={bw_fin:.0f} KiB/s | "
                f"interference={interf:.1f}"
            )

    print()

# ============================================================
# Step 4: Optional compact summary only
# ============================================================
print("\n==================== COMPACT SUMMARY ====================\n")

for combo in sorted(results.keys()):
    minl, zsz = combo
    print(f"{combo_title(minl, zsz)}")

    for label in CONFIG_ORDER:
        if label not in results[combo]:
            continue

        entries = sorted(results[combo][label], key=lambda x: x["jobs"])
        vals = [f"{e['jobs']}jobs={e['interference']:.1f}" for e in entries]
        print(f"  {label}: " + ", ".join(vals))

    print()