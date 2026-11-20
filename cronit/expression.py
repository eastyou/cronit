"""cron 表达式：解析、下次执行时间计算、中文说明。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Iterable, List, Optional, Sequence, Tuple

from .fields import (
    DAY_OF_MONTH,
    DAY_OF_WEEK,
    HOUR,
    MINUTE,
    MONTH,
    CronError,
    parse_field,
)

ALIASES = {
    "@yearly": "0 0 1 1 *",
    "@annually": "0 0 1 1 *",
    "@monthly": "0 0 1 * *",
    "@weekly": "0 0 * * 0",
    "@daily": "0 0 * * *",
    "@midnight": "0 0 * * *",
    "@hourly": "0 * * * *",
}

WEEKDAY_NAMES = ("周日", "周一", "周二", "周三", "周四", "周五", "周六")
MAX_SEARCH = timedelta(days=366 * 8)


def _runs(values: Sequence[int]) -> List[Tuple[int, int]]:
    """把递增序列压缩成连续区间。"""
    if not values:
        return []
    ranges: List[Tuple[int, int]] = []
    start = previous = values[0]
    for value in values[1:]:
        if value == previous + 1:
            previous = value
            continue
        ranges.append((start, previous))
        start = previous = value
    ranges.append((start, previous))
    return ranges


def _format_numbers(values: Iterable[int], unit: str = "") -> str:
    parts: List[str] = []
    for start, end in _runs(sorted(values)):
        if start == end:
            parts.append("%d%s" % (start, unit))
        elif end == start + 1:
            parts.append("%d%s、%d%s" % (start, unit, end, unit))
        else:
            parts.append("%d%s至%d%s" % (start, unit, end, unit))
    return "、".join(parts)


def _format_weekdays(values: Iterable[int]) -> str:
    parts: List[str] = []
    for start, end in _runs(sorted(values)):
        if start == end:
            parts.append(WEEKDAY_NAMES[start])
        elif end == start + 1:
            parts.append(WEEKDAY_NAMES[start] + "、" + WEEKDAY_NAMES[end])
        else:
            parts.append(WEEKDAY_NAMES[start] + "至" + WEEKDAY_NAMES[end])
    return "、".join(parts)


@dataclass(frozen=True)
class CronExpression:
    """解析完成的五字段 cron 表达式。"""

    raw: Tuple[str, str, str, str, str]
    minutes: frozenset
    hours: frozenset
    days: frozenset
    months: frozenset
    weekdays: frozenset

    def matches(self, moment: datetime) -> bool:
        """判断某个时刻是否匹配（精确到分钟）。"""
        if moment.minute not in self.minutes or moment.hour not in self.hours:
            return False
        if moment.month not in self.months:
            return False
        return self._day_matches(moment)

    def next_runs(self, start: datetime, count: int = 5) -> List[datetime]:
        """返回严格晚于 ``start`` 的下 ``count`` 次执行时间。"""
        if count <= 0:
            raise ValueError("count 必须大于 0")
        results: List[datetime] = []
        cursor = start
        for _ in range(count):
            cursor = self._next_after(cursor)
            results.append(cursor)
        return results

    def describe(self) -> str:
        """用中文概括执行规律。"""
        day_text = self._day_text()
        month_star = self.raw[3] == "*"
        month_phrase = _format_numbers(self.months, "月")
        if month_star:
            date_text = day_text
        elif self.raw[2] == "*" and self.raw[4] == "*":
            date_text = "每年 %s 的每天" % month_phrase
        elif self.raw[4] == "*":
            date_text = "每年 %s 的 %s" % (
                month_phrase,
                _format_numbers(self.days, "日"),
            )
        elif self.raw[2] == "*":
            date_text = "每年 %s 的每周 %s" % (
                month_phrase,
                _format_weekdays(self.weekdays),
            )
        else:
            date_text = "每年 %s 的 %s 日或每周 %s" % (
                month_phrase,
                _format_numbers(self.days),
                _format_weekdays(self.weekdays),
            )
        return "%s，%s 执行" % (date_text, self._time_text())

    def field_rows(self) -> List[Tuple[str, str, str]]:
        """返回 ``(字段, 原始值, 解析结果)``，供命令行展示。"""
        return [
            ("分钟", self.raw[0], _format_numbers(self.minutes)),
            ("小时", self.raw[1], _format_numbers(self.hours, "点")),
            ("日", self.raw[2], _format_numbers(self.days, "日")),
            ("月", self.raw[3], _format_numbers(self.months, "月")),
            ("星期", self.raw[4], _format_weekdays(self.weekdays)),
        ]

    # ---- 内部实现 ----

    def _day_matches(self, moment: datetime) -> bool:
        dom_ok = moment.day in self.days
        cron_weekday = (moment.weekday() + 1) % 7
        dow_ok = cron_weekday in self.weekdays
        dom_star = self.raw[2] == "*"
        dow_star = self.raw[4] == "*"
        if dom_star and dow_star:
            return True
        if dom_star:
            return dow_ok
        if dow_star:
            return dom_ok
        # 标准 cron：日与星期都受限时取并集。
        return dom_ok or dow_ok

    def _next_after(self, start: datetime) -> datetime:
        candidate = start.replace(second=0, microsecond=0) + timedelta(minutes=1)
        limit = candidate + MAX_SEARCH
        while candidate <= limit:
            if candidate.month not in self.months:
                candidate = _first_of_next_month(candidate)
                continue
            if not self._day_matches(candidate):
                candidate = (candidate + timedelta(days=1)).replace(
                    hour=0, minute=0
                )
                continue
            if candidate.hour not in self.hours:
                candidate = (candidate + timedelta(hours=1)).replace(minute=0)
                continue
            if candidate.minute not in self.minutes:
                candidate += timedelta(minutes=1)
                continue
            return candidate
        raise CronError("未来 8 年内没有匹配的执行时间")

    def _minute_phrase(self) -> str:
        raw = self.raw[0]
        if raw.startswith("*/") and "," not in raw:
            return "每 %s 分钟" % raw[2:]
        if raw == "*":
            return "每一分钟"
        return "第 %s 分钟" % _format_numbers(self.minutes)

    def _hour_phrase(self) -> str:
        raw = self.raw[1]
        if raw.startswith("*/") and "," not in raw:
            return "每 %s 小时" % raw[2:]
        if raw == "*":
            return "每小时"
        return _format_numbers(self.hours, "点")

    def _time_text(self) -> str:
        hour_raw = self.raw[1]
        minute_raw = self.raw[0]
        if hour_raw == "*" and minute_raw == "*":
            return "每分钟"
        if hour_raw == "*":
            return self._minute_phrase()
        if minute_raw == "*":
            return "%s的每一分钟" % self._hour_phrase()
        if len(self.hours) == 1 and len(self.minutes) == 1:
            hour = next(iter(self.hours))
            minute = next(iter(self.minutes))
            return "%d点%02d分" % (hour, minute)
        return "%s %s" % (self._hour_phrase(), self._minute_phrase())

    def _day_text(self) -> str:
        dom_star = self.raw[2] == "*"
        dow_star = self.raw[4] == "*"
        if dom_star and dow_star:
            return "每天"
        if dom_star:
            return "每周 %s" % _format_weekdays(self.weekdays)
        if dow_star:
            return "每月 %s" % _format_numbers(self.days, "日")
        return "每月 %s 日或每周 %s" % (
            _format_numbers(self.days),
            _format_weekdays(self.weekdays),
        )


def _first_of_next_month(moment: datetime) -> datetime:
    if moment.month == 12:
        return datetime(moment.year + 1, 1, 1)
    return datetime(moment.year, moment.month + 1, 1)


def parse_expression(text: str) -> CronExpression:
    """解析五字段 cron 表达式，支持 ``@daily`` 等别名。"""
    if not isinstance(text, str):
        raise CronError("表达式必须是字符串")
    cleaned = text.strip()
    if not cleaned:
        raise CronError("表达式不能为空")
    lowered = cleaned.lower()
    if lowered in ALIASES:
        cleaned = ALIASES[lowered]
    fields = cleaned.split()
    if len(fields) != 5:
        raise CronError("需要 5 个字段（分 时 日 月 周），实际为 %d 个" % len(fields))
    return CronExpression(
        raw=(fields[0], fields[1], fields[2], fields[3], fields[4]),
        minutes=parse_field(fields[0], MINUTE),
        hours=parse_field(fields[1], HOUR),
        days=parse_field(fields[2], DAY_OF_MONTH),
        months=parse_field(fields[3], MONTH),
        weekdays=parse_field(fields[4], DAY_OF_WEEK),
    )


def parse_datetime(text: str) -> datetime:
    """解析命令行传入的时间，支持三种常见格式。"""
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    raise ValueError("时间格式应为 YYYY-MM-DD HH:MM 或 YYYY-MM-DD HH:MM:SS")
