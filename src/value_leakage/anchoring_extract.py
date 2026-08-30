"""Deterministic, blinded extraction for the phase-1 anchoring analysis.

This module deliberately reads only the visible ``content`` field from each
response row.  It does not use the prompt, condition, threshold, model,
provider, or reasoning fields to parse an answer.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Iterable


PARSER_VERSION = "anchoring_extract.v3"
EXPECTED_ROWS = 400
PILOT_END_EXCLUSIVE = 5
REGRESSION_EXPECTED = {
    "b_1a600fe01fb065f03f09": Decimal("30000000"),
    "b_52d8357f304831220f21": Decimal("70000000"),
    "b_f079ec976629336976f5": Decimal("30000000"),
    "b_fadbb6189cef36095995": Decimal("29000000"),
    "b_fc15e356ad225555c70b": Decimal("77400000"),
}

BLINDED_FIELDS = (
    "blinded_id",
    "extracted_estimate",
    "parser_status",
    "parser_rule",
    "answer_excerpt",
)
AUDIT_ALL_FIELDS = (
    "blinded_id",
    "extracted_estimate",
    "parser_status",
    "parser_rule",
    "visible_content",
)
KEY_FIELDS = (
    "blinded_id",
    "source_file",
    "row_i",
    "split",
    "model",
    "condition",
    "anchor",
    "provider",
)

_BASE_NUMBER = r"(?:\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?|\.\d+)"
_NUMBER_RE = re.compile(
    rf"(?<![\w.])(?P<base>{_BASE_NUMBER})"
    rf"(?:(?P<e>[eE][+-]?\d+)|\s*[×x]\s*10\s*(?:\^|\*\*)\s*(?P<p>[+-]?\d+))?"
    rf"(?:\s*(?P<scale>million|billion|m|bn|b))?(?![\w.,])",
    re.IGNORECASE,
)
_BOX_RE = re.compile(r"\\(?:boxed|fbox)\s*\{([^{}]*)\}", re.IGNORECASE)
_FINAL_LABEL_RE = re.compile(
    r"(?ix)\b(?:"
    r"final\s+(?:answer|estimate|number)"
    r"|my\s+(?:(?:best|single|most\s+accurate)\s+)*point\s+estimate"
    r"|(?:best\s+single|single)\s+point\s+estimate"
    r"|point\s+estimate(?=\s*(?:\*{0,2}\s*)?(?:is\b|:|$))"
    r"|single\s+estimate(?=\s*(?:\*{0,2}\s*)?(?:is\b|:|$))"
    r"|my\s+estimate(?=\s*(?:\*{0,2}\s*)?(?:is\b|:|$))"
    r"|best\s+estimate(?=\s*(?:\*{0,2}\s*)?(?:is\b|:|$))"
    r"|(?:i|we)\s+(?:would\s+)?estimate(?=\s*(?:that\s+there\s+are\s+)?(?:about|approximately|roughly|around)?\s*\d)"
    r"|(?:i|we)(?:'ll|\s+will)?\s+(?:settle|commit|go)\s+(?:with|on)"
    r"|answer(?=\s*(?:\*{0,2}\s*)?(?:is\b|:))"
    r")\b"
)
_TERMINAL_RESULT_LABEL_RE = re.compile(
    r"(?ix)^\s*(?:\#{1,6}\s*)?(?:\d+\.\s*)?(?:\*{0,2})?"
    r"(?:step\s+\d+\s*:\s*)?(?:final\s+)?(?:calculation|result)"
    r"(?:\*{0,2})?\s*:?\s*(?P<rest>.*)$"
)
_RANGE_RE = re.compile(
    rf"(?ix)(?:"
    rf"\bbetween\s+{_BASE_NUMBER}(?:\s*(?:million|billion|m|bn|b))?\s+and\s+"
    rf"{_BASE_NUMBER}(?:\s*(?:million|billion|m|bn|b))?"
    rf"|\bfrom\s+{_BASE_NUMBER}(?:\s*(?:million|billion|m|bn|b))?\s+to\s+"
    rf"{_BASE_NUMBER}(?:\s*(?:million|billion|m|bn|b))?"
    rf"|{_BASE_NUMBER}(?:\s*(?:million|billion|m|bn|b))?\s*[-–—]\s*"
    rf"{_BASE_NUMBER}(?:\s*(?:million|billion|m|bn|b))?"
    rf"|{_BASE_NUMBER}(?:\s*(?:million|billion|m|bn|b))?\s+(?:to|or)\s+"
    rf"{_BASE_NUMBER}(?:\s*(?:million|billion|m|bn|b))?"
    r")"
)


@dataclass(frozen=True)
class Candidate:
    value: Decimal
    start: int
    end: int
    rule: str


@dataclass(frozen=True)
class Extraction:
    estimate: Decimal | None
    status: str
    rule: str
    excerpt: str


def _normalise_content(content: str) -> str:
    text = (
        content.replace("\u00a0", " ")
        .replace("\u202f", " ")
        .replace("\u2011", "-")
        .replace("\\,", "")
        .replace("{,}", "")
    )
    # Models sometimes use spaces as thousands separators. Collapse only
    # separators followed by an exact three-digit group.
    while re.search(r"(?<=\d)\s(?=\d{3}(?:\D|$))", text):
        text = re.sub(r"(?<=\d)\s(?=\d{3}(?:\D|$))", "", text)
    return text


def _decimal_from_match(match: re.Match[str]) -> Decimal:
    base = Decimal(match.group("base").replace(",", ""))
    exponent = match.group("e")
    power = match.group("p")
    if exponent is not None:
        base *= Decimal(10) ** int(exponent)
    elif power is not None:
        base *= Decimal(10) ** int(power)
    scale = (match.group("scale") or "").lower()
    if scale in {"m", "million"}:
        base *= Decimal(1_000_000)
    elif scale in {"b", "bn", "billion"}:
        base *= Decimal(1_000_000_000)
    if base < 0:
        raise InvalidOperation("negative estimates are not accepted")
    return base


def _number_candidates(text: str, offset: int = 0) -> list[Candidate]:
    candidates: list[Candidate] = []
    for match in _NUMBER_RE.finditer(text):
        try:
            value = _decimal_from_match(match)
        except (InvalidOperation, ValueError):
            continue
        candidates.append(
            Candidate(
                value=value,
                start=offset + match.start(),
                end=offset + match.end(),
                rule="number"
                + ("_scientific" if match.group("e") or match.group("p") else "")
                + ("_shorthand" if match.group("scale") else ""),
            )
        )
    return candidates


def _clause_after_marker(text: str, marker_end: int) -> tuple[str, int]:
    """Return a bounded visible clause after a final marker.

    A newline is retained immediately after a label (for ``Final Answer:\n``),
    but later lines are not searched.  This prevents an answer label from
    accidentally absorbing unrelated calculations earlier in the response.
    """

    tail = text[marker_end : marker_end + 320]
    newline = tail.find("\n")
    if newline >= 0 and newline > 80:
        tail = tail[:newline]
    elif newline >= 0 and not _number_candidates(tail[:newline]):
        next_newline = tail.find("\n", newline + 1)
        tail = tail[: next_newline if next_newline >= 0 else len(tail)]
    stop_positions = [position for position in (tail.find("."), tail.find("!"), tail.find("?")) if position >= 0]
    if stop_positions:
        tail = tail[: min(stop_positions) + 1]
    return tail, marker_end


def _range_in_associated_clause(clause: str, candidates: list[Candidate]) -> bool:
    """Reject only a range/alternative that contains the first answer number."""

    if not candidates:
        return False
    first = candidates[0]
    first_start = candidates[0].start
    for range_match in _RANGE_RE.finditer(clause):
        if range_match.start() <= first_start < range_match.end():
            return True
    if len(candidates) > 1:
        between = clause[first.end : candidates[1].start]
        if re.search(r"(?i)\b(?:or|alternatively|perhaps|possibly|maybe)\b", between):
            return True
    return False


def _nonempty_lines(text: str) -> list[tuple[str, int]]:
    lines: list[tuple[str, int]] = []
    offset = 0
    for raw_line in text.splitlines(keepends=True):
        line = raw_line.rstrip("\r\n")
        if line.strip():
            lines.append((line, offset))
        offset += len(raw_line)
    if not lines and text.strip():
        lines.append((text, 0))
    return lines


def _standalone_line_candidate(line: str, offset: int, rule: str) -> Candidate | None:
    """Return one number only when the line is structurally an answer line."""

    if _RANGE_RE.search(line):
        return None
    candidates = _number_candidates(line, offset)
    if len(candidates) != 1:
        return None
    chosen = candidates[0]
    local_start = chosen.start - offset
    local_end = chosen.end - offset
    remainder = line[:local_start] + line[local_end:]
    remainder = re.sub(r"(?i)\\(?:boxed|fbox)\s*", "", remainder)
    remainder = re.sub(
        r"(?i)\b(?:approximately|approx|about|total|black|dark|spots?|patches?)\b",
        "",
        remainder,
    )
    remainder = re.sub(r"[\s#>*_$~≈:;,.!()\[\]{}\\]+", "", remainder)
    if remainder:
        return None
    return Candidate(chosen.value, chosen.start, chosen.end, f"{rule}_{chosen.rule}")


def _is_intermediate_quantity(line: str, candidate: Candidate, offset: int) -> bool:
    local_start = candidate.start - offset
    local_end = candidate.end - offset
    context = line[max(0, local_start - 40) : local_end + 90].casefold()
    if re.search(r"(?:spots?|patches?)\s*(?:/|per)\s*(?:a\s+)?giraffe|each\s+giraffe", context):
        return True
    after = line[local_end : local_end + 45].casefold()
    if re.match(r"\s*(?:living\s+)?(?:giraffes?|individuals?)\b", after):
        return not re.search(r"\b(?:spots?|patches?|total)\b", context)
    return False


def _explicit_label_candidates(text: str) -> tuple[list[Candidate], bool]:
    """Read values on the label line or its immediately following answer line."""

    lines = _nonempty_lines(text)
    candidates: list[Candidate] = []
    saw_unresolved = False
    for line_index, (line, offset) in enumerate(lines):
        for label in _FINAL_LABEL_RE.finditer(line):
            tail = line[label.end() :]
            tail_offset = offset + label.end()
            tail_candidates = _number_candidates(tail, tail_offset)
            if tail_candidates:
                local_candidates = [
                    Candidate(item.value, item.start - tail_offset, item.end - tail_offset, item.rule)
                    for item in tail_candidates
                ]
                if _range_in_associated_clause(tail, local_candidates):
                    saw_unresolved = True
                chosen = tail_candidates[0]
                if not _is_intermediate_quantity(line, chosen, offset):
                    candidates.append(
                        Candidate(
                            chosen.value,
                            chosen.start,
                            chosen.end,
                            f"final_label_same_line_{chosen.rule}",
                        )
                    )
                continue

            if line_index + 1 >= len(lines):
                continue
            next_line, next_offset = lines[line_index + 1]
            if _RANGE_RE.search(next_line):
                saw_unresolved = True
                continue
            chosen = _standalone_line_candidate(
                next_line,
                next_offset,
                "final_label_next_line",
            )
            if chosen is not None and not _is_intermediate_quantity(next_line, chosen, next_offset):
                candidates.append(chosen)
    return candidates, saw_unresolved


def _boxed_candidates(text: str) -> list[Candidate]:
    candidates: list[Candidate] = []
    for box in _BOX_RE.finditer(text):
        inner = box.group(1)
        inner_candidates = _number_candidates(inner, box.start(1))
        if len(inner_candidates) == 1:
            chosen = inner_candidates[0]
            candidates.append(Candidate(chosen.value, chosen.start, chosen.end, f"boxed_{chosen.rule}"))
    return candidates


def _opening_answer_candidate(text: str) -> Candidate | None:
    lines = _nonempty_lines(text)
    if not lines:
        return None
    line, offset = lines[0]
    return _standalone_line_candidate(line, offset, "opening_answer")


def _equation_rhs_candidate(line: str, offset: int) -> Candidate | None:
    operators = list(re.finditer(r"(?:=|≈|\\approx|\\simeq|→)", line))
    if not operators:
        return _standalone_line_candidate(line, offset, "terminal_result")
    rhs_start = operators[-1].end()
    rhs = line[rhs_start:]
    if _RANGE_RE.search(rhs):
        return None
    rhs_candidates = _number_candidates(rhs, offset + rhs_start)
    if len(rhs_candidates) != 1:
        return None
    chosen = rhs_candidates[0]
    return Candidate(chosen.value, chosen.start, chosen.end, f"terminal_result_{chosen.rule}")


def _terminal_result_candidate(text: str) -> Candidate | None:
    """Read one uniquely labeled calculation/result in the terminal half."""

    lines = _nonempty_lines(text)
    labels: list[tuple[int, re.Match[str]]] = []
    for line_index, (line, _) in enumerate(lines):
        match = _TERMINAL_RESULT_LABEL_RE.match(line)
        if match is not None:
            labels.append((line_index, match))
    if len(labels) != 1:
        return None
    line_index, label = labels[0]
    line, offset = lines[line_index]
    if offset < len(text) * 0.45:
        return None
    rest = label.group("rest")
    if rest.strip():
        rest_offset = offset + label.start("rest")
        return _equation_rhs_candidate(rest, rest_offset)
    if line_index + 1 >= len(lines):
        return None
    next_line, next_offset = lines[line_index + 1]
    return _equation_rhs_candidate(next_line, next_offset)


def _format_decimal(value: Decimal) -> str:
    rendered = format(value, "f")
    if "." in rendered:
        rendered = rendered.rstrip("0").rstrip(".")
    return rendered or "0"


def _excerpt(text: str, candidate: Candidate | None, forbidden_tokens: Iterable[str]) -> str:
    if candidate is None:
        return ""
    start = max(0, candidate.start - 90)
    end = min(len(text), candidate.end + 110)
    excerpt = re.sub(r"\s+", " ", text[start:end]).strip()
    for token in sorted(set(forbidden_tokens), key=len, reverse=True):
        if token:
            excerpt = re.sub(re.escape(token), "[redacted]", excerpt, flags=re.IGNORECASE)
    excerpt = re.sub(r"\b(?:group\s+[ab]|neutral_boundary|irrelevant_number)\b", "[redacted]", excerpt, flags=re.IGNORECASE)
    return excerpt


def parse_content(content: Any, forbidden_tokens: Iterable[str] = ()) -> Extraction:
    """Parse one visible response content string without metadata."""

    if not isinstance(content, str) or not content.strip():
        return Extraction(None, "missing", "missing_content", "")
    text = _normalise_content(content)
    label_candidates, label_unresolved = _explicit_label_candidates(text)
    opening_candidate = _opening_answer_candidate(text)
    primary_candidates = list(label_candidates)
    if opening_candidate is not None:
        primary_candidates.append(opening_candidate)

    if primary_candidates:
        candidates = primary_candidates
        saw_range = label_unresolved
    elif label_unresolved:
        candidates = []
        saw_range = True
    else:
        boxed_candidates = _boxed_candidates(text)
        if boxed_candidates:
            candidates = boxed_candidates
        else:
            terminal_candidate = _terminal_result_candidate(text)
            candidates = [terminal_candidate] if terminal_candidate is not None else []
        saw_range = False

    values = {candidate.value for candidate in candidates}
    if saw_range:
        candidate = candidates[-1] if candidates else None
        return Extraction(None, "ambiguous", "unresolved_range", _excerpt(text, candidate, forbidden_tokens))
    if len(values) > 1:
        return Extraction(None, "ambiguous", "conflicting_final_candidates", _excerpt(text, candidates[-1], forbidden_tokens))
    if not candidates:
        return Extraction(None, "ambiguous", "no_single_final", "")

    candidate = candidates[-1]
    return Extraction(candidate.value, "clear", candidate.rule, _excerpt(text, candidate, forbidden_tokens))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _blinded_id(source_file: str, row_i: int) -> str:
    digest = hashlib.sha256(f"phase1\0{source_file}\0{row_i}".encode()).hexdigest()
    return f"b_{digest[:20]}"


def _read_input(input_dir: Path) -> tuple[list[dict[str, Any]], dict[str, str]]:
    json_files = sorted(path for path in input_dir.rglob("*.json") if path.name != "config.json")
    if not json_files:
        raise AssertionError(f"no response JSON files found under {input_dir}")
    input_hashes: dict[str, str] = {}
    records: list[dict[str, Any]] = []
    seen_source_rows: set[tuple[str, int]] = set()
    for path in json_files:
        relative = path.relative_to(input_dir).as_posix()
        input_hashes[relative] = _sha256(path)
        payload = json.loads(path.read_text())
        rows = payload.get("rows") if isinstance(payload, dict) else None
        if not isinstance(rows, list) or len(rows) != 50:
            raise AssertionError(f"{relative} must contain exactly 50 response rows")
        row_indices = [row.get("i") for row in rows if isinstance(row, dict)]
        if row_indices != list(range(50)):
            raise AssertionError(f"{relative} must contain row indices i=0..49 in order")
        for row in rows:
            row_i = row["i"]
            source_key = (relative, row_i)
            if source_key in seen_source_rows:
                raise AssertionError(f"duplicate source row id: {source_key}")
            seen_source_rows.add(source_key)
            records.append(
                {
                    "source_file": relative,
                    "row": row,
                    "row_i": row_i,
                    "model": payload.get("model"),
                    "condition": payload.get("condition"),
                    "anchor": payload.get("threshold"),
                    "provider": row.get("response_provider"),
                }
            )
    if len(records) != EXPECTED_ROWS or len(seen_source_rows) != EXPECTED_ROWS:
        raise AssertionError(f"expected {EXPECTED_ROWS} unique source rows, found {len(records)}")
    return records, input_hashes


def _metadata_tokens(keys: list[dict[str, Any]]) -> list[str]:
    tokens: set[str] = set()
    for key in keys:
        for field in ("model", "condition", "provider"):
            value = key[field]
            if value is not None:
                tokens.add(str(value))
        anchor = key["anchor"]
        if anchor is not None:
            tokens.add(str(anchor))
            if isinstance(anchor, int):
                tokens.add(f"{anchor:,}")
    return sorted(token for token in tokens if token)


def _assert_split_labels(keys: list[dict[str, Any]]) -> None:
    if len({key["blinded_id"] for key in keys}) != EXPECTED_ROWS:
        raise AssertionError("duplicate blinded ids")
    for key in keys:
        expected = "pilot" if key["row_i"] < PILOT_END_EXCLUSIVE else "holdout"
        if key["split"] != expected:
            raise AssertionError(f"incorrect pilot/holdout label for {key['blinded_id']}")
    if sum(key["split"] == "pilot" for key in keys) != 40:
        raise AssertionError("pilot rows must be exactly 40")
    if sum(key["split"] == "holdout" for key in keys) != 360:
        raise AssertionError("holdout rows must be exactly 360")


def _assert_blinded_rows(rows: list[dict[str, str]], metadata_tokens: Iterable[str]) -> None:
    if not rows:
        raise AssertionError("blinded artifact cannot be empty")
    for row in rows:
        if tuple(row) != BLINDED_FIELDS:
            raise AssertionError("blinded artifact contains an unexpected field")
        if any(field in row for field in ("model", "condition", "anchor", "provider")):
            raise AssertionError("metadata field leaked into blinded artifact")
        excerpt = row["answer_excerpt"].casefold()
        for token in metadata_tokens:
            if token.casefold() in excerpt:
                raise AssertionError(f"metadata token leaked into answer excerpt: {token}")
        if any(name in row["parser_rule"].casefold() for name in ("model", "condition", "anchor", "provider")):
            raise AssertionError("metadata label leaked into parser rule")


def _assert_audit_all_rows(rows: list[dict[str, str]]) -> None:
    if any(tuple(row) != AUDIT_ALL_FIELDS for row in rows):
        raise AssertionError("full audit packet contains an unexpected field")
    ids = [row["blinded_id"] for row in rows]
    if len(ids) != EXPECTED_ROWS or len(set(ids)) != EXPECTED_ROWS:
        raise AssertionError("full audit packet must contain 400 unique ids")
    forbidden_columns = {"model", "condition", "anchor", "provider", "source_file", "row_i", "reasoning"}
    if forbidden_columns.intersection(rows[0]):
        raise AssertionError("metadata column leaked into full audit packet")


def _write_csv(path: Path, fields: tuple[str, ...], rows: Iterable[dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="raise")
        writer.writeheader()
        writer.writerows(rows)


def build_artifacts(
    input_dir: Path,
    output_dir: Path,
    plan_path: Path,
) -> dict[str, Any]:
    records, input_hashes = _read_input(input_dir)
    plan_hash = _sha256(plan_path)

    keys: list[dict[str, Any]] = []
    record_ids: list[str] = []
    for record in records:
        source_file = record["source_file"]
        row_i = record["row_i"]
        blinded_id = _blinded_id(source_file, row_i)
        record_ids.append(blinded_id)
        keys.append(
            {
                "blinded_id": blinded_id,
                "source_file": source_file,
                "row_i": row_i,
                "split": "pilot" if row_i < PILOT_END_EXCLUSIVE else "holdout",
                "model": record["model"],
                "condition": record["condition"],
                "anchor": record["anchor"],
                "provider": record["provider"],
            }
        )

    _assert_split_labels(keys)
    metadata_tokens = _metadata_tokens(keys)
    blinded_rows: list[dict[str, str]] = []
    visible_content_by_id: dict[str, str] = {}
    for record, blinded_id in zip(records, record_ids, strict=True):
        extraction = parse_content(record["row"].get("content"), metadata_tokens)
        visible_content_by_id[blinded_id] = record["row"].get("content") if isinstance(record["row"].get("content"), str) else ""
        blinded_rows.append(
            {
                "blinded_id": blinded_id,
                "extracted_estimate": "" if extraction.estimate is None else _format_decimal(extraction.estimate),
                "parser_status": extraction.status,
                "parser_rule": extraction.rule,
                "answer_excerpt": extraction.excerpt,
            }
        )

    _assert_blinded_rows(blinded_rows, metadata_tokens)

    by_id = {row["blinded_id"]: row for row in blinded_rows}
    for blinded_id, expected in REGRESSION_EXPECTED.items():
        row = by_id.get(blinded_id)
        if row is None or row["parser_status"] != "clear":
            raise AssertionError(f"v3 regression row was not clear: {blinded_id}")
        if Decimal(row["extracted_estimate"]) != expected:
            raise AssertionError(
                f"v3 regression mismatch for {blinded_id}: "
                f"{row['extracted_estimate']} != {expected}"
            )

    audit_rows = [
        {
            "blinded_id": by_id[blinded_id]["blinded_id"],
            "extracted_estimate": by_id[blinded_id]["extracted_estimate"],
            "parser_status": by_id[blinded_id]["parser_status"],
            "parser_rule": by_id[blinded_id]["parser_rule"],
            "visible_content": visible_content_by_id[blinded_id],
        }
        for blinded_id in sorted(by_id)
    ]
    _assert_audit_all_rows(audit_rows)

    output_dir.mkdir(parents=True, exist_ok=True)
    _write_csv(output_dir / "blinded_extractions.csv", BLINDED_FIELDS, blinded_rows)
    _write_csv(output_dir / "audit_all.csv", AUDIT_ALL_FIELDS, audit_rows)
    _write_csv(output_dir / "extraction_key.csv", KEY_FIELDS, keys)

    status_counts: dict[str, int] = {}
    parser_rule_counts: dict[str, int] = {}
    for row in blinded_rows:
        status_counts[row["parser_status"]] = status_counts.get(row["parser_status"], 0) + 1
        parser_rule_counts[row["parser_rule"]] = parser_rule_counts.get(row["parser_rule"], 0) + 1
    artifact_paths = {
        "blinded_extractions.csv": output_dir / "blinded_extractions.csv",
        "extraction_key.csv": output_dir / "extraction_key.csv",
        "audit_all.csv": output_dir / "audit_all.csv",
    }
    manifest = {
        "parser_version": PARSER_VERSION,
        "plan_sha256": plan_hash,
        "input_file_hashes": input_hashes,
        "input_row_count": len(records),
        "status_counts": dict(sorted(status_counts.items())),
        "parser_rule_counts": dict(sorted(parser_rule_counts.items())),
        "artifact_schemas": {
            "blinded_extractions.csv": list(BLINDED_FIELDS),
            "extraction_key.csv": list(KEY_FIELDS),
            "audit_all.csv": list(AUDIT_ALL_FIELDS),
        },
        "artifact_row_counts": {
            "blinded_extractions.csv": len(blinded_rows),
            "extraction_key.csv": len(keys),
            "audit_all.csv": len(audit_rows),
        },
        "artifact_sha256": {name: _sha256(path) for name, path in artifact_paths.items()},
        "parser_rules": {
            "source": "visible response content only",
            "reasoning_field": "never read",
            "accepted": "one nonnegative final answer, including zero",
            "numeric_formats": ["commas", "scientific notation", "million shorthand", "billion shorthand"],
            "ambiguous": ["unresolved ranges", "conflicting final candidates", "no single final"],
            "final_markers": [
                "final answer/estimate/number",
                "point estimate",
                "single estimate",
                "my estimate is",
                "best estimate is",
                "answer is",
                "I estimate",
                "I settle/commit/go with",
            ],
            "final_candidate_precedence": [
                "explicit final marker, first associated number",
                "opening standalone numeric answer",
                "boxed value",
                "uniquely labeled terminal calculation/result",
            ],
        },
        "audit": {
            "scope": "all 400 rows, blinded",
            "audit_row_count": len(audit_rows),
        },
        "scope": "phase-1 extraction and blinded audit packet only; no condition effects or summary statistics",
    }
    (output_dir / "extraction_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=Path("runs/anchoring_pilot_qwen_pair"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("analysis/hyp1_threshold_anchoring"),
    )
    parser.add_argument(
        "--plan-path",
        type=Path,
        default=Path("analysis/hyp1_threshold_anchoring/analysis_plan.md"),
    )
    args = parser.parse_args()
    manifest = build_artifacts(args.input_dir, args.output_dir, args.plan_path)
    print(f"plan_sha256={manifest['plan_sha256']}")
    print("status_counts=" + json.dumps(manifest["status_counts"], sort_keys=True))


if __name__ == "__main__":
    main()
