from __future__ import annotations

import unittest
from datetime import datetime

from cronit.expression import CronError, parse_datetime, parse_expression


class ParseTest(unittest.TestCase):
    def test_basic(self) -> None:
        expression = parse_expression("*/15 9-17 * * 1-5")
        self.assertEqual(sorted(expression.minutes), [0, 15, 30, 45])
        self.assertEqual(sorted(expression.hours), list(range(9, 18)))
        self.assertEqual(sorted(expression.weekdays), [1, 2, 3, 4, 5])
        self.assertEqual(len(expression.months), 12)

    def test_lists_and_names(self) -> None:
        expression = parse_expression("0 0 1,15 JAN,MAR MON")
        self.assertEqual(sorted(expression.days), [1, 15])
        self.assertEqual(sorted(expression.months), [1, 3])
        self.assertEqual(sorted(expression.weekdays), [1])

    def test_step_with_range(self) -> None:
        expression = parse_expression("0-20/5 * * * *")
        self.assertEqual(sorted(expression.minutes), [0, 5, 10, 15, 20])

    def test_step_from_start(self) -> None:
        expression = parse_expression("10/20 * * * *")
        self.assertEqual(sorted(expression.minutes), [10, 30, 50])

    def test_sunday_alias(self) -> None:
        self.assertEqual(sorted(parse_expression("0 0 * * 7").weekdays), [0])
        self.assertEqual(sorted(parse_expression("0 0 * * SUN").weekdays), [0])

    def test_aliases(self) -> None:
        self.assertEqual(
            parse_expression("@daily").raw, ("0", "0", "*", "*", "*")
        )
        self.assertEqual(
            parse_expression("@hourly").raw, ("0", "*", "*", "*", "*")
        )

    def test_invalid_field_count(self) -> None:
        with self.assertRaises(CronError):
            parse_expression("* * * *")

    def test_out_of_range(self) -> None:
        with self.assertRaises(CronError):
            parse_expression("60 * * * *")
        with self.assertRaises(CronError):
            parse_expression("* * 32 * *")
        with self.assertRaises(CronError):
            parse_expression("* * * 13 *")

    def test_invalid_step(self) -> None:
        with self.assertRaises(CronError):
            parse_expression("*/0 * * * *")
        with self.assertRaises(CronError):
            parse_expression("*/abc * * * *")

    def test_reversed_range(self) -> None:
        with self.assertRaises(CronError):
            parse_expression("10-5 * * * *")

    def test_invalid_token(self) -> None:
        with self.assertRaises(CronError):
            parse_expression("abc * * * *")

    def test_empty_list_item(self) -> None:
        with self.assertRaises(CronError):
            parse_expression("1,,2 * * * *")

    def test_empty_expression(self) -> None:
        with self.assertRaises(CronError):
            parse_expression("   ")

    def test_parse_datetime(self) -> None:
        self.assertEqual(
            parse_datetime("2026-11-20 08:30"), datetime(2026, 11, 20, 8, 30)
        )
        self.assertEqual(
            parse_datetime("2026-11-20 08:30:15"), datetime(2026, 11, 20, 8, 30, 15)
        )
        with self.assertRaises(ValueError):
            parse_datetime("2026/11/20")


class NextRunsTest(unittest.TestCase):
    def test_every_five_minutes(self) -> None:
        expression = parse_expression("*/5 * * * *")
        runs = expression.next_runs(datetime(2026, 1, 1, 0, 2), 3)
        self.assertEqual(
            runs,
            [
                datetime(2026, 1, 1, 0, 5),
                datetime(2026, 1, 1, 0, 10),
                datetime(2026, 1, 1, 0, 15),
            ],
        )

    def test_weekday_morning(self) -> None:
        expression = parse_expression("30 9 * * 1-5")
        runs = expression.next_runs(datetime(2026, 11, 20, 10, 0), 1)
        self.assertEqual(runs[0], datetime(2026, 11, 23, 9, 30))

    def test_month_end(self) -> None:
        expression = parse_expression("0 0 31 * *")
        runs = expression.next_runs(datetime(2026, 4, 1), 1)
        self.assertEqual(runs[0], datetime(2026, 5, 31))

    def test_leap_day(self) -> None:
        expression = parse_expression("0 0 29 2 *")
        runs = expression.next_runs(datetime(2025, 1, 1), 1)
        self.assertEqual(runs[0], datetime(2028, 2, 29))

    def test_day_or_weekday(self) -> None:
        expression = parse_expression("0 0 13 * 5")
        runs = expression.next_runs(datetime(2026, 11, 1), 2)
        self.assertEqual(runs[0], datetime(2026, 11, 6))
        self.assertEqual(runs[1], datetime(2026, 11, 13))

    def test_impossible_date(self) -> None:
        expression = parse_expression("0 0 30 2 *")
        with self.assertRaises(CronError):
            expression.next_runs(datetime(2026, 1, 1), 1)

    def test_invalid_count(self) -> None:
        with self.assertRaises(ValueError):
            parse_expression("* * * * *").next_runs(datetime(2026, 1, 1), 0)

    def test_matches(self) -> None:
        expression = parse_expression("0 12 * * *")
        self.assertTrue(expression.matches(datetime(2026, 1, 1, 12, 0)))
        self.assertFalse(expression.matches(datetime(2026, 1, 1, 12, 1)))


class DescribeTest(unittest.TestCase):
    def test_every_five_minutes(self) -> None:
        text = parse_expression("*/5 * * * *").describe()
        self.assertIn("每天", text)
        self.assertIn("每 5 分钟", text)

    def test_weekday_schedule(self) -> None:
        text = parse_expression("0 9 * * MON-FRI").describe()
        self.assertIn("周一至周五", text)
        self.assertIn("9点00分", text)

    def test_day_of_month(self) -> None:
        text = parse_expression("0 0 1 * *").describe()
        self.assertIn("每月 1日", text)

    def test_month_restricted(self) -> None:
        text = parse_expression("0 0 29 2 *").describe()
        self.assertIn("每年 2月", text)
        self.assertIn("29日", text)

    def test_field_rows(self) -> None:
        rows = parse_expression("*/15 9-10 * * *").field_rows()
        self.assertEqual(rows[0][0], "分钟")
        self.assertEqual(rows[0][2], "0、15、30、45")
        self.assertEqual(rows[1][2], "9点、10点")


if __name__ == "__main__":
    unittest.main()
