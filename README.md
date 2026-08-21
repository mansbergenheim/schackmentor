# Schackmentor ♟️

Analyserar dina Chess.com-partier med Stockfish och coachar dig att bli en bättre
schackspelare – med konkreta svagheter, träningsplan och ställningar att studera.

## Pipeline

```
fetch   → hämtar dina partier från Chess.coms API (PGN/JSON per månad)
analyze → kör Stockfish drag-för-drag: centipawn-förlust, win%-drop,
          klassar inexaktheter/misstag/blundrar, faser, hängd materia
report  → bygger en rapport (data/reports/report.md) + en coach-brief (brief.json)
coach   → AI-coachen (Claude) gör om allt till konkreta råd
```

## Kom igång

```bash
# 1. Ställ in ditt användarnamn (en gång)
./mentor config --user DITT_CHESSCOM_NAMN

# 2. Kör allt
./mentor run

# eller steg för steg:
./mentor fetch --max-months 6      # hämta senaste 6 månaderna
./mentor analyze --time-class rapid,blitz
./mentor report
./mentor coach                     # skriver brief; be Claude Code coacha dig
```

## Användbara flaggor

| Kommando | Flagga | Betydelse |
|---|---|---|
| `fetch` | `--max-months N` / `--since YYYY-MM` | begränsa hur långt bak |
| `fetch` | `--force` | hämta om även gamla månader |
| `analyze` | `--depth N` | sökdjup (default 12; högre = långsammare/noggrannare) |
| `analyze` | `--limit N` | analysera högst N nya partier (bra för test) |
| `analyze` | `--time-class blitz,rapid` | hoppa över t.ex. bullet |
| `coach` | `--api` | helautomatisk coachning via Claude API (kräver `ANTHROPIC_API_KEY`) |

Analysen är **inkrementell** – redan hämtade månader och analyserade partier hoppas
över, så du kan köra `./mentor run` regelbundet och bara nya partier bearbetas.

## AI-coachning

Utan API-nyckel: `./mentor report` skapar `data/reports/brief.json`. Be sedan
Claude Code: *"Läs data/reports/brief.json och coacha mig som en schacktränare."*

Med API-nyckel: `export ANTHROPIC_API_KEY=...` och kör `./mentor coach --api`
→ skriver `data/reports/coaching.md`.

## Komponenter

- Motor: Stockfish 18 (arm64) i `engine/`
- Python-paket: `schackmentor/` (fetch, analyze, aggregate, report, coach, cli)
- Inställningar: `config.json`
- Data: `data/games/` (rådata), `data/analysis/` (per parti), `data/reports/`

## Tröskelvärden

Drag klassas på tappad vinstchans (procentenheter), justerbart i `config.json`:
inexakthet ≥ 8, misstag ≥ 15, blunder ≥ 25.
