"""Kommandoradsgränssnitt för Schackmentor."""
import argparse

from . import config


def _cmd_config(args):
    cfg = config.load()
    changed = False
    if args.user is not None:
        cfg["username"] = args.user
        changed = True
    if args.depth is not None:
        cfg["depth"] = args.depth
        changed = True
    if args.model is not None:
        cfg["coach_model"] = args.model
        changed = True
    if args.time_classes is not None:
        cfg["time_classes"] = [t.strip() for t in args.time_classes.split(",") if t.strip()]
        changed = True
    if changed:
        config.save(cfg)
        print("Sparat config.json")
    print(f"  användarnamn:    {cfg['username'] or '(ej satt)'}")
    print(f"  djup:            {cfg['depth']}")
    print(f"  coach-modell:    {cfg['coach_model']}")
    print(f"  tidskontroller:  {cfg['time_classes'] or 'alla'}")
    print(f"  motor:           {cfg['engine_path']}")


def _cmd_fetch(args):
    from . import fetch
    fetch.fetch(username=args.user, max_months=args.max_months, since=args.since, force=args.force)


def _cmd_analyze(args):
    from . import analyze
    tc = [t.strip() for t in args.time_class.split(",")] if args.time_class else None
    analyze.analyse_all(depth=args.depth, limit_games=args.limit, time_classes=tc, force=args.force)


def _cmd_report(args):
    from . import report
    report.build_report()


def _cmd_coach(args):
    from . import coach
    coach.coach(use_api=args.api, model=args.model)


def _cmd_progress(args):
    from . import progress
    progress.build_chart(window=args.window)


def _cmd_run(args):
    from . import analyze, fetch, report
    fetch.fetch(username=args.user, max_months=args.max_months, since=args.since)
    tc = [t.strip() for t in args.time_class.split(",")] if args.time_class else None
    analyze.analyse_all(depth=args.depth, limit_games=args.limit, time_classes=tc)
    report.build_report()
    from . import coach
    coach.coach(use_api=args.api)


def main():
    parser = argparse.ArgumentParser(
        prog="schackmentor",
        description="Analyserar dina Chess.com-partier och coachar dig att bli bättre.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    pc = sub.add_parser("config", help="Visa/ändra inställningar")
    pc.add_argument("--user", help="Chess.com-användarnamn")
    pc.add_argument("--depth", type=int, help="Sökdjup för Stockfish")
    pc.add_argument("--model", help="Claude-modell för coachen")
    pc.add_argument("--time-classes", dest="time_classes",
                    help="Kommaseparerat, t.ex. blitz,rapid (tom = alla)")
    pc.set_defaults(func=_cmd_config)

    pf = sub.add_parser("fetch", help="Hämta partier från Chess.com")
    pf.add_argument("--user", help="Chess.com-användarnamn (annars från config)")
    pf.add_argument("--max-months", type=int, help="Begränsa till de N senaste månaderna")
    pf.add_argument("--since", help="Hämta från och med YYYY-MM")
    pf.add_argument("--force", action="store_true", help="Hämta om även gamla månader")
    pf.set_defaults(func=_cmd_fetch)

    pa = sub.add_parser("analyze", help="Analysera partier med Stockfish")
    pa.add_argument("--depth", type=int, help="Sökdjup (default från config)")
    pa.add_argument("--limit", type=int, help="Analysera högst N nya partier")
    pa.add_argument("--time-class", help="Filtrera, t.ex. blitz,rapid")
    pa.add_argument("--force", action="store_true", help="Analysera om även klara partier")
    pa.set_defaults(func=_cmd_analyze)

    pr = sub.add_parser("report", help="Bygg rapport + coach-brief")
    pr.set_defaults(func=_cmd_report)

    pp = sub.add_parser("progress", help="Rita din utveckling över tid (PNG)")
    pp.add_argument("--window", type=int, default=8, help="Fönster för glidande snitt")
    pp.set_defaults(func=_cmd_progress)

    pco = sub.add_parser("coach", help="Få AI-coachning")
    pco.add_argument("--api", action="store_true", help="Använd Claude API (kräver ANTHROPIC_API_KEY)")
    pco.add_argument("--model", help="Claude-modell")
    pco.set_defaults(func=_cmd_coach)

    prun = sub.add_parser("run", help="Kör allt: fetch + analyze + report + coach")
    prun.add_argument("--user")
    prun.add_argument("--max-months", type=int)
    prun.add_argument("--since")
    prun.add_argument("--depth", type=int)
    prun.add_argument("--limit", type=int)
    prun.add_argument("--time-class")
    prun.add_argument("--api", action="store_true")
    prun.set_defaults(func=_cmd_run)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
