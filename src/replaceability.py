"""
Core logic: how replaceable is a knight in a specific chess position?

Measure, for one position:
  E0      engine evaluation of the real position (centipawns, side to move)
  swap    put a bishop of the same colour on the knight's square
  E1      evaluation after the swap
  damage  E1 - E0   (positive = the engine likes the bishop better)
  repair  the fewest pawn edits that bring the evaluation back to within
          TOL of E0. An edit shifts one of the swapping side's own pawns
          one square along its file. Greedy search, up to MAX_EDITS edits.

Repair cost: 0 (harmless swap), 1, 2, or "unrepaired".
"""
import chess
import chess.engine

DEPTH = 12        # fixed search depth for every evaluation (comparability)
TOL = 30          # centipawns: "restored" means |E - E0| <= 0.3 pawns
MAX_EDITS = 2     # repair search budget
MAX_ABS_E0 = 300  # skip positions already decided (|E0| > 3 pawns)
MATE_CAP = 1500   # mate scores are capped so they don't dominate statistics


def evaluate(engine, board, depth=DEPTH):
    """Evaluation in centipawns from the side to move's point of view."""
    info = engine.analyse(board, chess.engine.Limit(depth=depth))
    score = info["score"].relative.score(mate_score=10000)
    return max(-MATE_CAP, min(MATE_CAP, score))


def substitute(board, square):
    """Copy of the board with the piece on `square` replaced by a bishop."""
    new = board.copy(stack=False)
    new.set_piece_at(square, chess.Piece(chess.BISHOP, board.turn))
    return new


def is_quiet(board, square):
    """True if the new bishop attacks no enemy piece.

    Without this filter the first result was an artifact: a bishop that
    appears on its own turn often captures something immediately, which
    says nothing about the knight's positional role.
    """
    us = board.piece_at(square).color
    for target in board.attacks(square):
        piece = board.piece_at(target)
        if piece is not None and piece.color != us:
            return False
    return True


def pawn_edits(board, color):
    """All legal boards reachable by shifting one own pawn one square along its file."""
    results = []
    for sq in board.pieces(chess.PAWN, color):
        for step in (8, -8):
            target = sq + step
            if not (8 <= target < 56) or board.piece_at(target) is not None:
                continue
            new = board.copy(stack=False)
            new.remove_piece_at(sq)
            new.set_piece_at(target, chess.Piece(chess.PAWN, color))
            if new.is_valid():
                name = f"P{chess.square_name(sq)}->{chess.square_name(target)}"
                results.append((name, new))
    return results


def repair(engine, swapped, e0, e1, color):
    """Greedy repair search. Returns (cost, edits_used, final_gap)."""
    current = swapped
    edits = []
    gap = abs(e1 - e0)
    if gap <= TOL:
        return 0, edits, gap
    for k in range(1, MAX_EDITS + 1):
        candidates = [(abs(evaluate(engine, b) - e0), name, b)
                      for name, b in pawn_edits(current, color)]
        if not candidates:
            break
        gap, name, current = min(candidates, key=lambda c: c[0])
        edits.append(name)
        if gap <= TOL:
            return k, edits, gap
    return "unrepaired", edits, gap


def locked_pawn_pairs(board):
    """Number of white pawns directly blocked by a black pawn."""
    n = 0
    for sq in board.pieces(chess.PAWN, chess.WHITE):
        ahead = sq + 8
        if ahead < 64 and board.piece_at(ahead) == chess.Piece(chess.PAWN, chess.BLACK):
            n += 1
    return n


def structure(board):
    """Crude, hand-made definition: 'closed' if >= 2 locked pawn pairs.

    This definition turned out to show no difference in replaceability,
    which may say more about the definition than about chess.
    """
    return "closed" if locked_pawn_pairs(board) >= 2 else "open"


def bishop_configuration(board, square):
    """How the swap changes the bishops of the side to move."""
    us = board.turn

    def colour(s):
        return (chess.square_rank(s) + chess.square_file(s)) % 2

    before = {colour(s) for s in board.pieces(chess.BISHOP, us)}
    after = [colour(s) for s in substitute(board, square).pieces(chess.BISHOP, us)]
    if len(before) == 2:
        return "had pair"
    if len(set(after)) == 2:
        return "creates pair"
    if len(after) >= 2:
        return "same-colour"
    return "lone bishop"
