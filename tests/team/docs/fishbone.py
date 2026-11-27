#!/usr/bin/env python3
"""Draw a fishbone (Ishikawa) diagram from an RCA json file.  Usage: python fishbone.py rca_1.json"""
import json, sys
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

src = Path(sys.argv[1] if len(sys.argv) > 1 else "rca_example.json")
d = json.loads(src.read_text(encoding="utf-8"))
fig, ax = plt.subplots(figsize=(13, 6.5)); ax.axis("off"); ax.set_xlim(0, 13); ax.set_ylim(0, 7)
ax.plot([0.5, 10.5], [3.5, 3.5], color="black", lw=2)
ax.text(10.6, 3.5, d["effect"], va="center", fontsize=11, weight="bold", bbox=dict(boxstyle="round", fc="#ffe9b3"))
cats = list(d["causes"].items())
for i, (cat, items) in enumerate(cats):
    top = i % 2 == 0
    x = 1.5 + (i // 2) * 3.2
    y0, y1 = (6.2, 3.5) if top else (0.8, 3.5)
    ax.plot([x, x + 1.2], [y0, y1], color="#444", lw=1.5)
    ax.text(x - 0.1, y0 + (0.25 if top else -0.3), cat, ha="center", weight="bold", fontsize=10)
    for j, it in enumerate(items):
        yy = y0 + (y1 - y0) * (0.25 + 0.2 * j)
        xx = x + (1.2) * (0.25 + 0.2 * j)
        ax.text(xx - 0.15, yy, it, ha="right", va="center", fontsize=7.5)
ax.set_title(d["title"], fontsize=12)
out = src.with_suffix(".png"); fig.savefig(out, dpi=150, bbox_inches="tight"); print("saved", out)
