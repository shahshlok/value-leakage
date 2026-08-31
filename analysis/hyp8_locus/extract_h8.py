"""Offline deterministic extraction for H8 mechanism localization.

The N/S extractor reads ``reasoning`` only.  It never sees the prompt,
condition threshold, visible answer, or outcome while choosing factor values.
Visible Y is joined only after factor extraction and is used solely for the
prespecified validity gate.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RUNS = ROOT / "runs"
H6_OUTCOMES = ROOT / "analysis/hyp6_impartiality/existing_data/outcomes_and_claims.csv"
OUTPUT = HERE / "extractions.csv"

MODELS = (
    "claude-opus-4-7_20260815_042213",
    "deepseek-v4-flash-0731_20260815_030703",
    "deepseek-v4-pro-0813_20260815_030703",
    "glm-5p2_20260815_030703",
    "inkling-small_20260815_192811",
    "inkling_20260815_030703",
    "kimi-k3_20260815_030702",
    "minimax-m3_20260815_030703",
    "qwen3.5-122b-a10b_20260815_030702",
    "qwen3p8-2p4t-a95b_20260815_030703",
)
CONDITIONS = ("baseline", "below_good", "above_good")

PARSER_VERSION = "h8_locus.v1"

NUMBER_PATTERN = (
    r"(?<![\w.])"
    r"(?:\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?)"
    r"(?:\s*(?:[eE][+-]?\d+|[×x]\s*10\s*(?:\^|\*\*)\s*[+-]?\d+))?"
    r"(?:\s*(?:thousand|million|billion|k|m|bn|b))?"
    r"(?![\w.])"
)
NUMBER_RE = re.compile(NUMBER_PATTERN, re.IGNORECASE)
OP_RE = re.compile(r"(?:×|\*|\\cdot|\b[xX]\b)")

POPULATION_WORD_RE = re.compile(
    r"(?i)\b(?:population|giraffes?|individuals?|animals?|living|wild|captive|zoos?)\b"
)
GIRAFFE_UNIT_RE = re.compile(r"(?i)\b(?:giraffes?|individuals?|animals?)\b")
SPOT_WORD_RE = re.compile(r"(?i)\b(?:spots?|patches?)\b")
PER_CONTEXT_RE = re.compile(
    r"(?i)\b(?:per|each|average|avg|mean|weighted|typical|individual|giraffes?)\b"
)
ADOPTION_RE = re.compile(
    r"(?i)\b(?:use|using|used|assume|assuming|adopt|adopted|take|taking|choose|chosen|"
    r"settle|settling|go with|going with|working average|point estimate|best estimate|"
    r"final|overall|population-weighted|weighted average|round(?:ed|ing)? to)\b"
)
SENSITIVITY_RE = re.compile(
    r"(?i)\b(?:if|range|between|low(?:er)?|high(?:er)?|minimum|maximum|scenario|could|"
    r"perhaps|maybe|alternative|sensitivity)\b"
)
AGGREGATE_RE = re.compile(
    r"(?i)\b(?:total|global|worldwide|world|all|overall|weighted|average|living)\b"
)
SPECIES_RE = re.compile(
    r"(?i)\b(?:masai|reticulated|southern|northern|nubian|kordofan|rothschild|"
    r"west african|south african|angolan)\b"
)


@dataclass(frozen=True)
class Number:
    value: float
    start: int
    end: int
    raw: str
    in_range: bool


@dataclass(frozen=True)
class Candidate:
    value: float
    start: int
    end: int
    strength: int
    rule: str
    span: str


@dataclass(frozen=True)
class Pair:
    n: Candidate
    s: Candidate
    operator_start: int
    aggregate_score: int


@dataclass(frozen=True)
class FactorExtraction:
    n: float | None
    s: float | None
    n_confidence: str
    s_confidence: str
    n_rule: str
    s_rule: str
    n_span: str
    s_span: str
    decomposition_other: str


def _normalise(text: str) -> str:
    return (
        text.replace("\u00a0", " ")
        .replace("\u202f", " ")
        .replace("\u2011", "-")
        .replace("\\,", "")
        .replace("{,}", "")
    )


def _parse_number(raw: str) -> float | None:
    compact = raw.strip().lower().replace(",", "")
    compact = re.sub(r"\s+", " ", compact)
    scale = 1.0
    scale_match = re.search(r"(?i)\s*(thousand|million|billion|k|m|bn|b)\s*$", compact)
    if scale_match:
        token = scale_match.group(1).lower()
        scale = {"thousand": 1e3, "k": 1e3, "million": 1e6, "m": 1e6,
                 "billion": 1e9, "bn": 1e9, "b": 1e9}[token]
        compact = compact[: scale_match.start()].strip()
    scientific = re.fullmatch(
        r"(?P<base>\d+(?:\.\d+)?)\s*[×x]\s*10\s*(?:\^|\*\*)\s*(?P<power>[+-]?\d+)",
        compact,
        re.IGNORECASE,
    )
    try:
        if scientific:
            return float(scientific.group("base")) * 10 ** int(scientific.group("power")) * scale
        return float(compact) * scale
    except ValueError:
        return None


def _numbers(text: str) -> list[Number]:
    found: list[Number] = []
    for match in NUMBER_RE.finditer(text):
        value = _parse_number(match.group())
        if value is None or not math.isfinite(value):
            continue
        found.append(Number(
            value=value,
            start=match.start(),
            end=match.end(),
            raw=match.group(),
            in_range=_is_range_endpoint(text, match.start(), match.end()),
        ))
    return found


def _is_range_endpoint(text: str, start: int, end: int) -> bool:
    """Bounded range check; avoids a costly whole-trace composite regex."""
    before = text[max(0, start - 45):start]
    after = text[end:min(len(text), end + 45)]
    if re.search(r"(?i)\b(?:between|from)\s*$", before) and re.match(
        rf"(?i)\s*(?:-|–|—|to|and|or)\s*{NUMBER_PATTERN}", after
    ):
        return True
    if re.search(rf"(?i){NUMBER_PATTERN}\s*(?:-|–|—|to|and|or)\s*$", before):
        return True
    if re.match(rf"(?i)\s*(?:-|–|—|to|and|or)\s*{NUMBER_PATTERN}", after):
        return True
    return False


def _bounded_span(text: str, start: int, end: int, radius: int = 150) -> str:
    left = max(0, start - radius)
    right = min(len(text), end + radius)
    # Prefer full local line; otherwise use the bounded window.
    line_left = text.rfind("\n", left, start)
    line_right = text.find("\n", end, right)
    if line_left >= 0:
        left = line_left + 1
    if line_right >= 0:
        right = line_right
    return re.sub(r"\s+", " ", text[left:right]).strip()


def _local(text: str, number: Number, radius: int = 110) -> str:
    return text[max(0, number.start - radius): min(len(text), number.end + radius)]


def _factor_kind(text: str, number: Number) -> str | None:
    value = number.value
    local = _local(text, number)
    before = text[max(0, number.start - 70):number.start]
    after = text[number.end:min(len(text), number.end + 70)]
    if re.match(r"\s*%", after):
        return None
    if re.match(r"(?i)\s*(?:cm|m|km)(?:\^?2|²)\b", after) or re.match(
        r"(?i)\s*(?:square\s+)?(?:centi|kilo)?met(?:er|re)s?\b", after
    ):
        return None

    followed_by_spots = re.match(r"(?i)\s*(?:dark\s+|black\s+|coat\s+)?(?:spots?|patches?)\b", after)
    followed_by_giraffes = re.match(r"(?i)\s*(?:living\s+|wild\s+|captive\s+)?(?:giraffes?|individuals?|animals?)\b", after)
    if 20 <= value <= 5_000 and re.search(
        r"(?i)\b(?:captive|captivity|zoos?|sanctuar(?:y|ies)|AZA|EEP)\b", local
    ) and not followed_by_spots:
        return None
    area_spot_context = re.search(
        r"(?i)\b(?:spot\s+area|area\s+(?:of|per)\s+(?:a\s+)?spot|spot\s+size|cm[²2]|m[²2]|square)\b",
        local,
    )
    explicit_per_giraffe = re.search(
        r"(?i)\b(?:spots?|patches?)\s*(?:/|per)\s*(?:an?\s+)?(?:giraffe|individual)\b",
        local,
    )
    explicit_average_spots = re.search(
        r"(?i)\b(?:(?:average|avg|mean|weighted)(?:\s+(?:number|count))?(?:\s+of)?\s+(?:dark\s+)?(?:spots?|patches?)|"
        r"(?:spots?|patches?)\s+(?:average|mean))\b",
        local,
    )
    if 20 <= value <= 5_000 and SPOT_WORD_RE.search(local) and (
        followed_by_spots or explicit_per_giraffe or explicit_average_spots
    ) and (not area_spot_context or explicit_per_giraffe):
        return "s"
    if 10_000 <= value <= 1_000_000 and POPULATION_WORD_RE.search(local):
        # A total spot answer often appears beside "all giraffes".  Do not call
        # it population unless population language or a giraffe count unit is
        # locally attached to the number.
        has_population_label = re.search(r"(?i)\bpopulation\b", local)
        has_unit = bool(followed_by_giraffes) or bool(re.search(
            r"(?i)(?:giraffes?|individuals?|animals?)\s*(?:[:=≈~]|of)?\s*$", before
        ))
        if (has_population_label or has_unit) and not followed_by_spots:
            return "n"
    return None


def _strength(text: str, number: Number, kind: str) -> int:
    local = _local(text, number, 90)
    before = text[max(0, number.start - 80):number.start]
    after = text[number.end:min(len(text), number.end + 80)]
    score = 1
    if ADOPTION_RE.search(local):
        score = 4
    elif re.search(r"[:=≈~]\s*$", before) or re.match(r"\s*(?:giraffes?|individuals?|spots?|patches?)\b", after, re.I):
        score = 3
    if number.in_range and not ADOPTION_RE.search(local):
        score = 0
    if re.search(r"(?i)\bif\b", before[-45:]):
        score = min(score, 1)
    elif SENSITIVITY_RE.search(before[-100:]):
        score = min(score, 1)
    if kind == "n" and re.search(r"(?i)\b(?:wild|captive|zoo)\b", local) and not AGGREGATE_RE.search(local):
        score = min(score, 2)
    return score


def _candidate(text: str, number: Number, kind: str, strength: int, rule: str, span: str | None = None) -> Candidate:
    return Candidate(
        value=number.value,
        start=number.start,
        end=number.end,
        strength=strength,
        rule=rule,
        span=span or _bounded_span(text, number.start, number.end),
    )


def _multiplication_pairs(text: str, nums: list[Number]) -> list[Pair]:
    pairs: list[Pair] = []
    for operator in OP_RE.finditer(text):
        # Ignore Markdown emphasis and bullets unless numeric operands flank it.
        before = [n for n in nums if n.end <= operator.start() and operator.start() - n.end <= 90]
        after = [n for n in nums if n.start >= operator.end() and n.start - operator.end() <= 90]
        if not before or not after:
            continue
        left, right = before[-1], after[0]
        between = text[left.end:right.start]
        if "=" in between or "≈" in between or "→" in between:
            continue
        if operator.group() == "*" and (
            "\n" in between
            or operator.start() - left.end > 35
            or right.start - operator.end() > 35
        ):
            # Markdown bullets/emphasis are asterisks too.  A real arithmetic
            # asterisk has nearby operands on the same line.
            continue
        left_kind, right_kind = _factor_kind(text, left), _factor_kind(text, right)
        # Multiplication itself supplies factor semantics when the numeric
        # ranges are disjoint, even if the units are stated elsewhere.
        if left_kind is None:
            left_kind = "n" if 10_000 <= left.value <= 1_000_000 else "s" if 20 <= left.value <= 5_000 else None
        if right_kind is None:
            right_kind = "n" if 10_000 <= right.value <= 1_000_000 else "s" if 20 <= right.value <= 5_000 else None
        if {left_kind, right_kind} != {"n", "s"}:
            continue
        pair_span = _bounded_span(text, left.start, right.end, radius=180)
        n_number, s_number = (left, right) if left_kind == "n" else (right, left)
        aggregate_score = len(AGGREGATE_RE.findall(pair_span))
        pairs.append(Pair(
            n=_candidate(text, n_number, "n", 5, "multiplication_pair", pair_span),
            s=_candidate(text, s_number, "s", 5, "multiplication_pair", pair_span),
            operator_start=operator.start(),
            aggregate_score=aggregate_score,
        ))
    # Operators such as asterisks in Markdown can rediscover the same operands.
    dedup: dict[tuple[int, int, float, float], Pair] = {}
    for pair in pairs:
        dedup[(pair.n.start, pair.s.start, pair.n.value, pair.s.value)] = pair
    return sorted(dedup.values(), key=lambda p: p.operator_start)


def _pair_is_adopted(text: str, pair: Pair, multi_pair: bool) -> bool:
    """Reject counterfactual/sensitivity and subgroup multiplications."""
    start = min(pair.n.start, pair.s.start)
    end = max(pair.n.end, pair.s.end)
    before = text[max(0, start - 110):start]
    local = text[max(0, start - 40):min(len(text), end + 100)]
    if re.search(
        r"(?i)(?:\bif\b|\b(?:upper|lower|minimum|maximum|sensitivity|scenario|suppose)\b)",
        before[-80:],
    ):
        return False
    if multi_pair and pair.n.span.count("=") >= 2:
        # One line containing a sum/list of several products is a component
        # decomposition, not a common N*S multiplication.
        return False
    if multi_pair and re.match(r"(?i)^\s*[*+-]?\s*[NRMS]\s+\d", pair.n.span):
        # Shorthand species-component lines such as ``M 46,000*360``.
        return False
    if multi_pair and SPECIES_RE.search(pair.n.span):
        return False
    if multi_pair and re.search(r"(?i)\b(?:calves?|juveniles?|adults?|wild|captive|zoo)\s*[:(]", pair.n.span):
        return False
    return True


def _decomposition_label(text: str, pairs: list[Pair], chosen: Pair | None) -> str:
    """Label mapped alternatives or final alternatives that could not be mapped."""
    lowered = text.casefold()
    if not lowered.strip():
        return "no_reasoning"
    species = set(m.group().casefold() for m in SPECIES_RE.finditer(text))
    surface = "surface area" in lowered and bool(re.search(
        r"(?i)\b(?:density|per\s+(?:square|m[²2]|cm[²2]))\b", text
    ))
    if chosen is not None:
        vicinity = text[max(0, chosen.operator_start - 1_200):min(len(text), chosen.operator_start + 1_200)]
        if "surface area" in vicinity.casefold():
            return "mapped_surface_area_density"
        if len(species) >= 2 and re.search(r"(?i)\b(?:weighted|species mix|across species)\b", vicinity):
            return "mapped_species_weighted"
        return ""
    final_half = text[len(text) // 2:]
    if surface and "surface area" in final_half.casefold():
        return "surface_area_density_unmapped"
    if len(species) >= 2 and (len(pairs) >= 2 or "weighted" in lowered or "breakdown" in lowered):
        return "species_weighted_or_sum_unmapped"
    if re.search(r"(?i)\b(?:adult|calves?|juveniles?|wild|captive|zoo)\b", final_half) and len(pairs) >= 2:
        return "demographic_or_habitat_sum_unmapped"
    return ""


def _final_repetition_score(nums: list[Number], pair: Pair, text_length: int) -> int:
    """Reward factor pairs that the trace restates after the computation."""
    tail_start = max(0, text_length - 2_000)
    later = [
        n.value for n in nums
        if n.start >= tail_start and n.start not in {pair.n.start, pair.s.start}
    ]
    def count(value: float) -> int:
        return min(3, sum(math.isclose(item, value, rel_tol=1e-10, abs_tol=1e-8) for item in later))
    n_count, s_count = count(pair.n.value), count(pair.s.value)
    final_zone = int(pair.operator_start >= max(0, text_length - 8_000))
    return 3 * int(n_count > 0 and s_count > 0) + n_count + s_count + 3 * final_zone


def _select_text_candidate(candidates: list[Candidate]) -> tuple[Candidate | None, str]:
    candidates = [c for c in candidates if c.strength > 0]
    if not candidates:
        return None, "missing"
    strongest = max(c.strength for c in candidates)
    top = [c for c in candidates if c.strength == strongest]
    chosen = top[-1]
    if strongest >= 4:
        return chosen, "clear"
    distinct = {c.value for c in top}
    if strongest >= 3 and len(distinct) == 1:
        return chosen, "clear"
    return chosen, "ambiguous"


def extract_factors(reasoning: Any) -> FactorExtraction:
    if not isinstance(reasoning, str) or not reasoning.strip():
        return FactorExtraction(None, None, "missing", "missing", "", "", "", "", "no_reasoning")
    text = _normalise(reasoning)
    nums = _numbers(text)
    pairs = _multiplication_pairs(text, nums)

    candidates: dict[str, list[Candidate]] = {"n": [], "s": []}
    for number in nums:
        kind = _factor_kind(text, number)
        if kind is None:
            continue
        candidates[kind].append(_candidate(
            text,
            number,
            kind,
            _strength(text, number, kind),
            f"context_{kind}",
        ))

    # Among multiplications that represent the common N*S decomposition, take
    # the last one.  Species/group component products and counterfactual checks
    # are not adopted common-factor calculations.
    adopted_pairs = [p for p in pairs if _pair_is_adopted(text, p, len(pairs) > 1)]
    species = set(m.group().casefold() for m in SPECIES_RE.finditer(text))
    aggregate_n = [
        c for c in candidates["n"]
        if c.strength >= 3 and re.search(r"(?i)\b(?:total|population|global|worldwide|living)\b", c.span)
    ]
    if len(species) >= 2 and aggregate_n:
        # A species component can itself satisfy the broad N range.  When the
        # trace states a total population, component multiplications well below
        # that total are not the common N*S decomposition.
        reference_n = max(c.value for c in aggregate_n)
        adopted_pairs = [p for p in adopted_pairs if p.n.value >= 0.60 * reference_n]
    chosen_pair = max(
        adopted_pairs,
        key=lambda p: (_final_repetition_score(nums, p, len(text)), p.operator_start),
        default=None,
    )
    other = _decomposition_label(text, pairs, chosen_pair)

    selected: dict[str, Candidate | None] = {"n": None, "s": None}
    confidence: dict[str, str] = {"n": "missing", "s": "missing"}
    if chosen_pair is not None:
        selected.update(n=chosen_pair.n, s=chosen_pair.s)
        confidence.update(n="clear", s="clear")
        # A trace can do a multiplication and then explicitly restate a new
        # adopted N and S without multiplying again.  Override only when both
        # later factor statements are strong, close together, and are not
        # species-component rows.
        later_n = [
            c for c in candidates["n"]
            if c.start > max(chosen_pair.n.end, chosen_pair.s.end)
            and c.strength >= 3 and not SPECIES_RE.search(c.span)
        ]
        later_s = [
            c for c in candidates["s"]
            if c.start > max(chosen_pair.n.end, chosen_pair.s.end)
            and c.strength >= 3 and not SPECIES_RE.search(c.span)
        ]
        later_pairs = [
            (n, s) for n in later_n for s in later_s
            if abs(n.start - s.start) <= 600
            and min(n.start, s.start) >= 0.70 * len(text)
        ]
        if later_pairs:
            n_later, s_later = max(
                later_pairs,
                key=lambda pair: (min(pair[0].start, pair[1].start), -abs(pair[0].start - pair[1].start)),
            )
            selected.update(n=n_later, s=s_later)
    else:
        for kind in ("n", "s"):
            selected[kind], confidence[kind] = _select_text_candidate(candidates[kind])
        if other.endswith("_unmapped"):
            # Values mentioned inside an unresolved alternative decomposition
            # are retained for audit, but never called clear or gated.
            for kind in ("n", "s"):
                confidence[kind] = "missing" if selected[kind] is None else "ambiguous"

    n, s = selected["n"], selected["s"]
    return FactorExtraction(
        n=None if n is None else n.value,
        s=None if s is None else s.value,
        n_confidence=confidence["n"],
        s_confidence=confidence["s"],
        n_rule="" if n is None else n.rule,
        s_rule="" if s is None else s.rule,
        n_span="" if n is None else n.span,
        s_span="" if s is None else s.span,
        decomposition_other=other,
    )


def _load_corrected_y() -> dict[tuple[str, str, int], tuple[float | None, str]]:
    corrected: dict[tuple[str, str, int], tuple[float | None, str]] = {}
    with H6_OUTCOMES.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            raw = row["estimate"].strip()
            value = float(raw) if raw else None
            corrected[(row["model_dir"], row["condition"], int(row["row_i"]))] = (
                value,
                f"h6_{row['answer_source']}",
            )
    if len(corrected) != 1_000:
        raise AssertionError(f"expected 1,000 corrected H6 rows, found {len(corrected)}")
    return corrected


def _local_y(content: Any) -> tuple[float | None, str, str]:
    sys.path.insert(0, str(ROOT / "src"))
    from value_leakage.anchoring_extract import parse_content  # noqa: PLC0415

    extraction = parse_content(content)
    value = None if extraction.estimate is None else float(extraction.estimate)
    return value, f"local_parser_{extraction.rule}", extraction.status


FIELDS = (
    "model", "condition", "row_i", "trace_id",
    "N", "S", "N_confidence", "S_confidence", "N_rule", "S_rule",
    "N_span", "S_span", "decomposition_other",
    "product", "Y", "Y_source", "Y_status", "product_to_Y_ratio", "gate_pass",
)


def extract_all() -> list[dict[str, Any]]:
    corrected = _load_corrected_y()
    rows_out: list[dict[str, Any]] = []
    for model in MODELS:
        model_dir = RUNS / model
        if not model_dir.is_dir():
            raise AssertionError(f"missing model directory: {model_dir}")
        for condition in CONDITIONS:
            payload = json.loads((model_dir / f"{condition}.json").read_text(encoding="utf-8"))
            rows = payload.get("rows")
            if not isinstance(rows, list) or len(rows) != 100:
                raise AssertionError(f"{model}/{condition} must contain 100 rows")
            if [r.get("i") for r in rows] != list(range(100)):
                raise AssertionError(f"{model}/{condition} row keys are not 0..99")
            for row in rows:
                row_i = int(row["i"])
                factors = extract_factors(row.get("reasoning"))
                key = (model, condition, row_i)
                if key in corrected:
                    y, y_source = corrected[key]
                    y_status = "clear" if y is not None else "missing"
                else:
                    y, y_source, y_status = _local_y(row.get("content"))
                product = factors.n * factors.s if factors.n is not None and factors.s is not None else None
                ratio = product / y if product is not None and y is not None and y > 0 else None
                gate = (
                    factors.n_confidence == "clear"
                    and factors.s_confidence == "clear"
                    and product is not None
                    and y is not None
                    and y > 0
                    and (1 / 3) <= ratio <= 3
                )
                rows_out.append({
                    "model": model,
                    "condition": condition,
                    "row_i": row_i,
                    "trace_id": f"{model}|{condition}|{row_i}",
                    "N": factors.n,
                    "S": factors.s,
                    "N_confidence": factors.n_confidence,
                    "S_confidence": factors.s_confidence,
                    "N_rule": factors.n_rule,
                    "S_rule": factors.s_rule,
                    "N_span": factors.n_span,
                    "S_span": factors.s_span,
                    "decomposition_other": factors.decomposition_other,
                    "product": product,
                    "Y": y,
                    "Y_source": y_source,
                    "Y_status": y_status,
                    "product_to_Y_ratio": ratio,
                    "gate_pass": gate,
                })
    if len(rows_out) != 3_000:
        raise AssertionError(f"expected 3,000 extracted rows, found {len(rows_out)}")
    return rows_out


def _render(value: Any) -> Any:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    return value


def write_extractions(rows: Iterable[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, extrasaction="raise")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: _render(row[key]) for key in FIELDS})


def print_pass_rates(rows: list[dict[str, Any]]) -> None:
    print("\nPRESPECIFIED VALIDITY-GATE PASS RATES (before any condition contrast)")
    print("model\tcondition\tpass/n\trate\tN clear\tS clear\tY positive\tdecomp_other")
    for model in MODELS:
        for condition in CONDITIONS:
            cell = [r for r in rows if r["model"] == model and r["condition"] == condition]
            passed = sum(r["gate_pass"] for r in cell)
            n_clear = sum(r["N_confidence"] == "clear" for r in cell)
            s_clear = sum(r["S_confidence"] == "clear" for r in cell)
            y_positive = sum(r["Y"] is not None and r["Y"] > 0 for r in cell)
            other = sum(bool(r["decomposition_other"]) for r in cell)
            print(f"{model}\t{condition}\t{passed}/100\t{passed/100:.1%}\t{n_clear}\t{s_clear}\t{y_positive}\t{other}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    rows = extract_all()
    write_extractions(rows, args.output)
    print(f"parser_version={PARSER_VERSION}")
    print(f"wrote={args.output}")
    print_pass_rates(rows)


if __name__ == "__main__":
    main()
