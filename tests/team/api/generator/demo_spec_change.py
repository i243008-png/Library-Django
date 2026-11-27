#!/usr/bin/env python3
"""Shows the effect of changing two constraints in the spec (needed for the viva).
Change 1: IssueRequest.days maximum 30 -> 21.   Change 2: IssueRequest.days minimum 1 -> 3.
Run from tests/team/api:  python generator/demo_spec_change.py
"""
import copy, json, sys
from pathlib import Path
import yaml
sys.path.insert(0, str(Path(__file__).parent))
from generate_cases import generate

here = Path(__file__).resolve().parent.parent
spec = yaml.safe_load(open(here / "openapi.yaml", encoding="utf-8"))
changed = copy.deepcopy(spec)
d = changed["components"]["schemas"]["IssueRequest"]["properties"]["days"]
d["maximum"], d["minimum"] = 21, 3
before, after = generate(spec)["issue_reservation"]["cases"], generate(changed)["issue_reservation"]["cases"]
show = lambda cs: {(c["field"], json.dumps(c["value"])): c for c in cs}
b, a = show(before), show(after)
out = ["# Effect of changing days: max 30 -> 21 and min 1 -> 3\n",
       "| Value | Before | After |", "|---|---|---|"]
for key in sorted(set(b) | set(a), key=lambda k: (str(type(json.loads(k[1]))), str(json.loads(k[1])))):
    verdict = lambda c: "-" if c is None else ("accept" if c["valid"] else "reject")
    flag = "" if verdict(b.get(key)) == verdict(a.get(key)) else "  <-- CHANGED"
    out.append(f"| {key[1]} | {verdict(b.get(key))} | {verdict(a.get(key))}{flag} |")
text = "\n".join(out)
(here / "results" / "spec_change_effect.md").write_text(text + "\n", encoding="utf-8")
json.dump(generate(changed), open(here / "results" / "cases_changed.json", "w"), indent=2)
print(text)
