"""Create the two figures shown in the README.   python src/make_figures.py"""
import collections

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import statistics as st

from analyze import FILES, load

batches = {name: load(path) for name, path in FILES.items()}
labels = ["0", "1", "2", "unrepaired"]
names = ["harmless", "1 pawn edit", "2 pawn edits", "not repaired\n(within 2)"]

# Figure 1: repair-cost distribution per batch
fig, ax = plt.subplots(figsize=(7, 4))
width = 0.25
for i, (bname, rows) in enumerate(batches.items()):
    c = collections.Counter(r["cost"] for r in rows)
    shares = [100 * c[l] / len(rows) for l in labels]
    ax.bar([x + (i - 1) * width for x in range(4)], shares, width,
           label=f"{bname} (n={len(rows)})")
ax.set_xticks(range(4), names)
ax.set_ylabel("% of swaps")
ax.set_title("Knight-to-bishop swaps: repair cost, three independent batches")
ax.legend(frameon=False)
ax.spines[["top", "right"]].set_visible(False)
fig.tight_layout()
fig.savefig("results/repair_cost_distribution.png", dpi=150)

# Figure 2: distribution of evaluation change
damage = [r["damage"] for rows in batches.values() for r in rows]
fig, ax = plt.subplots(figsize=(7, 4))
ax.hist([max(-400, min(400, d)) for d in damage], bins=40, color="#4c72b0")
ax.axvline(0, color="black", lw=1)
ax.axvline(st.median(damage), color="#c44e52", ls="--",
           label=f"median {st.median(damage):+.0f} cp")
ax.axvspan(-30, 30, color="grey", alpha=0.2, label="harmless band (±30 cp)")
ax.set_xlabel("evaluation change after swap, centipawns (clipped at ±400)")
ax.set_ylabel("positions")
ax.set_title(f"Engine evaluation change, n={len(damage)}: the engine tends to prefer the bishop")
ax.legend(frameon=False)
ax.spines[["top", "right"]].set_visible(False)
fig.tight_layout()
fig.savefig("results/evaluation_change_histogram.png", dpi=150)
print("saved figures to results/")
