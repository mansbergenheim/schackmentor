"""Ritar din utveckling över tid: rating, snittfel (ACPL) och blundrar/parti."""
import datetime
import glob
import json
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from . import config  # noqa: E402


def _load():
    p = config.paths()
    games = []
    for f in sorted(glob.glob(os.path.join(p["analysis"], "*.json"))):
        with open(f, encoding="utf-8") as fh:
            g = json.load(fh)
        try:
            g["_dt"] = datetime.datetime.strptime(g.get("date", ""), "%Y.%m.%d")
        except ValueError:
            continue
        games.append(g)
    games.sort(key=lambda x: (x["_dt"], str(x.get("id", ""))))
    return games


def _rolling(vals, w):
    out = []
    for i in range(len(vals)):
        chunk = vals[max(0, i - w + 1): i + 1]
        out.append(sum(chunk) / len(chunk))
    return out


def _month_ticks(games):
    ticks, labels, prev = [], [], None
    for i, g in enumerate(games, 1):
        ym = g["_dt"].strftime("%Y-%m")
        if ym != prev:
            ticks.append(i)
            labels.append(ym)
            prev = ym
    return ticks, labels


def _comeback_index(games):
    """Index för första partiet efter det längsta uppehållet (din comeback)."""
    best_gap, best_i = datetime.timedelta(0), None
    for i in range(1, len(games)):
        gap = games[i]["_dt"] - games[i - 1]["_dt"]
        if gap > best_gap:
            best_gap, best_i = gap, i + 1  # 1-indexerat
    # Bara intressant om uppehållet är rejält.
    return best_i if best_gap.days >= 60 else None


def build_chart(window=8):
    games = _load()
    if len(games) < 2:
        raise SystemExit("För få analyserade partier för en graf. Kör:  ./mentor analyze")

    n = len(games)
    idx = list(range(1, n + 1))
    acpl = [g["user_acpl"] for g in games]
    blunders = [g["counts"]["blunder"] for g in games]
    ticks, labels = _month_ticks(games)
    cb = _comeback_index(games)

    plt.rcParams.update({"font.size": 10, "axes.grid": True, "grid.alpha": 0.3})
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(11, 10), sharex=True)
    fig.suptitle(f"Schackutveckling – mansbergenheim ({n} partier)", fontsize=14, fontweight="bold")

    # 1) Rating (blitz, som dominerar materialet)
    bx = [i for i, g in zip(idx, games) if g["time_class"] == "blitz"]
    by = [g["user_rating"] for g in games if g["time_class"] == "blitz"]
    if bx:
        ax1.plot(bx, by, color="#1f77b4", lw=1.4, marker="o", ms=2.5, label="Blitz-rating")
        ax1.axhline(by[0], color="#1f77b4", ls=":", lw=0.8, alpha=0.6)
        ax1.annotate(f"{by[0]}", (bx[0], by[0]), textcoords="offset points", xytext=(-4, 6), fontsize=8)
        ax1.annotate(f"{by[-1]}", (bx[-1], by[-1]), textcoords="offset points", xytext=(2, 6), fontsize=8)
    ax1.set_ylabel("Rating")
    ax1.set_title("Rating över tid", fontsize=11, loc="left")
    ax1.legend(loc="upper left", fontsize=8)

    # 2) ACPL (lägre = bättre)
    ax2.plot(idx, acpl, color="#bbbbbb", lw=0.8, marker=".", ms=3, label="Per parti")
    ax2.plot(idx, _rolling(acpl, window), color="#d62728", lw=2.2, label=f"Glidande snitt ({window})")
    ax2.set_ylabel("ACPL")
    ax2.set_title("Snittfel per drag – ACPL (lägre = bättre)", fontsize=11, loc="left")
    ax2.legend(loc="upper right", fontsize=8)

    # 3) Blundrar per parti
    ax3.bar(idx, blunders, color="#cccccc", width=0.9, label="Per parti")
    ax3.plot(idx, _rolling(blunders, window), color="#2ca02c", lw=2.2, label=f"Glidande snitt ({window})")
    ax3.set_ylabel("Blundrar")
    ax3.set_title("Blundrar per parti (lägre = bättre)", fontsize=11, loc="left")
    ax3.legend(loc="upper right", fontsize=8)
    ax3.set_xlabel("Parti (kronologiskt) · etiketter = månad")
    ax3.set_xticks(ticks)
    ax3.set_xticklabels(labels, rotation=45, ha="right", fontsize=8)

    if cb:
        for ax in (ax1, ax2, ax3):
            ax.axvline(cb, color="#ff7f0e", ls="--", lw=1.5, alpha=0.8)
        ax1.annotate("Comeback", (cb, ax1.get_ylim()[1]), textcoords="offset points",
                     xytext=(4, -12), color="#ff7f0e", fontweight="bold", fontsize=9)

    fig.tight_layout(rect=[0, 0, 1, 0.97])
    p = config.paths()
    out = os.path.join(p["reports"], "progress.png")
    fig.savefig(out, dpi=140)
    plt.close(fig)

    # Kort textsammanfattning: jämför första vs senaste tredjedelen.
    third = max(1, n // 3)
    def avg(xs):
        return sum(xs) / len(xs)
    early_acpl, late_acpl = avg(acpl[:third]), avg(acpl[-third:])
    early_bl, late_bl = avg(blunders[:third]), avg(blunders[-third:])
    print(f"Graf sparad: {out}")
    print(f"  ACPL: {early_acpl:.0f} (första {third}) → {late_acpl:.0f} (senaste {third})")
    print(f"  Blundrar/parti: {early_bl:.2f} → {late_bl:.2f}")
    return out
