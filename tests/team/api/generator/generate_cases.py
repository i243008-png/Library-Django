#!/usr/bin/env python3
"""Test-data generator: reads openapi.yaml and writes EP classes + 3-point BVA values.

Usage (from tests/team/api):
    python generator/generate_cases.py                       # uses openapi.yaml
    python generator/generate_cases.py --spec other.yaml --out results/cases_other.json

Every schema that has an `x-test-target` is turned into test cases. For each property:
  EP  (equivalence partitioning): one value per valid class and one per invalid class.
  BVA (3-point): for every limit L -> L-1, L, L+1  (just below, exactly at, just above).
Each case changes ONE field only (one invalid value per test); the other fields keep their
x-baseline value. Identical (field, value) pairs are merged and counted once.
"""
import argparse
import json
import sys
from pathlib import Path

import yaml

MISSING = "$MISSING"  # the field is left out of the request
NULL = "$NULL"        # the field is sent as JSON null


def case(target, field, technique, cls, value, valid, note):
    return {"target": target, "field": field, "technique": technique, "class": cls,
            "value": value, "valid": valid, "note": note}


def int_cases(target, field, p, required):
    out = []
    lo, hi = p.get("minimum"), p.get("maximum")
    if p.get("x-foreign-key"):
        # ids of other records have no business limit: classes only, no BVA (see test plan)
        out.append(case(target, field, "EP", "valid id of an existing record", p["x-baseline"], True, "real id"))
        out.append(case(target, field, "EP", "invalid: id of a record that does not exist", 999999999, False, "unknown id"))
        if lo is not None:
            out.append(case(target, field, "EP", f"invalid: below minimum {lo}", lo - 1, False, "below minimum"))
            out.append(case(target, field, "EP", "invalid: negative id", -5, False, "negative"))
    else:
        base = p.get("x-baseline", p.get("default", (lo if lo is not None else 0)))
        out.append(case(target, field, "EP", "valid: inside the range", base, True, "typical value"))
        if lo is not None:
            out.append(case(target, field, "EP", "invalid: far below range", lo - 10, False, "below range"))
        if hi is not None:
            out.append(case(target, field, "EP", "invalid: far above range", hi + 10, False, "above range"))
        # 3-point BVA around each limit
        for limit, name in ((lo, "min"), (hi, "max")):
            if limit is None:
                continue
            for delta, label in ((-1, "just below"), (0, "at"), (1, "just above")):
                v = limit + delta
                valid = (lo is None or v >= lo) and (hi is None or v <= hi)
                out.append(case(target, field, "BVA", f"{label} {name} ({limit})", v, valid, f"{label} the {name} limit"))
    out.append(case(target, field, "EP", "invalid: text instead of a number", "abc", False, "wrong type"))
    out.append(case(target, field, "EP", "invalid: decimal number", 14.5, False, "not an integer"))
    if not p.get("nullable"):
        out.append(case(target, field, "EP", "invalid: null", NULL, False, "null not allowed"))
    if required:
        out.append(case(target, field, "EP", "invalid: field missing", MISSING, False, "required"))
    else:
        out.append(case(target, field, "EP", "valid: field missing (default used)", MISSING, True, "optional"))
    return out


def string_cases(target, field, p, required):
    out = []
    if p.get("format") == "date-time":
        out.append(case(target, field, "EP", "valid: ISO date-time", p.get("x-baseline", "$FUTURE_ISO"), True, "well-formed"))
        out.append(case(target, field, "EP", "invalid: not a date", "not-a-date", False, "malformed"))
        out.append(case(target, field, "EP", "invalid: impossible date", "2026-13-45T00:00:00Z", False, "month 13"))
        out.append(case(target, field, "EP", "invalid: number instead of text", 12345, False, "wrong type"))
    else:
        lo, hi = p.get("minLength"), p.get("maxLength")
        out.append(case(target, field, "EP", "valid: typical text", "x" * 10, True, "typical"))
        for limit, name in ((lo, "min"), (hi, "max")):
            if limit is None:
                continue
            for delta, label in ((-1, "just below"), (0, "at"), (1, "just above")):
                n = limit + delta
                if n < 0:
                    continue
                valid = (lo is None or n >= lo) and (hi is None or n <= hi)
                out.append(case(target, field, "BVA", f"{label} {name} length ({limit})", "x" * n, valid, f"length {n}"))
        out.append(case(target, field, "EP", "invalid: number instead of text", 12345, False, "wrong type"))
    if p.get("nullable"):
        out.append(case(target, field, "EP", "valid: null", NULL, True, "nullable"))
    else:
        out.append(case(target, field, "EP", "invalid: null", NULL, False, "null not allowed"))
    if required:
        out.append(case(target, field, "EP", "invalid: field missing", MISSING, False, "required"))
    else:
        out.append(case(target, field, "EP", "valid: field missing", MISSING, True, "optional"))
    return out


def generate(spec):
    result = {}
    for name, schema in spec["components"]["schemas"].items():
        target = schema.get("x-test-target")
        if not target:
            continue
        required = set(schema.get("required", []))
        cases = []
        for field, p in schema["properties"].items():
            kind = p.get("type")
            if kind == "integer":
                cases += int_cases(target, field, p, field in required)
            elif kind == "string":
                cases += string_cases(target, field, p, field in required)
        # merge identical (field, value) pairs: one executable case, both techniques named
        merged = {}
        for c in cases:
            key = (c["field"], json.dumps(c["value"], sort_keys=True))
            if key in merged:
                tech = set(merged[key]["technique"].split("+")) | {c["technique"]}
                merged[key]["technique"] = "+".join(sorted(tech))
            else:
                merged[key] = dict(c)
        final = list(merged.values())
        for i, c in enumerate(final, 1):
            c["id"] = f"{target}-{i:02d}"
            c["expect_status"] = schema.get("x-success-status") if c["valid"] else 400
        result[target] = {
            "schema": name,
            "success_status": schema.get("x-success-status"),
            "baseline": {f: p.get("x-baseline") for f, p in schema["properties"].items()
                         if p.get("x-baseline") is not None},
            "required": sorted(required),
            "cases": final,
        }
    return result


def write_markdown(result, path):
    lines = ["# Generated test cases (EP + 3-point BVA)\n"]
    total = 0
    for target, block in result.items():
        lines.append(f"\n## {target}  (schema {block['schema']}, {len(block['cases'])} cases)\n")
        lines.append("| ID | Field | Technique | Class | Value | Expected |")
        lines.append("|---|---|---|---|---|---|")
        for c in block["cases"]:
            val = str(c["value"])
            val = (val[:20] + "...(len %d)" % len(val)) if len(val) > 24 else val
            exp = "accept (%s)" % c["expect_status"] if c["valid"] else "reject 400"
            lines.append(f"| {c['id']} | {c['field']} | {c['technique']} | {c['class']} | `{val}` | {exp} |")
        total += len(block["cases"])
    lines.append(f"\n**Total cases: {total}**")
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")
    return total


def main():
    here = Path(__file__).resolve().parent.parent
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", default=str(here / "openapi.yaml"))
    ap.add_argument("--out", default=str(here / "results" / "cases.json"))
    args = ap.parse_args()
    spec = yaml.safe_load(open(args.spec, encoding="utf-8"))
    result = generate(spec)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    total = write_markdown(result, out.with_suffix(".md"))
    print(f"Wrote {out} and {out.with_suffix('.md')}  ({total} cases)")
    for t, b in result.items():
        v = sum(1 for c in b["cases"] if c["valid"])
        print(f"  {t:18} {len(b['cases']):3} cases  ({v} valid, {len(b['cases']) - v} invalid)")


if __name__ == "__main__":
    sys.exit(main())
