#!/usr/bin/env python3
"""API coverage report: compares what the tests actually called (results/api_calls.jsonl,
written by conftest.py) with what openapi.yaml promises.
Criteria: endpoint+method, status code, request-body field, role (reader / librarian / anonymous).
Usage (after running pytest):  python api_coverage.py
"""
import json
from pathlib import Path

import yaml

here = Path(__file__).parent
spec = yaml.safe_load(open(here / "openapi.yaml", encoding="utf-8"))
log = here / "results" / "api_calls.jsonl"
if not log.exists():
    raise SystemExit("No results/api_calls.jsonl - run pytest first.")
calls = [json.loads(l) for l in log.read_text(encoding="utf-8").splitlines() if l.strip()]

def schema_of(op):
    s = op.get("requestBody", {}).get("content", {}).get("application/json", {}).get("schema", {})
    return spec["components"]["schemas"].get(s.get("$ref", "").split("/")[-1], {})

ops = []
for path, item in spec["paths"].items():
    for method, op in item.items():
        if method in ("get", "post", "patch", "put", "delete"):
            ops.append((method.upper(), path, op))

seen_ops = {(c["method"], c["path"]) for c in calls}
seen_status = {(c["method"], c["path"], str(c["status"])) for c in calls}
seen_fields = {(c["method"], c["path"], f) for c in calls for f in c["body_fields"]}

lines = ["# API coverage report\n", "| Operation | Called | Status codes hit / documented | Body fields hit / documented | Missing |", "|---|---|---|---|---|"]
tot = {"ops": [0, 0], "status": [0, 0], "fields": [0, 0]}
for method, path, op in ops:
    called = (method, path) in seen_ops
    codes = [str(c) for c in op["responses"]]
    hit = [c for c in codes if (method, path, c) in seen_status]
    fields = list(schema_of(op).get("properties", {}))
    fhit = [f for f in fields if (method, path, f) in seen_fields]
    missing = [f"status {c}" for c in codes if c not in hit] + [f"field {f}" for f in fields if f not in fhit]
    lines.append(f"| {method} {path} | {'yes' if called else 'NO'} | {len(hit)}/{len(codes)} | {len(fhit)}/{len(fields)} | {', '.join(missing) or '-'} |")
    tot["ops"][0] += called; tot["ops"][1] += 1
    tot["status"][0] += len(hit); tot["status"][1] += len(codes)
    tot["fields"][0] += len(fhit); tot["fields"][1] += len(fields)
roles = {c["role"] for c in calls}
pct = lambda a: f"{a[0]}/{a[1]} = {100*a[0]/max(a[1],1):.0f}%"
lines += ["", f"- **Endpoint+method coverage:** {pct(tot['ops'])}",
          f"- **Status-code coverage:** {pct(tot['status'])}",
          f"- **Request-field coverage:** {pct(tot['fields'])}",
          f"- **Roles exercised:** {', '.join(sorted(roles))}",
          f"- **Total API calls made:** {len(calls)}"]
out = here / "results" / "api_coverage.md"
out.write_text("\n".join(lines) + "\n", encoding="utf-8")
print("\n".join(lines))
