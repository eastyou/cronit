from __future__ import annotations

import io
import json
import unittest
from contextlib import redirect_stderr, redirect_stdout

from cronit.cli import main


class CliTest(unittest.TestCase):
    def run_cli(self, args):
        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = main(args)
        return code, stdout.getvalue(), stderr.getvalue()

    def test_next(self) -> None:
        code, output, _ = self.run_cli(
            ["next", "*/15 * * * *", "-n", "2", "--from", "2026-01-01 00:07"]
        )
        self.assertEqual(code, 0)
        self.assertIn("2026-01-01 00:15:00", output)
        self.assertIn("2026-01-01 00:30:00", output)

    def test_next_shows_weekday(self) -> None:
        code, output, _ = self.run_cli(
            ["next", "0 0 * * *", "-n", "1", "--from", "2026-11-20 12:00"]
        )
        self.assertEqual(code, 0)
        self.assertIn("2026-11-21 00:00:00", output)
        self.assertIn("周六", output)

    def test_next_json(self) -> None:
        code, output, _ = self.run_cli(
            ["next", "0 9 * * *", "-n", "1", "--from", "2026-01-01 10:00", "--json"]
        )
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(output), ["2026-01-02T09:00:00"])

    def test_validate(self) -> None:
        code, output, _ = self.run_cli(["validate", "@daily"])
        self.assertEqual(code, 0)
        self.assertIn("表达式合法", output)
        self.assertIn("含义", output)

    def test_explain(self) -> None:
        code, output, _ = self.run_cli(["explain", "0 9 * * MON-FRI"])
        self.assertEqual(code, 0)
        self.assertIn("字段明细", output)
        self.assertIn("周一至周五", output)

    def test_invalid_expression(self) -> None:
        code, _, stderr = self.run_cli(["validate", "* * *"])
        self.assertEqual(code, 2)
        self.assertIn("错误", stderr)

    def test_invalid_start_time(self) -> None:
        code, _, stderr = self.run_cli(["next", "* * * * *", "--from", "bad"])
        self.assertEqual(code, 2)
        self.assertIn("时间格式", stderr)

    def test_invalid_count(self) -> None:
        code, _, stderr = self.run_cli(["next", "* * * * *", "-n", "0"])
        self.assertEqual(code, 2)
        self.assertIn("次数", stderr)


if __name__ == "__main__":
    unittest.main()
