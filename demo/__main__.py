"""Demo data commands.

    python -m app.demo seed      # load the demo dataset (replaces what is there)
    python -m app.demo reset     # same thing, said out loud
    python -m app.demo clear     # remove every record, keep the profile
    python -m app.demo status    # what is currently loaded
    python -m app.demo validate  # run the engine and check the planted patterns

``validate`` is the interesting one: it generates, analyses, and reports
whether each planted pattern survived all five gates and whether either
negative control produced a false positive. It exits non-zero if not, so
"the demo still demonstrates what it claims" is a check you can run rather
than a belief you hold.

Run from the repository root:

    python -m app.demo seed --app-dir backend

or with ``backend`` on the path already.
"""

from __future__ import annotations

import argparse
import sys
from datetime import date

from app.core.clock import SystemClock
from app.core.database import SessionFactory, engine
from app.demo.design import NEGATIVE_CONTROLS, PLANTED_PATTERNS
from app.demo.generator import generate
from app.demo.loader import clear_demo_data, describe, load_demo_data
from app.demo.validation import validate_dataset
from app.models import Base


def _rupees(paise: int | None) -> str:
    if paise is None:
        return "—"
    return f"₹{paise / 100:,.2f}"


def _print_status(status) -> None:
    print(f"  profile        {status.profile or '(none)'}")
    print(f"  budget         {_rupees(status.monthly_budget_paise)} / month")
    print(f"  expenses       {status.expenses}")
    print(f"  check-ins      {status.check_ins}")
    print(f"  life events    {status.events}")
    if status.earliest:
        print(f"  date range     {status.earliest} .. {status.latest}")


def command_seed(args: argparse.Namespace) -> int:
    reference = date.fromisoformat(args.date) if args.date else SystemClock().today()
    Base.metadata.create_all(bind=engine)

    dataset = generate(reference, seed=args.seed, days=args.days)
    with SessionFactory() as session:
        status = load_demo_data(session, dataset)

    print(f"Loaded demo data (seed {args.seed}, ending {reference.isoformat()}).")
    _print_status(status)
    print("\nOpen the dashboard:  cd frontend && npm run dev")
    return 0


def command_clear(_: argparse.Namespace) -> int:
    Base.metadata.create_all(bind=engine)
    with SessionFactory() as session:
        status = clear_demo_data(session)

    if status.profile is None:
        print("Nothing to clear — no profile exists yet.")
        return 0
    print("Cleared every record. The profile itself was kept.")
    _print_status(status)
    return 0


def command_status(_: argparse.Namespace) -> int:
    Base.metadata.create_all(bind=engine)
    with SessionFactory() as session:
        status = describe(session)

    if status.is_empty:
        print("No data loaded. Run:  python -m app.demo seed")
        return 0
    print("Currently loaded:")
    _print_status(status)
    return 0


def command_validate(args: argparse.Namespace) -> int:
    """Prove the demo still demonstrates what it claims."""
    reference = date.fromisoformat(args.date) if args.date else SystemClock().today()
    dataset = generate(reference, seed=args.seed, days=args.days)
    report = validate_dataset(dataset, window_days=args.window)

    print(f"Validation over a {args.window}-day window ending {reference.isoformat()}")
    print(f"  complete weeks       {report.complete_weeks}")
    print(f"  insight types found  {len(report.insight_types)}")
    print(f"  hypotheses tested    {report.hypotheses_tested}")
    print()

    for pattern in PLANTED_PATTERNS:
        found = report.found_patterns.get((pattern.habit, pattern.category.value))
        mark = "PASS" if found else "FAIL"
        detail = (
            f"q={found['q_value']:.6f} conf={found['confidence']:.3f} test={found['test']}"
            if found
            else "not emitted — a planted pattern failed a gate"
        )
        print(f"  [{mark}] {pattern.habit} ↔ {pattern.category.value}: {detail}")

    print()
    controls = ", ".join(NEGATIVE_CONTROLS)
    mark = "PASS" if report.control_false_positives == 0 else "FAIL"
    print(
        f"  [{mark}] negative controls ({controls}): "
        f"{report.control_false_positives} false positive(s)"
    )

    missing = sorted(report.missing_insight_types)
    if missing:
        print(f"\n  not demonstrated in this window: {', '.join(missing)}")

    print()
    if report.is_valid:
        print("The demo dataset demonstrates everything it claims.")
        return 0
    print("VALIDATION FAILED — the demo would not show what the README says it does.")
    return 1


def build_parser() -> argparse.ArgumentParser:
    # The shared options live on a parent parser so they work *after* the
    # subcommand — `demo validate --date …` is what anyone would type, and
    # putting them only on the top-level parser rejects exactly that.
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--seed", type=int, default=None, help="Override the fixed seed.")
    common.add_argument("--days", type=int, default=None, help="Days of history to generate.")
    common.add_argument(
        "--date", default=None, help="Reference date (YYYY-MM-DD). Defaults to today."
    )

    parser = argparse.ArgumentParser(
        prog="python -m app.demo",
        description="Load, clear and validate the deterministic demo dataset.",
        parents=[common],
    )

    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("seed", parents=[common], help="Load the demo dataset, replacing what is there.")
    sub.add_parser("reset", parents=[common], help="Alias for seed — clears and reloads.")
    sub.add_parser("clear", parents=[common], help="Remove every record, keeping the profile.")
    sub.add_parser("status", parents=[common], help="Report what is currently loaded.")
    validate = sub.add_parser(
        "validate", parents=[common], help="Check the planted patterns still survive."
    )
    validate.add_argument("--window", type=int, default=90, help="Analysis window in days.")
    return parser


def _force_utf8_stdout() -> None:
    """Make Unicode output safe on any console.

    The Windows console defaults to a legacy code page (cp1252), which cannot
    encode the ``↔`` and ``—`` characters this CLI prints, so ``validate``
    crashed with ``UnicodeEncodeError`` before printing its verdict. Python
    3.7+ exposes ``reconfigure`` on the standard streams; we switch them to
    UTF-8 with ``errors="replace"`` so output degrades to a placeholder glyph
    rather than aborting the command. No-op on platforms that already use
    UTF-8, and guarded for streams that don't support reconfigure (pytest's
    capture buffers, pipes).
    """
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except (ValueError, OSError):  # pragma: no cover - stream-specific
                pass


def main(argv: list[str] | None = None) -> int:
    from app.demo.design import DEMO_DAYS, DEMO_SEED

    _force_utf8_stdout()
    parser = build_parser()
    args = parser.parse_args(argv)
    args.seed = DEMO_SEED if args.seed is None else args.seed
    args.days = DEMO_DAYS if args.days is None else args.days

    handlers = {
        "seed": command_seed,
        "reset": command_seed,
        "clear": command_clear,
        "status": command_status,
        "validate": command_validate,
    }
    return handlers[args.command](args)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
