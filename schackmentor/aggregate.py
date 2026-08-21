"""Slår ihop alla analyserade partier till mönster och nyckeltal."""
import glob
import json
import os
from collections import defaultdict

from . import config

MIN_OPENING_GAMES = 4  # minst så många partier för att en öppning ska bedömas


def _load_games():
    p = config.paths()
    games = []
    for f in sorted(glob.glob(os.path.join(p["analysis"], "*.json"))):
        with open(f, encoding="utf-8") as fh:
            games.append(json.load(fh))
    return games


def _score(wins, draws, n):
    return round(100 * (wins + 0.5 * draws) / n, 1) if n else 0.0


def _pooled_acpl(items):
    """items: lista av (acpl, n_moves) -> viktat snitt."""
    tot = sum(a * n for a, n in items if n)
    cnt = sum(n for _, n in items if n)
    return round(tot / cnt) if cnt else None


def aggregate():
    games = _load_games()
    if not games:
        raise SystemExit("Inga analyserade partier. Kör:  ./mentor analyze")

    n = len(games)
    dates = sorted(g["date"] for g in games if g.get("date"))
    date_range = [dates[0], dates[-1]] if dates else ["", ""]

    by_time_class = defaultdict(int)
    color_stat = {c: {"n": 0, "w": 0, "d": 0, "l": 0, "acpl_items": []} for c in ("white", "black")}
    phase_acpl_items = {ph: [] for ph in ("opening", "middlegame", "endgame")}
    phase_blunders = defaultdict(int)
    phase_moves = defaultdict(int)
    total_b = total_m = total_i = 0
    acpl_items = []
    openings = defaultdict(lambda: {"n": 0, "w": 0, "d": 0, "l": 0, "acpl_items": [], "blunders": 0, "eco": ""})

    for g in games:
        by_time_class[g.get("time_class") or "okänd"] += 1
        c = g["user_color"]
        cs = color_stat[c]
        cs["n"] += 1
        res = g["result"]
        cs[{"win": "w", "draw": "d", "loss": "l"}[res]] += 1
        cs["acpl_items"].append((g["user_acpl"], g["n_user_moves"]))
        acpl_items.append((g["user_acpl"], g["n_user_moves"]))

        cc = g["counts"]
        total_b += cc["blunder"]
        total_m += cc["mistake"]
        total_i += cc["inaccuracy"]

        for ph in phase_acpl_items:
            a = g["phase_acpl"].get(ph)
            nm = g["phase_n"].get(ph, 0)
            if a is not None and nm:
                phase_acpl_items[ph].append((a, nm))
            phase_moves[ph] += nm
        for mk in g["mistakes"]:
            if mk["class"] == "blunder":
                phase_blunders[mk["phase"]] += 1

        key = (c, g["opening"] or g["eco"] or "Okänd öppning")
        ob = openings[key]
        ob["n"] += 1
        ob[{"win": "w", "draw": "d", "loss": "l"}[res]] += 1
        ob["acpl_items"].append((g["user_acpl"], g["n_user_moves"]))
        ob["blunders"] += cc["blunder"]
        ob["eco"] = g["eco"] or ob["eco"]

    def color_block(cs):
        return {
            "games": cs["n"],
            "wins": cs["w"], "draws": cs["d"], "losses": cs["l"],
            "score_pct": _score(cs["w"], cs["d"], cs["n"]),
            "acpl": _pooled_acpl(cs["acpl_items"]),
        }

    opening_list = []
    for (color, name), ob in openings.items():
        opening_list.append({
            "color": color, "name": name, "eco": ob["eco"], "games": ob["n"],
            "wins": ob["w"], "draws": ob["d"], "losses": ob["l"],
            "score_pct": _score(ob["w"], ob["d"], ob["n"]),
            "acpl": _pooled_acpl(ob["acpl_items"]),
            "blunders": ob["blunders"],
        })
    opening_list.sort(key=lambda o: (-o["games"], o["score_pct"]))
    qualified = [o for o in opening_list if o["games"] >= MIN_OPENING_GAMES]
    worst = sorted(qualified, key=lambda o: o["score_pct"])[:6]
    best = sorted(qualified, key=lambda o: -o["score_pct"])[:6]

    # Värsta enskilda blundrar (största tappade vinstchans) för konkreta lektioner.
    all_blunders = []
    for g in games:
        for mk in g["mistakes"]:
            if mk["class"] != "blunder":
                continue
            all_blunders.append({
                "url": g["url"], "date": g["date"], "color": g["user_color"],
                "opening": g["opening"] or g["eco"],
                "move_no": mk["move_no"], "phase": mk["phase"],
                "played": mk["played"], "best": mk["best"],
                "drop": mk["drop"], "eval_before": mk["eval_before"], "eval_after": mk["eval_after"],
                "punished_by_capture": mk["punished_by_capture"],
                "fen": mk["fen"],
            })
    all_blunders.sort(key=lambda b: -b["drop"])
    top_blunders = all_blunders[:15]

    hung = sum(1 for b in all_blunders if b["punished_by_capture"])

    return {
        "summary": {
            "games": n,
            "date_range": date_range,
            "by_time_class": dict(by_time_class),
            "overall_acpl": _pooled_acpl(acpl_items),
            "by_color": {"white": color_block(color_stat["white"]), "black": color_block(color_stat["black"])},
            "phase_acpl": {ph: _pooled_acpl(items) for ph, items in phase_acpl_items.items()},
            "blunders_per_game": round(total_b / n, 2),
            "mistakes_per_game": round(total_m / n, 2),
            "inaccuracies_per_game": round(total_i / n, 2),
            "blunders_by_phase": dict(phase_blunders),
            "moves_by_phase": dict(phase_moves),
            "total_blunders": total_b,
            "blunders_hanging_material": hung,
        },
        "openings": {
            "most_played": opening_list[:10],
            "best": best,
            "worst": worst,
        },
        "top_blunders": top_blunders,
    }
