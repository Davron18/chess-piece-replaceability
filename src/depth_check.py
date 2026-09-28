"""
Depth check: re-evaluate every position before and after the swap at a deeper
search depth, and compare with the original depth 12 results.

  python src/depth_check.py 18 399

Arguments: depth, number of positions, (optional) engine path.
Only the swap damage is recomputed; the repair search is not repeated.
"""
import csv, chess, chess.engine, statistics as st, time, sys
DEPTH = int(sys.argv[1]) if len(sys.argv) > 1 else 18
N = int(sys.argv[2]) if len(sys.argv) > 2 else 400
ENGINE = sys.argv[3] if len(sys.argv) > 3 else "/usr/games/stockfish"
rows, seen = [], set()
for p in ["data/batch1_100.csv", "data/batch2_100.csv", "data/batch3_200.csv"]:
    for r in csv.DictReader(open(p)):
        if r["fen"] not in seen:
            seen.add(r["fen"]); rows.append(r)
rows = rows[:N]
eng = chess.engine.SimpleEngine.popen_uci(ENGINE)
def ev(b):
    s = eng.analyse(b, chess.engine.Limit(depth=DEPTH))["score"].relative.score(mate_score=10000)
    return max(-1500, min(1500, s))
out, t0 = [], time.time()
for i, r in enumerate(rows, 1):
    b = chess.Board(r["fen"]); us = b.turn; sq = chess.parse_square(r["knight_sq"])
    sw = b.copy(); sw.set_piece_at(sq, chess.Piece(chess.BISHOP, us))
    e0, e1 = ev(b), ev(sw)
    out.append((int(r["damage"]), e1 - e0))
    if i % 25 == 0:
        print(f"{i}/{len(rows)} done, {time.time()-t0:.0f}s", flush=True)
eng.quit()
d12 = [a for a, _ in out]; dD = [b for _, b in out]
n = len(out)
print(f"\nPositions: {n}   depth 12 vs depth {DEPTH}")
print(f"Harmless share (|damage| <= 30):   {sum(abs(x)<=30 for x in d12)/n:.0%}  vs  {sum(abs(x)<=30 for x in dD)/n:.0%}")
print(f"Bishop favored (damage > +30):     {sum(x>30 for x in d12)/n:.0%}  vs  {sum(x>30 for x in dD)/n:.0%}")
print(f"Median damage (centipawns):        {st.median(d12):+.0f}  vs  {st.median(dD):+.0f}")
mx, my = st.mean(d12), st.mean(dD)
cov = sum((a-mx)*(b-my) for a, b in out)
r_ = cov / (sum((a-mx)**2 for a in d12)**.5 * sum((b-my)**2 for b in dD)**.5)
print(f"Correlation of damage across depths: {r_:.2f}")
