#!/usr/bin/env python3
"""GQM metrics for the weekly report. Reads traceability.csv, defects.csv and the pytest result
counts you pass in.   Usage: python gqm_metrics.py --executed 69 --passed 60
Goal: know whether API testing is complete and effective.
  Q1 Are all requirements tested?        M1 requirements coverage = reqs with a Passed/Failed test / total reqs
  Q2 How buggy is the area?              M2 defect density = defects / executed test cases x 100
  Q3 Is fixing reliable?                 M3 reopen rate = reopened defects / fixed-or-closed defects
"""
import argparse, csv
from pathlib import Path
ap = argparse.ArgumentParser(); ap.add_argument("--executed", type=int, required=True); ap.add_argument("--passed", type=int, default=0)
a = ap.parse_args(); here = Path(__file__).parent
reqs = list(csv.DictReader(open(here / "traceability.csv", encoding="utf-8")))
defects = list(csv.DictReader(open(here / "defects.csv", encoding="utf-8")))
covered = sum(1 for r in reqs if r["status"].strip().lower() in ("passed", "failed"))
fixed = [d for d in defects if d["status"].strip().lower() in ("fixed", "verified", "closed", "reopened")]
reopened = [d for d in defects if d["reopened"].strip().lower() == "yes"]
print(f"M1 requirements coverage : {covered}/{len(reqs)} = {100*covered/max(len(reqs),1):.0f}%")
print(f"M2 defect density        : {len(defects)} defects / {a.executed} tests x 100 = {100*len(defects)/max(a.executed,1):.1f} per 100 tests")
print(f"M3 reopen rate           : {len(reopened)}/{len(fixed)} = {100*len(reopened)/max(len(fixed),1):.0f}%" if fixed else "M3 reopen rate           : no fixed defects yet")
print(f"Pass rate                : {a.passed}/{a.executed} = {100*a.passed/max(a.executed,1):.0f}%")
