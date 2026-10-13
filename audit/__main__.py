"""CLI:
    python -m audit generate --rows 5000000      # sintetik ma'lumot yaratish
    python -m audit run                          # Spark tahlili + hisobot
"""
from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="audit")
    sub = p.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("generate")
    g.add_argument("--rows", type=int, default=5_000_000)
    g.add_argument("--out", type=Path, default=ROOT / "data")
    r = sub.add_parser("run")
    r.add_argument("--data", type=Path, default=ROOT / "data")
    r.add_argument("--out", type=Path, default=ROOT / "output")
    args = p.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    if args.cmd == "generate":
        from audit.generate import generate
        t0 = time.time()
        info = generate(args.out, rows=args.rows)
        print(f"Yaratildi: {info['contracts']:,} shartnoma, {info['payments']:,} to'lov -> {info['path']} "
              f"({time.time() - t0:.0f} s)")
        return 0

    from audit.job import run
    from audit.report import write_report
    from audit.spark import get_spark
    spark = get_spark()
    spark.sparkContext.setLogLevel("ERROR")
    try:
        res = run(spark, args.data, args.out)
    finally:
        spark.stop()
    write_report(res, args.out / "report.md")
    print(f"\nTayyor: {res.contracts_total:,} shartnoma {res.seconds} s da tahlil qilindi.")
    print(f"Jiddiy xavfli shartnomalar: {len(res.flagged_contracts):,}; hisobot: {args.out / 'report.md'}")
    if res.evaluation is not None:
        print(res.evaluation.to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
