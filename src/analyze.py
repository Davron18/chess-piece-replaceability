"""
Reproduce every number reported in the README from the CSV files.

  python src/analyze.py

Tests (fixed before batch 3 was run):
  1. Is the repair-cost distribution stable across batches?
  2. Does the engine's bishop preference depend on the bishop configuration?
  3. Do closed and open positions differ?  (permutation test)
  4. Does an offset correction estimated on batches 1+2 work on batch 3?
"""
import collections
import csv
import random
import statistics as st

import chess

import replaceability as rp

FILES = {"batch1": "data/batch1_100.csv", "batch2": "data/batch2_100.csv",
         "batch3": "data/batch3_200.csv"}


def load(path):
    rows, seen = [], set()
    for r in csv.DictReader(open(path)):
        if r["fen"] in seen:               # drop the one duplicate position
            continue
        seen.add(r["fen"])
        r["damage"] = int(r["damage"])
        board = chess.Board(r["fen"])
        r["config"] = rp.bishop_configuration(board, chess.parse_square(r["knight_sq"]))
        rows.append(r)
    return rows


def distribution(rows):
    c = collections.Counter(r["cost"] for r in rows)
    n = len(rows)
    return (f"harmless {c['0'] / n:4.0%}  1 edit {c['1'] / n:4.0%}  "
            f"2 edits {c['2'] / n:4.0%}  unrepaired {c['unrepaired'] / n:4.0%}  (n={n})")


def bootstrap_ci(values, k=5000, seed=1):
    rng = random.Random(seed)
    meds = sorted(st.median(rng.choices(values, k=len(values))) for _ in range(k))
    return meds[int(0.025 * k)], meds[int(0.975 * k)]


def permutation_p(a, b, k=10000, seed=0):
    """One-sided p-value for median(a) - median(b) >= observed."""
    rng = random.Random(seed)
    observed = st.median(a) - st.median(b)
    pooled, n = a + b, len(b)
    hits = 0
    for _ in range(k):
        rng.shuffle(pooled)
        hits += (st.median(pooled[n:]) - st.median(pooled[:n])) >= observed
    return hits / k


def main():
    b = {name: load(path) for name, path in FILES.items()}
    first, third = b["batch1"] + b["batch2"], b["batch3"]
    everything = first + third

    print("TEST 1  repair-cost distribution")
    for name, rows in list(b.items()) + [("all", everything)]:
        print(f"  {name:7s} {distribution(rows)}")

    print("\nTEST 2  bishop preference by configuration (median damage, centipawns)")
    print(f"  overall median {st.median(r['damage'] for r in everything):+.0f}, "
          f"bishop favoured in {sum(r['damage'] > rp.TOL for r in everything) / len(everything):.0%}")
    for cfg in ["creates pair", "had pair", "lone bishop", "same-colour"]:
        v1 = [r["damage"] for r in first if r["config"] == cfg]
        v3 = [r["damage"] for r in third if r["config"] == cfg]
        va = v1 + v3
        lo, hi = bootstrap_ci(va)
        print(f"  {cfg:13s} b1+2 {st.median(v1):+5.0f} | b3 {st.median(v3):+5.0f} | "
              f"all {st.median(va):+5.0f}  95% CI [{lo:+.0f}, {hi:+.0f}]  n={len(va)}")

    print("\nTEST 3  closed vs open (|damage|)")
    op = [abs(r["damage"]) for r in everything if r["structure"] == "open"]
    cl = [abs(r["damage"]) for r in everything if r["structure"] == "closed"]
    print(f"  open n={len(op)} median {st.median(op):.0f} | closed n={len(cl)} median {st.median(cl):.0f} | "
          f"p = {permutation_p(op, cl):.2f}")

    print("\nTEST 4  offset correction, estimated on batches 1+2, applied to batch 3")
    offset = {cfg: st.median([r["damage"] for r in first if r["config"] == cfg])
              for cfg in ["creates pair", "had pair", "lone bishop", "same-colour"]}
    raw = [r["damage"] for r in third]
    corrected = [r["damage"] - offset[r["config"]] for r in third]
    for name, v in [("raw", raw), ("corrected", corrected)]:
        print(f"  {name:9s} median {st.median(v):+5.0f}   median |deviation| "
              f"{st.median(abs(x) for x in v):.0f}")


if __name__ == "__main__":
    main()
