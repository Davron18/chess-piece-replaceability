"""
Run one batch of the study.

Example:
  python src/run_study.py --pgn-dir chessdatabase/chess-games --n 100 --seed 42 \
      --out data/batch1_100.csv
  python src/run_study.py --pgn-dir chessdatabase/chess-games --n 100 --seed 43 \
      --exclude data/batch1_100.csv --out data/batch2_100.csv

Positions: one per game, taken at move 20 (ply 40), from the side to move's
point of view, only if that side has a knight. Earlier batches can be passed
with --exclude so no position is used twice.
"""
import argparse
import csv
import glob
import os
import random
import time

import chess
import chess.engine
import chess.pgn

import replaceability as rp

PLY = 40


def collect_positions(pgn_dir, games_per_player, seed, exclude):
    rng = random.Random(seed)
    positions = []
    for path in sorted(glob.glob(os.path.join(pgn_dir, "*", "*.pgn"))):
        player = os.path.basename(os.path.dirname(path))
        games = []
        with open(path, encoding="latin-1") as f:
            while len(games) < 1000:
                game = chess.pgn.read_game(f)
                if game is None:
                    break
                games.append(game)
        rng.shuffle(games)
        taken = 0
        for game in games:
            moves = list(game.mainline_moves())
            if len(moves) < PLY + 10:
                continue
            board = game.board()
            for move in moves[:PLY]:
                board.push(move)
            knights = list(board.pieces(chess.KNIGHT, board.turn))
            if not knights or board.fen() in exclude:
                continue
            positions.append(dict(player=player, white=game.headers.get("White", "?"),
                                  black=game.headers.get("Black", "?"),
                                  year=game.headers.get("Date", "?")[:4],
                                  fen=board.fen(), knight=rng.choice(knights)))
            taken += 1
            if taken >= games_per_player:
                break
    rng.shuffle(positions)
    return positions


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pgn-dir", required=True)
    ap.add_argument("--n", type=int, default=100)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--games-per-player", type=int, default=70)
    ap.add_argument("--exclude", nargs="*", default=[])
    ap.add_argument("--engine", default="/usr/games/stockfish")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    exclude = {r["fen"] for p in args.exclude for r in csv.DictReader(open(p))}
    positions = collect_positions(args.pgn_dir, args.games_per_player, args.seed, exclude)

    engine = chess.engine.SimpleEngine.popen_uci(args.engine)
    engine.configure({"Threads": 1, "Hash": 64})
    rows, seen, t0 = [], set(), time.time()
    for pos in positions:
        if len(rows) >= args.n:
            break
        if pos["fen"] in seen:          # same game can appear in two players' files
            continue
        board = chess.Board(pos["fen"])
        e0 = rp.evaluate(engine, board)
        if abs(e0) > rp.MAX_ABS_E0:
            continue
        swapped = rp.substitute(board, pos["knight"])
        if not swapped.is_valid() or not rp.is_quiet(swapped, pos["knight"]):
            continue
        e1 = rp.evaluate(engine, swapped)
        cost, edits, gap = rp.repair(engine, swapped, e0, e1, board.turn)
        seen.add(pos["fen"])
        rows.append(dict(player=pos["player"], white=pos["white"], black=pos["black"],
                         year=pos["year"], fen=pos["fen"],
                         knight_sq=chess.square_name(pos["knight"]),
                         E0=e0, E1=e1, damage=e1 - e0, cost=cost, best_gap=gap,
                         edits=" ".join(edits),
                         locked_pairs=rp.locked_pawn_pairs(board),
                         structure=rp.structure(board)))
        print(f"{len(rows):3d} {pos['player']:14s} E0={e0:+5d} E1={e1:+5d} "
              f"cost={cost} [{time.time() - t0:.0f}s]", flush=True)
    engine.quit()

    with open(args.out, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    print(f"saved {len(rows)} positions to {args.out}")


if __name__ == "__main__":
    main()
