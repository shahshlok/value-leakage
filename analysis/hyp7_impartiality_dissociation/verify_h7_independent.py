"""Independent H7 contrast verification (no imports from analyze_h7)."""
from __future__ import annotations

import json
import math
from collections import Counter
from math import comb
from pathlib import Path

import numpy as np


def fisher_exact_p(table: list[list[int]]) -> float:
    """Two-sided Fisher exact p-value for a 2x2 table."""
    a, b = table[0]
    c, d = table[1]
    row1 = a + b
    col1 = a + c
    n = row1 + c + d

    def hypergeom(x: int) -> float:
        return comb(col1, x) * comb(n - col1, row1 - x) / comb(n, row1)

    lo = max(0, row1 - (n - col1))
    hi = min(row1, col1)
    obs = hypergeom(a)
    return sum(hypergeom(x) for x in range(lo, hi + 1) if hypergeom(x) <= obs + 1e-15)


HERE = Path(__file__).resolve().parent
OUT = HERE / "outputs"
CONDITIONS = ("below_good", "above_good")
PRIMARY_9 = [
    "claude-opus-4-7_20260815_042213",
    "deepseek-v4-flash-0731_20260815_030703",
    "glm-5p2_20260815_030703",
    "inkling-small_20260815_192811",
    "inkling_20260815_030703",
    "kimi-k3_20260815_030702",
    "minimax-m3_20260815_030703",
    "qwen3.5-122b-a10b_20260815_030702",
    "qwen3p8-2p4t-a95b_20260815_030703",
]
DS_PRO = "deepseek-v4-pro-0813_20260815_030703"
REPORTED = {
    ("h6_corrected", "all"): 15.5,
    ("h6_corrected", "positive"): 14.1,
    ("h6_excluding_confirmed", "all"): 15.1,
    ("h6_excluding_confirmed_or_uncertain", "all"): 14.0,
}


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines()]


def in_stratum(row: dict, stratum: str) -> bool:
    if stratum == "all":
        return True
    if stratum == "known_label":
        return row.get("claim") is not None
    if stratum == "positive":
        return row.get("claim") is True
    if stratum == "negative":
        return row.get("claim") is False
    raise ValueError(stratum)


def log_usable(row: dict) -> bool:
    y = row.get("estimate")
    return y is not None and math.isfinite(y) and y > 0


def model_contrast(rows: list[dict], model: str, stratum: str = "all") -> tuple[float | None, int, int]:
    cells = {c: [r for r in rows if r["model_dir"] == model and r["condition"] == c] for c in CONDITIONS}
    means = {}
    ns = {}
    for c, group in cells.items():
        subset = [r for r in group if in_stratum(r, stratum) and log_usable(r)]
        ns[c] = len(subset)
        if not subset:
            means[c] = None
        else:
            means[c] = float(np.mean(np.log([r["estimate"] for r in subset])))
    if means["above_good"] is None or means["below_good"] is None:
        return None, ns["below_good"], ns["above_good"]
    delta = means["above_good"] - means["below_good"]
    return 100 * math.expm1(delta), ns["below_good"], ns["above_good"]


def pooled_contrast(rows: list[dict], models: list[str], stratum: str = "all") -> float | None:
    deltas = []
    for m in models:
        cells = {c: [r for r in rows if r["model_dir"] == m and r["condition"] == c] for c in CONDITIONS}
        means = {}
        for c, group in cells.items():
            subset = [r for r in group if in_stratum(r, stratum) and log_usable(r)]
            if not subset:
                means[c] = None
                break
            means[c] = float(np.mean(np.log([r["estimate"] for r in subset])))
        else:
            deltas.append(means["above_good"] - means["below_good"])
    if len(deltas) != len(models):
        return None
    return 100 * math.expm1(float(np.mean(deltas)))


def threshold_rates(rows: list[dict], model: str) -> dict:
    out = {}
    for c in CONDITIONS:
        group = [r for r in rows if r["model_dir"] == model and r["condition"] == c]
        numeric = [r for r in group if r.get("estimate") is not None and math.isfinite(r["estimate"])]
        above = sum(r["estimate"] > r["threshold"] for r in numeric)
        out[c] = (above / len(numeric) if numeric else None, len(numeric))
    return out


def label_counts(rows: list[dict], model: str) -> dict:
    group = [r for r in rows if r["model_dir"] == model and log_usable(r)]
    return {
        "positive": sum(r.get("claim") is True for r in group),
        "negative": sum(r.get("claim") is False for r in group),
        "missing": sum(r.get("claim") is None for r in group),
        "total_usable_y": len(group),
    }


def exclusion_distribution(exclusions: dict, h6_by_id: dict) -> dict:
    dist = Counter()
    for sid in exclusions:
        r = h6_by_id[sid]
        dist[(r["model_dir"], r["condition"])] += 1
    return dist


def fisher_disclosure(deblinded: list[dict]) -> tuple[float, list[list[int]]]:
    above = [d for d in deblinded if d["condition"] == "above_good"]
    below = [d for d in deblinded if d["condition"] == "below_good"]
    table = [
        [sum(d["finally_adopted"] is True for d in above), len(above) - sum(d["finally_adopted"] is True for d in above)],
        [sum(d["finally_adopted"] is True for d in below), len(below) - sum(d["finally_adopted"] is True for d in below)],
    ]
    p = fisher_exact_p(table)
    return p, table


def main():
    h6 = read_jsonl(OUT / "h7_outcomes.jsonl")
    full_ids = {r["source_id"] for r in read_jsonl(OUT / "full_corpus_answers.jsonl")}
    exclusions = json.loads((OUT / "disclosure_exclusions.json").read_text())
    deblinded = json.loads((OUT / "disclosure_adjudication_deblinded.json").read_text())["cases"]
    h6_by_id = {r["source_id"]: r for r in h6}

    datasets = {
        "h6_corrected": h6,
        "h6_excluding_confirmed": [r for r in h6 if r["source_id"] not in set(exclusions["confirmed"])],
        "h6_excluding_confirmed_or_uncertain": [r for r in h6 if r["source_id"] not in set(exclusions["confirmed_or_uncertain"])],
    }

    print("=== 1. POOLED CONTRASTS (primary_9, log, %) ===")
    for (ds, stratum), sol in REPORTED.items():
        mine = pooled_contrast(datasets[ds], PRIMARY_9, stratum)
        print(f"{ds:40s} {stratum:10s}  Sol={sol:5.1f}  Mine={mine:.3f}  diff={mine - sol:+.3f}")

    print("\n=== 2. PER-MODEL FOREST (h6_corrected, all stratum) ===")
    print(f"{'model':<45} {'pct':>8} {'n_below':>8} {'n_above':>8}")
    for m in PRIMARY_9 + [DS_PRO]:
        pct, nb, na = model_contrast(h6, m, "all")
        short = m.rsplit("_", 2)[0]
        print(f"{short:<45} {pct:8.2f} {nb:8d} {na:8d}")

    print("\n=== 3. DISCLOSURE EXCLUSIONS ===")
    for key in ("confirmed", "confirmed_or_uncertain"):
        ids = exclusions[key]
        print(f"{key}: n={len(ids)} subset_of_corpus={set(ids) <= full_ids}")
        dist = exclusion_distribution(ids, h6_by_id)
        for (model, cond), n in sorted(dist.items()):
            print(f"  {model.rsplit('_',2)[0]:30s} {cond:12s} {n}")

    print("\n=== 4. LABEL STRATA (usable Y > 0) ===")
    print(f"{'model':<35} {'pos':>5} {'neg':>5} {'miss':>5} {'total':>6}")
    total_neg = 0
    for m in PRIMARY_9:
        c = label_counts(h6, m)
        total_neg += c["negative"]
        short = m.rsplit("_", 2)[0]
        print(f"{short:<35} {c['positive']:5d} {c['negative']:5d} {c['missing']:5d} {c['total_usable_y']:6d}")
    print(f"TOTAL label-negative usable-Y across 9 models: {total_neg}")

    print("\n=== 5. FISHER EXACT (finally_adopted in sampled hits) ===")
    p, table = fisher_disclosure(deblinded)
    print(f"2x2: above_good {table[0]}  below_good {table[1]}  p={p:.6f}")

    print("\n=== 7. THRESHOLD CROSSING RATES (all H6, usable numeric Y) ===")
    diffs = []
    print(f"{'model':<35} {'P_below':>8} {'P_above':>8} {'diff':>8} {'n/cell':>8}")
    for m in PRIMARY_9:
        rates = threshold_rates(h6, m)
        pb, nb = rates["below_good"]
        pa, na = rates["above_good"]
        d = pa - pb
        diffs.append(d)
        short = m.rsplit("_", 2)[0]
        print(f"{short:<35} {100*pb:7.1f}% {100*pa:7.1f}% {100*d:+7.1f}pp n={nb}/{na}")
    print(f"9-model mean diff: {100*np.mean(diffs):+.2f} pp")


if __name__ == "__main__":
    main()
