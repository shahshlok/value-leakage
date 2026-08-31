"""Deterministic balanced partition of the 40 blinded disclosure packets into N batches.
Greedy longest-processing-time (LPT) by character count. Reproducible, no randomness."""
import json, pathlib
BLIND = pathlib.Path("outputs/disclosure_blind")
N = 8
sizes = {}
for p in sorted(BLIND.glob("D*.txt")):
    sizes[p.stem] = len(p.read_text(encoding="utf-8"))
bins = [[] for _ in range(N)]
loads = [0]*N
for bid, sz in sorted(sizes.items(), key=lambda kv: -kv[1]):
    j = loads.index(min(loads))
    bins[j].append(bid); loads[j] += sz
batches = {f"batch{j+1:02d}": sorted(bins[j], key=lambda b:int(b[1:])) for j in range(N)}
out = {"n_batches": N, "batches": batches,
       "loads_chars": {f"batch{j+1:02d}": loads[j] for j in range(N)},
       "counts": {f"batch{j+1:02d}": len(bins[j]) for j in range(N)}}
pathlib.Path("outputs/adjudication_batches.json").write_text(json.dumps(out, indent=2))
for j in range(N):
    print(f"batch{j+1:02d}: {len(bins[j])} packets, {loads[j]:>7d} chars -> {bins[j]}")
