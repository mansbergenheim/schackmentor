"""AI-coachen: gör om statistiken till konkreta, personliga schackråd."""
import json
import os

from . import config

SYSTEM = (
    "Du är en erfaren, rak och uppmuntrande schacktränare på FIDE-mästarnivå. "
    "Du får statistik från en spelares Chess.com-partier (analyserade med Stockfish) "
    "och ska ge konkret, handlingsbar coachning på svenska. Var specifik och peka "
    "alltid på siffrorna/ställningarna som stöd. Undvik floskler."
)

PROMPT_TEMPLATE = """\
Här är en sammanställning av spelarens partier (JSON):

```json
{brief}
```

Förklaring av fälten:
- ACPL = genomsnittlig centipawn-förlust per drag (lägre = bättre).
- top_blunders innehåller de värsta enskilda dragen med FEN-ställning, spelat drag,
  bästa drag och eval före/efter (i centipawns ur spelarens perspektiv).
- punished_by_capture=true betyder att motståndarens bästa svar var en slagväxling
  (ofta tecken på att en pjäs hängde).

Skriv en coachningsrapport i markdown på svenska med dessa avsnitt:

1. **Helhetsbedömning** – var står spelaren ungefär, och vad är det enskilt viktigaste att jobba på?
2. **Dina 3–5 största svagheter** – rangordnade, var och en motiverad med konkreta siffror ur datan.
3. **Träningsplan** – konkreta övningar (taktik, slutspel, öppningar) anpassade efter svagheterna,
   med ungefärlig tidsfördelning per vecka.
4. **Öppningsråd** – baserat på best/worst-öppningarna: vad ska behållas, vad bör bytas eller pluggas?
5. **Tre ställningar att studera** – välj tre lärorika exempel ur top_blunders. För varje:
   ange parti-länk och drag-nummer, förklara vad som gick fel, vilket idé/plan som var rätt,
   och vilket mönster spelaren ska känna igen i framtiden.

Var konkret och personlig. Det här är en riktig spelare som vill bli bättre.
"""


def _load_brief():
    p = config.paths()
    brief_path = os.path.join(p["reports"], "brief.json")
    if not os.path.exists(brief_path):
        raise SystemExit("Ingen brief.json. Kör:  ./mentor report")
    with open(brief_path, encoding="utf-8") as f:
        return json.load(f), brief_path


def build_prompt():
    brief, _ = _load_brief()
    return PROMPT_TEMPLATE.format(brief=json.dumps(brief, ensure_ascii=False, indent=2))


def coach(use_api=False, model=None):
    cfg = config.load()
    p = config.paths()
    prompt = build_prompt()

    if not use_api:
        print(
            "Coach-brief är klar (data/reports/brief.json) och rapporten ligger i\n"
            "data/reports/report.md.\n\n"
            "AI-coachning utan API-nyckel: be Claude Code läsa rapporten, t.ex.:\n"
            "   \"Läs data/reports/brief.json och coacha mig som en schacktränare.\"\n\n"
            "Vill du köra helautomatiskt: sätt ANTHROPIC_API_KEY och kör  ./mentor coach --api"
        )
        return None

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise SystemExit("ANTHROPIC_API_KEY är inte satt i miljön.")
    try:
        import anthropic
    except ImportError:
        raise SystemExit("Paketet 'anthropic' saknas i venv.")

    model = model or cfg["coach_model"]
    client = anthropic.Anthropic(api_key=api_key)
    print(f"Frågar {model} om coachning...")
    msg = client.messages.create(
        model=model,
        max_tokens=4000,
        system=SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )
    text = "".join(block.text for block in msg.content if getattr(block, "type", "") == "text")
    out = os.path.join(p["reports"], "coaching.md")
    with open(out, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"Coachning sparad: {out}\n")
    print(text)
    return out
