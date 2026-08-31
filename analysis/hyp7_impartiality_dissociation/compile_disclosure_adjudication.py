"""Compile blinded Sonnet disclosure adjudications into the H7 sensitivity input.

Steps:
1. Merge the eight staging batch files (reader=sonnet_high, rubric v1).
2. For each evidence quote, locate it in the blinded packet text and fill exact
   Python-unicode start/end offsets (exact match, then whitespace-normalized
   fallback). Unlocated quotes are recorded with null offsets and counted.
3. De-blind via disclosure_sample_key.json (blind_id -> source_id/model/condition).
4. Emit disclosure_exclusions.json for analyze_h7.py:
     confirmed             = finally_adopted is True
     confirmed_or_uncertain= finally_adopted in {True, None} or ambiguous_disclosure True
   These are the traces whose visible reasoning is (confirmed / possibly) a
   donation-aware adopted choice; analyze_h7 recomputes the contrast without them.

Reader files stay blinded-format; de-blinding happens only here, in the compiler.
No model calls. Deterministic.
"""
import json, re, hashlib, pathlib, sys

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE / "outputs"
BLIND = OUT / "disclosure_blind"
STAGE = OUT / "disclosure_staging"
KEY = OUT / "disclosure_sample_key.json"

BOOL_FIELDS = ["prospective_promise", "retrospective_denial", "considered_rejected",
               "finally_adopted", "explicit_disclosure", "ambiguous_disclosure"]

def norm_ws(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()

def locate(text: str, quote: str):
    """Return (start, end, method) indexing into `text`, or (None, None, 'unlocated')."""
    if not quote:
        return None, None, "empty"
    i = text.find(quote)
    if i >= 0:
        return i, i + len(quote), "exact"
    # whitespace-normalized fallback: match on collapsed whitespace, map back approximately
    nt, nq = norm_ws(text), norm_ws(quote)
    j = nt.find(nq)
    if j >= 0:
        # best-effort: locate the first ~20 non-space chars of the quote in raw text
        head = quote.strip()[:24]
        k = text.find(head)
        if k >= 0:
            return k, k + len(quote), "normalized_head"
        return None, None, "normalized_only"
    return None, None, "unlocated"

def main():
    key = json.loads(KEY.read_text())
    by_blind = {k["blind_id"]: k for k in key}

    cases = {}
    for bf in sorted(STAGE.glob("batch*.json")):
        payload = json.loads(bf.read_text())
        assert payload.get("reader") == "sonnet_high", f"{bf}: unexpected reader"
        assert payload.get("rubric_version") == 1, f"{bf}: unexpected rubric"
        for c in payload["cases"]:
            bid = c["blind_id"]
            if bid in cases:
                sys.exit(f"duplicate blind_id {bid} across batches")
            cases[bid] = c

    expected = set(by_blind)
    got = set(cases)
    missing, extra = expected - got, got - expected
    if missing:
        print(f"WARNING: missing adjudications for {sorted(missing)}")
    if extra:
        sys.exit(f"adjudications for unknown blind_ids: {sorted(extra)}")

    unlocated = 0
    reader_cases, deblinded = [], []
    for bid in sorted(cases, key=lambda b: int(b[1:])):
        c = cases[bid]
        text = (BLIND / f"{bid}.txt").read_text(encoding="utf-8")
        # sha check vs original reasoning (informational; blinded file may differ slightly)
        meta = by_blind[bid]
        sha_match = hashlib.sha256(text.encode("utf-8")).hexdigest() == meta.get("reasoning_sha256")
        ev_out = []
        for e in c.get("evidence", []):
            s, en, method = locate(text, e.get("quote", ""))
            if method in ("unlocated", "normalized_only", "empty"):
                unlocated += 1
            ev_out.append({"field": e.get("field"), "start": s, "end": en,
                           "quote": e.get("quote", ""), "locate_method": method})
        norm = {k: c.get(k) for k in BOOL_FIELDS}
        base = {"blind_id": bid, **norm,
                "final_reasoning_number": c.get("final_reasoning_number"),
                "rationale": c.get("rationale", ""), "evidence": ev_out,
                "full_text_read": c.get("full_text_read", False),
                "blinded_sha_matches_source": sha_match}
        reader_cases.append(base)
        deblinded.append({**base, "source_id": meta["source_id"], "trace_id": meta.get("trace_id"),
                          "model_dir": meta["model_dir"], "condition": meta["condition"]})

    (OUT / "disclosure_reader_sonnet.json").write_text(json.dumps(
        {"reader": "sonnet_high", "rubric_version": 1, "n_cases": len(reader_cases),
         "cases": reader_cases}, indent=2))
    (OUT / "disclosure_adjudication_deblinded.json").write_text(json.dumps(
        {"reader": "sonnet_high", "n_cases": len(deblinded), "cases": deblinded}, indent=2))

    confirmed = sorted({d["source_id"] for d in deblinded if d["finally_adopted"] is True})
    cou = sorted({d["source_id"] for d in deblinded
                  if d["finally_adopted"] is True or d["finally_adopted"] is None
                  or d["ambiguous_disclosure"] is True})
    (OUT / "disclosure_exclusions.json").write_text(json.dumps(
        {"confirmed": confirmed, "confirmed_or_uncertain": cou,
         "definition": {
             "confirmed": "finally_adopted is true",
             "confirmed_or_uncertain": "finally_adopted true/uncertain, or ambiguous_disclosure true"},
         "reader": "sonnet_high"}, indent=2))

    # compact console summary (counts only; no trace text)
    def tally(field):
        t = sum(1 for d in deblinded if d[field] is True)
        f = sum(1 for d in deblinded if d[field] is False)
        n = sum(1 for d in deblinded if d[field] is None)
        return f"T={t} F={f} N={n}"
    print(f"cases compiled: {len(deblinded)}  (missing {sorted(missing) or 'none'})")
    for fld in BOOL_FIELDS:
        print(f"  {fld:22s} {tally(fld)}")
    for cond in ("below_good", "above_good"):
        fa = sum(1 for d in deblinded if d["condition"] == cond and d["finally_adopted"] is True)
        tot = sum(1 for d in deblinded if d["condition"] == cond)
        print(f"  finally_adopted in {cond}: {fa}/{tot}")
    print(f"exclusions: confirmed={len(confirmed)}  confirmed_or_uncertain={len(cou)}")
    print(f"unlocated/normalized-only evidence quotes: {unlocated}")
    sha_bad = [d['blind_id'] for d in reader_cases if not d['blinded_sha_matches_source']]
    print(f"blinded files whose sha != source reasoning: {len(sha_bad)} {sha_bad[:5]}")

if __name__ == "__main__":
    main()
