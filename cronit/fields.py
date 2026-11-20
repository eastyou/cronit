"""单个 cron 字段的解析与校验。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, FrozenSet, Mapping, Set


class CronError(ValueError):
    """cron 表达式非法。"""


@dataclass(frozen=True)
class FieldSpec:
    """一个字段的取值范围与允许的英文别名。"""

    name: str
    minimum: int
    maximum: int
    names: Mapping[str, int] = field(default_factory=dict)


MINUTE = FieldSpec("分钟", 0, 59)
HOUR = FieldSpec("小时", 0, 23)
DAY_OF_MONTH = FieldSpec("日", 1, 31)
MONTH = FieldSpec(
    "月",
    1,
    12,
    {
        "JAN": 1,
        "FEB": 2,
        "MAR": 3,
        "APR": 4,
        "MAY": 5,
        "JUN": 6,
        "JUL": 7,
        "AUG": 8,
        "SEP": 9,
        "OCT": 10,
        "NOV": 11,
        "DEC": 12,
    },
)
DAY_OF_WEEK = FieldSpec(
    "星期",
    0,
    7,
    {
        "SUN": 0,
        "MON": 1,
        "TUE": 2,
        "WED": 3,
        "THU": 4,
        "FRI": 5,
        "SAT": 6,
    },
)


def _value(token: str, spec: FieldSpec) -> int:
    cleaned = token.strip().upper()
    if not cleaned:
        raise CronError("%s字段存在空值" % spec.name)
    if cleaned in spec.names:
        return spec.names[cleaned]
    if not cleaned.isdigit():
        raise CronError("%s字段包含非法值: %s" % (spec.name, token))
    number = int(cleaned)
    if not spec.minimum <= number <= spec.maximum:
        raise CronError(
            "%s字段超出范围 %d-%d: %s"
            % (spec.name, spec.minimum, spec.maximum, token)
        )
    return number


def _parse_chunk(chunk: str, spec: FieldSpec) -> Set[int]:
    base = chunk
    step = 1
    has_step = "/" in chunk
    if has_step:
        base, _, step_text = chunk.partition("/")
        if not step_text.isdigit() or int(step_text) <= 0:
            raise CronError("%s字段的步长必须是正整数: %s" % (spec.name, chunk))
        step = int(step_text)

    if base == "*":
        start = spec.minimum
        end = spec.maximum
    elif "-" in base:
        left, _, right = base.partition("-")
        start = _value(left, spec)
        end = _value(right, spec)
        if start > end:
            raise CronError(
                "%s字段的范围起点大于终点: %s" % (spec.name, chunk)
            )
    else:
        start = _value(base, spec)
        end = spec.maximum if has_step else start

    return set(range(start, end + 1, step))


def parse_field(raw: str, spec: FieldSpec) -> FrozenSet[int]:
    """解析一个字段，支持 ``*``、``a``、``a-b``、``*/n``、``a-b/n`` 与逗号列表。"""
    if not raw:
        raise CronError("%s字段不能为空" % spec.name)
    values: Set[int] = set()
    for chunk in raw.split(","):
        if not chunk:
            raise CronError("%s字段存在空的列表项: %s" % (spec.name, raw))
        values |= _parse_chunk(chunk, spec)
    if not values:
        raise CronError("%s字段没有解析出任何值" % spec.name)
    if spec is DAY_OF_WEEK:
        # cron 里 0 和 7 都表示周日，统一成 0。
        values = {0 if value == 7 else value for value in values}
    return frozenset(values)
