"""Analyserar partier drag-för-drag med Stockfish och klassar dina fel."""
import glob
import io
import json
import math
import os

import chess
import chess.engine
import chess.pgn

from . import config

MATE_SCORE = 100000
CP_CAP = 1000  # centipawn-tak så att stora matt-svängar inte dominerar statistiken

DRAW_RESULTS = {
    "agreed", "repetition", "stalemate", "insufficient",
    "50move", "timevsinsufficient",
}

NONPAWN = {chess.KNIGHT: 3, chess.BISHOP: 3, chess.ROOK: 5, chess.QUEEN: 9}


def _winprob(cp):
    """Centipawns -> vinstchans i procent (0-100) ur dragarens perspektiv."""
    return 50.0 + 50.0 * (2.0 / (1.0 + math.exp(-0.00368208 * cp)) - 1.0)


def _cp(score):
    """chess.engine.Score (redan .pov:ad) -> centipawns, kapad till +-CP_CAP."""
    val = score.score(mate_score=MATE_SCORE)
    return max(-CP_CAP, min(CP_CAP, val))


def _nonpawn_material(board):
    total = 0
    for pt, v in NONPAWN.items():
        total += v * (len(board.pieces(pt, chess.WHITE)) + len(board.pieces(pt, chess.BLACK)))
    return total


def _phase(board):
    if _nonpawn_material(board) <= 20:
        return "endgame"
    if board.fullmove_number <= 10:
        return "opening"
    return "middlegame"


def _result_for(game_json, color):
    side = game_json["white"] if color == "white" else game_json["black"]
    r = side.get("result", "")
    if r == "win":
        return "win", "win"
    if r in DRAW_RESULTS:
        return "draw", r
    return "loss", r


def _opening(headers, game_json):
    eco = headers.get("ECO", "")
    url = game_json.get("eco") or headers.get("ECOUrl") or ""
    name = ""
    if "openings/" in url:
        slug = url.split("openings/")[-1].split("?")[0]
        name = slug.replace("-", " ").strip()
    return eco, name


def analyse_game(engine, g, username, depth, thr):
    game = chess.pgn.read_game(io.StringIO(g["pgn"]))
    if game is None:
        return None
    h = game.headers
    white = g["white"]["username"].lower()
    black = g["black"]["username"].lower()
    if username == white:
        color, uc = "white", chess.WHITE
    elif username == black:
        color, uc = "black", chess.BLACK
    else:
        return None

    moves = list(game.mainline_moves())
    if not moves:
        return None

    result, term = _result_for(g, color)
    eco, opening = _opening(h, g)
    limit = chess.engine.Limit(depth=depth)

    board = game.board()
    info = engine.analyse(board, limit)  # eval av startställningen

    counts = {"inaccuracy": 0, "mistake": 0, "blunder": 0}
    phase_loss = {"opening": [], "middlegame": [], "endgame": []}
    cploss_sum = 0
    cploss_n = 0
    mistakes = []  # detaljer för misstag + blundrar

    for move in moves:
        mover = board.turn
        best_for_mover = _cp(info["score"].pov(mover))
        pv = info.get("pv")
        best_move = pv[0] if pv else None
        best_san = board.san(best_move) if best_move else ""
        best_is_cap = bool(best_move) and board.is_capture(best_move)
        san = board.san(move)
        ph = _phase(board)
        move_no = board.fullmove_number
        fen = board.fen()

        board.push(move)

        if board.is_game_over():
            outcome = board.outcome()
            if outcome and outcome.winner == mover:
                achieved = CP_CAP
            elif outcome and outcome.winner is None:
                achieved = 0
            else:
                achieved = -CP_CAP
            opp_reply_cap = False
            info = None
        else:
            info = engine.analyse(board, limit)
            achieved = _cp(info["score"].pov(mover))
            opp_pv = info.get("pv")
            opp_reply_cap = bool(opp_pv) and board.is_capture(opp_pv[0])

        if mover != uc:
            continue

        cp_loss = max(0, best_for_mover - achieved)
        drop = max(0.0, _winprob(best_for_mover) - _winprob(achieved))
        cploss_sum += cp_loss
        cploss_n += 1
        phase_loss[ph].append(cp_loss)

        cls = "ok"
        if drop >= thr["blunder"]:
            cls = "blunder"
            counts["blunder"] += 1
        elif drop >= thr["mistake"]:
            cls = "mistake"
            counts["mistake"] += 1
        elif drop >= thr["inaccuracy"]:
            cls = "inaccuracy"
            counts["inaccuracy"] += 1

        if cls in ("mistake", "blunder"):
            mistakes.append({
                "move_no": move_no,
                "color": color,
                "played": san,
                "best": best_san,
                "best_was_capture": best_is_cap,
                "punished_by_capture": opp_reply_cap,
                "cp_loss": cp_loss,
                "drop": round(drop, 1),
                "eval_before": best_for_mover,
                "eval_after": achieved,
                "class": cls,
                "phase": ph,
                "fen": fen,
            })

    phase_n = {k: len(v) for k, v in phase_loss.items()}
    phase_acpl = {k: (round(sum(v) / len(v)) if v else None) for k, v in phase_loss.items()}
    user_rating = g["white"]["rating"] if color == "white" else g["black"]["rating"]
    opp_rating = g["black"]["rating"] if color == "white" else g["white"]["rating"]

    return {
        "id": g["url"].rstrip("/").split("/")[-1],
        "url": g["url"],
        "date": h.get("UTCDate") or h.get("Date") or "",
        "time_class": g.get("time_class"),
        "time_control": g.get("time_control"),
        "rated": g.get("rated", True),
        "user_color": color,
        "user_rating": user_rating,
        "opp_rating": opp_rating,
        "opponent": (g["black"] if color == "white" else g["white"]).get("username", ""),
        "result": result,
        "termination": term,
        "eco": eco,
        "opening": opening,
        "n_user_moves": cploss_n,
        "user_acpl": round(cploss_sum / cploss_n) if cploss_n else 0,
        "counts": counts,
        "phase_n": phase_n,
        "phase_acpl": phase_acpl,
        "mistakes": mistakes,
    }


def analyse_all(depth=None, limit_games=None, time_classes=None, force=False):
    cfg = config.load()
    depth = depth or cfg["depth"]
    thr = cfg["thresholds"]
    time_classes = time_classes if time_classes is not None else cfg.get("time_classes") or []
    username = cfg["username"].strip().lower()
    if not username:
        raise SystemExit("Inget användarnamn satt. Kör:  ./mentor config --user <namn>")
    if not os.path.exists(cfg["engine_path"]):
        raise SystemExit(f"Stockfish saknas på {cfg['engine_path']}")

    p = config.paths()
    month_files = sorted(glob.glob(os.path.join(p["games"], "*.json")))
    if not month_files:
        raise SystemExit("Inga partier nedladdade. Kör:  ./mentor fetch")

    engine = chess.engine.SimpleEngine.popen_uci(cfg["engine_path"])
    engine.configure({"Threads": cfg["threads"], "Hash": cfg["hash_mb"]})
    analyzed = 0
    skipped = 0
    print(f"Analyserar med Stockfish (djup {depth})...")
    try:
        for mf in month_files:
            with open(mf, encoding="utf-8") as f:
                games = json.load(f)
            for g in games:
                if time_classes and g.get("time_class") not in time_classes:
                    continue
                gid = g["url"].rstrip("/").split("/")[-1]
                out = os.path.join(p["analysis"], f"{gid}.json")
                if os.path.exists(out) and not force:
                    skipped += 1
                    continue
                rec = analyse_game(engine, g, username, depth, thr)
                if rec is None:
                    continue
                with open(out, "w", encoding="utf-8") as f:
                    json.dump(rec, f, ensure_ascii=False)
                analyzed += 1
                c = rec["counts"]
                print(
                    f"  [{analyzed}] {rec['date']} {rec['user_color']:5s} "
                    f"{rec['result']:4s}  ACPL {rec['user_acpl']:4d}  "
                    f"blund {c['blunder']} miss {c['mistake']} inex {c['inaccuracy']}"
                )
                if limit_games and analyzed >= limit_games:
                    print(f"Nådde gränsen ({limit_games}).")
                    return analyzed
    finally:
        engine.quit()

    print(f"Analyserade {analyzed} nya partier ({skipped} redan klara).")
    return analyzed
