"""Bygger en läsbar rapport (markdown) + en kompakt brief.json för AI-coachen."""
import json
import os

from . import aggregate, config


def _fmt(v, suffix=""):
    return f"{v}{suffix}" if v is not None else "–"


def _evalstr(cp):
    return f"{cp/100:+.1f}"


def build_report():
    agg = aggregate.aggregate()
    p = config.paths()
    s = agg["summary"]
    L = []
    L.append("# Schackmentor – rapport\n")
    L.append(f"**Partier analyserade:** {s['games']}  ")
    if any(s["date_range"]):
        L.append(f"**Period:** {s['date_range'][0]} – {s['date_range'][1]}  ")
    tc = ", ".join(f"{k}: {v}" for k, v in s["by_time_class"].items())
    L.append(f"**Tidskontroller:** {tc}\n")

    L.append("## Övergripande precision\n")
    L.append(f"- **Snittfel (ACPL):** {_fmt(s['overall_acpl'])} centipawns/drag "
             "(lägre = bättre; ~20–40 är klubbnivå, <20 är starkt)")
    L.append(f"- **Blundrar/parti:** {s['blunders_per_game']}  ·  "
             f"**Misstag/parti:** {s['mistakes_per_game']}  ·  "
             f"**Inexaktheter/parti:** {s['inaccuracies_per_game']}")
    if s["total_blunders"]:
        pct = round(100 * s["blunders_hanging_material"] / s["total_blunders"])
        L.append(f"- **Av dina blundrar bestraffades {pct}% direkt av en slagväxling** "
                 "(tecken på hängda pjäser/oskyddade brickor)")
    L.append("")

    L.append("## Vit vs svart\n")
    L.append("| Färg | Partier | V–O–F | Poäng | ACPL |")
    L.append("|---|---|---|---|---|")
    for col, label in (("white", "Vit"), ("black", "Svart")):
        b = s["by_color"][col]
        L.append(f"| {label} | {b['games']} | {b['wins']}–{b['draws']}–{b['losses']} "
                 f"| {b['score_pct']}% | {_fmt(b['acpl'])} |")
    L.append("")

    L.append("## Spelfaser (ACPL & blundrar)\n")
    L.append("| Fas | ACPL | Blundrar | Drag |")
    L.append("|---|---|---|---|")
    for ph, label in (("opening", "Öppning"), ("middlegame", "Mittspel"), ("endgame", "Slutspel")):
        L.append(f"| {label} | {_fmt(s['phase_acpl'].get(ph))} "
                 f"| {s['blunders_by_phase'].get(ph, 0)} "
                 f"| {s['moves_by_phase'].get(ph, 0)} |")
    L.append("")

    op = agg["openings"]
    if op["worst"]:
        L.append("## Svagaste öppningar (≥4 partier)\n")
        L.append("| Öppning | Färg | Partier | Poäng | ACPL | Blundrar |")
        L.append("|---|---|---|---|---|---|")
        for o in op["worst"]:
            L.append(f"| {o['name']} | {o['color']} | {o['games']} "
                     f"| {o['score_pct']}% | {_fmt(o['acpl'])} | {o['blunders']} |")
        L.append("")
    if op["best"]:
        L.append("## Starkaste öppningar (≥4 partier)\n")
        L.append("| Öppning | Färg | Partier | Poäng | ACPL |")
        L.append("|---|---|---|---|---|")
        for o in op["best"]:
            L.append(f"| {o['name']} | {o['color']} | {o['games']} | {o['score_pct']}% | {_fmt(o['acpl'])} |")
        L.append("")

    if agg["top_blunders"]:
        L.append("## Värsta enskilda misstagen\n")
        L.append("| # | Datum | Drag | Du spelade | Bästa drag | Eval → | Parti |")
        L.append("|---|---|---|---|---|---|---|")
        for i, b in enumerate(agg["top_blunders"], 1):
            L.append(f"| {i} | {b['date']} | {b['move_no']}. ({b['color']}) "
                     f"| {b['played']} | {b['best']} "
                     f"| {_evalstr(b['eval_before'])} → {_evalstr(b['eval_after'])} "
                     f"| [länk]({b['url']}) |")
        L.append("")

    md = "\n".join(L)
    md_path = os.path.join(p["reports"], "report.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md)

    brief_path = os.path.join(p["reports"], "brief.json")
    with open(brief_path, "w", encoding="utf-8") as f:
        json.dump(agg, f, ensure_ascii=False, indent=2)

    print(f"Rapport: {md_path}")
    print(f"Coach-brief: {brief_path}")
    return md_path, brief_path
