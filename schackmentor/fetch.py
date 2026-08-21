"""Hämtar partier från Chess.coms publika API och sparar dem månadsvis."""
import datetime
import json
import os
import time

import requests

from . import config

API = "https://api.chess.com/pub"
# Chess.com kräver en User-Agent, annars 403.
HEADERS = {"User-Agent": "schackmentor/0.1 (personligt analysverktyg)"}


def _get(url):
    r = requests.get(url, headers=HEADERS, timeout=30)
    if r.status_code == 404:
        raise SystemExit(
            f"Hittade inget på {url}\n"
            "Kontrollera att användarnamnet är korrekt (skiftläge spelar ingen roll)."
        )
    r.raise_for_status()
    return r.json()


def _archive_ym(url):
    """'.../games/2024/03' -> '2024-03' (nollutfyllt)."""
    parts = url.rstrip("/").split("/")
    y, m = parts[-2], parts[-1]
    return f"{int(y):04d}-{int(m):02d}"


def list_archives(username):
    data = _get(f"{API}/player/{username}/games/archives")
    return data.get("archives", [])


def fetch(username=None, max_months=None, since=None, force=False):
    cfg = config.load()
    username = (username or cfg["username"]).strip()
    if not username:
        raise SystemExit("Inget användarnamn. Kör:  ./mentor config --user <namn>")

    p = config.paths()
    archives = list_archives(username)
    if not archives:
        raise SystemExit(f"Inga partier hittades för '{username}' på Chess.com.")

    months = [(_archive_ym(u), u) for u in archives]  # äldst -> nyast
    if since:
        months = [(ym, u) for ym, u in months if ym >= since]
    if max_months:
        months = months[-max_months:]

    current_ym = datetime.date.today().strftime("%Y-%m")
    total = 0
    new_games = 0
    print(f"Hämtar partier för '{username}' ({len(months)} månader)...")
    for ym, url in months:
        out = os.path.join(p["games"], f"{ym}.json")
        # Hoppa över redan nedladdade gångna månader (de ändras inte).
        if os.path.exists(out) and not force and ym != current_ym:
            with open(out, encoding="utf-8") as f:
                total += len(json.load(f))
            continue
        data = _get(url)
        games = [g for g in data.get("games", []) if g.get("rules") == "chess" and g.get("pgn")]
        with open(out, "w", encoding="utf-8") as f:
            json.dump(games, f)
        total += len(games)
        new_games += len(games)
        print(f"  {ym}: {len(games)} partier")
        time.sleep(0.3)  # var snäll mot API:t

    print(f"Klart: {total} partier totalt ({new_games} nya/uppdaterade) i {p['games']}")
    return total
