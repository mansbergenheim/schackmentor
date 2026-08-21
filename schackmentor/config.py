"""Konfiguration och sökvägar för Schackmentor."""
import json
import os

# Projektroten = mappen ovanför detta paket.
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(ROOT, "config.json")

DEFAULTS = {
    "username": "",
    "engine_path": "engine/stockfish/stockfish-macos-m1-apple-silicon",
    "depth": 12,
    "threads": 2,
    "hash_mb": 256,
    # Tröskelvärden i procentenheters tappad vinstchans (win%-drop) per drag.
    "thresholds": {"inaccuracy": 8, "mistake": 15, "blunder": 25},
    "coach_model": "claude-opus-4-8",
    # Tom lista = alla tidskontroller (blitz/rapid/bullet/daily).
    "time_classes": [],
}


def load():
    """Läs config.json ovanpå standardvärden och gör engine_path absolut."""
    cfg = json.loads(json.dumps(DEFAULTS))  # djup kopia
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, encoding="utf-8") as f:
            user = json.load(f)
        for k, v in user.items():
            if k == "thresholds" and isinstance(v, dict):
                cfg["thresholds"].update(v)
            else:
                cfg[k] = v
    ep = cfg["engine_path"]
    if not os.path.isabs(ep):
        cfg["engine_path"] = os.path.join(ROOT, ep)
    return cfg


def save(cfg):
    """Spara config (utan att förstöra relativ engine_path)."""
    out = json.loads(json.dumps(cfg))
    ep = out.get("engine_path", "")
    if os.path.isabs(ep) and ep.startswith(ROOT):
        out["engine_path"] = os.path.relpath(ep, ROOT)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
        f.write("\n")


def paths():
    """Returnera (och skapa) projektets datamappar."""
    p = {
        "root": ROOT,
        "games": os.path.join(ROOT, "data", "games"),
        "analysis": os.path.join(ROOT, "data", "analysis"),
        "reports": os.path.join(ROOT, "data", "reports"),
    }
    for key in ("games", "analysis", "reports"):
        os.makedirs(p[key], exist_ok=True)
    return p
