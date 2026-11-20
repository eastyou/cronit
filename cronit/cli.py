"""命令行入口：计算下次执行时间、校验、解释 cron 表达式。"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from typing import Optional, Sequence

from . import __version__
from .expression import (
    WEEKDAY_NAMES,
    CronError,
    parse_datetime,
    parse_expression,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cronit",
        description="cron 表达式工具：校验、中文解释、计算未来执行时间",
    )
    parser.add_argument("--version", action="version", version=__version__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    next_parser = subparsers.add_parser("next", help="计算接下来 N 次执行时间")
    next_parser.add_argument("expression", help="五字段 cron 表达式")
    next_parser.add_argument("-n", "--count", type=int, default=5, help="次数，默认 5")
    next_parser.add_argument(
        "--from", dest="start", default=None, help="起始时间，默认当前时间"
    )
    next_parser.add_argument("--json", action="store_true", help="JSON 输出")

    validate_parser = subparsers.add_parser("validate", help="校验表达式是否合法")
    validate_parser.add_argument("expression", help="五字段 cron 表达式")

    explain_parser = subparsers.add_parser("explain", help="用中文解释表达式")
    explain_parser.add_argument("expression", help="五字段 cron 表达式")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        expression = parse_expression(args.expression)
    except CronError as exc:
        print("错误: %s" % exc, file=sys.stderr)
        return 2

    if args.command == "validate":
        print("表达式合法: %s" % args.expression)
        print("含义: %s" % expression.describe())
        return 0

    if args.command == "explain":
        print("表达式: %s" % args.expression)
        print("含义: %s" % expression.describe())
        print("字段明细:")
        for name, raw, parsed in expression.field_rows():
            print("  %-4s %-12s -> %s" % (name, raw, parsed))
        return 0

    if args.command == "next":
        if not 1 <= args.count <= 1000:
            print("错误: 次数必须在 1-1000 之间", file=sys.stderr)
            return 2
        try:
            start = parse_datetime(args.start) if args.start else datetime.now()
        except ValueError as exc:
            print("错误: %s" % exc, file=sys.stderr)
            return 2
        try:
            runs = expression.next_runs(start, args.count)
        except CronError as exc:
            print("错误: %s" % exc, file=sys.stderr)
            return 1
        if args.json:
            print(
                json.dumps(
                    [run.isoformat() for run in runs],
                    ensure_ascii=False,
                    indent=2,
                )
            )
        else:
            for run in runs:
                weekday = WEEKDAY_NAMES[(run.weekday() + 1) % 7]
                print(
                    "%s  %s"
                    % (run.strftime("%Y-%m-%d %H:%M:%S"), weekday)
                )
        return 0

    print("错误: 未知命令", file=sys.stderr)
    return 2
