#!/usr/bin/env python3
"""Pareto chart of defects by category from defects.csv.  Usage: python pareto.py"""
import csv
from collections import Counter
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

here = Path(__file__).parent
rows = list(csv.DictReader(open(here / "defects.csv", encoding="utf-8")))
if not rows:
    raise SystemExit("defects.csv has no rows yet - log real defects first.")
counts = Counter(r["category"] for r in rows).most_common()
names, vals = [c for c, _ in counts], [v for _, v in counts]
total, cum, run = sum(vals), [], 0
for v in vals:
    run += v; cum.append(100 * run / total)
fig, ax = plt.subplots(figsize=(8, 4.5))
ax.bar(names, vals, color="#4a6fa5"); ax.set_ylabel("Defects")
ax2 = ax.twinx(); ax2.plot(names, cum, "o-", color="#c0392b"); ax2.set_ylim(0, 105); ax2.set_ylabel("Cumulative %")
ax.set_title("Defect Pareto by category"); plt.setp(ax.get_xticklabels(), rotation=25, ha="right")
out = here.parent / "api" / "results" / "pareto.png"; out.parent.mkdir(exist_ok=True)
fig.tight_layout(); fig.savefig(out, dpi=150); print("saved", out)
for n, v, c in zip(names, vals, cum): print(f"{n:20} {v:3}  cumulative {c:5.1f}%")
