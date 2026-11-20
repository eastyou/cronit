# cronit

[![CI](https://github.com/eastyou/cronit/actions/workflows/ci.yml/badge.svg)](https://github.com/eastyou/cronit/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.9%2B-brightgreen.svg)](pyproject.toml)

一个零依赖的 cron 表达式工具：校验写法、用中文解释含义、算出接下来 N 次执行时间。支持标准五字段语法、英文月份/星期缩写与 `@daily` 等别名。

写定时任务时最怕两件事：表达式写错了没人发现，以及「下次到底什么时候跑」全靠脑补。`cronit` 把这两件事变成一条命令。

## 特性

- **完整五字段语法**：`*`、`5`、`1-5`、`*/15`、`1-30/5`、逗号列表，全部支持
- **英文别名**：`JAN-DEC`、`SUN-SAT`，`0` 和 `7` 都表示周日
- **常用别名**：`@hourly` `@daily` `@midnight` `@weekly` `@monthly` `@yearly`
- **下次执行时间**：按字段跳跃搜索（月→日→时→分），不会逐分钟空转
- **中文解释**：把 `0 9 * * MON-FRI` 翻译成「每周 周一至周五，9点00分 执行」
- **边界处理**：月底、闰年 2 月 29 日、「日」与「星期」同时受限时的并集语义
- **35 个单元测试**：解析、非法输入、跨月跨年、闰年、CLI 输出

## 安装

```bash
pip install "git+https://github.com/eastyou/cronit.git"
```

或本地开发：

```bash
git clone https://github.com/eastyou/cronit.git
cd cronit
python3 -m pip install -e .
```

不安装也能跑：`python3 -m cronit --help`

## 使用

### 计算下次执行时间

```console
$ cronit next "0 9 * * MON-FRI" -n 3 --from "2026-11-20 12:00"
2026-11-23 09:00:00  周一
2026-11-24 09:00:00  周二
2026-11-25 09:00:00  周三
```

`--from` 省略时以当前时间为起点；`--json` 输出 ISO 时间数组，便于脚本消费。

### 校验表达式

```console
$ cronit validate "*/15 * * * *"
表达式合法: */15 * * * *
含义: 每天，每 15 分钟 执行
```

非法表达式会说明原因并返回退出码 2：

```console
$ cronit validate "60 * * * *"
错误: 分钟字段超出范围 0-59: 60
```

### 解释字段

```console
$ cronit explain "0 9 * * MON-FRI"
表达式: 0 9 * * MON-FRI
含义: 每周 周一至周五，9点00分 执行
字段明细:
  分钟   0            -> 0
  小时   9            -> 9点
  日    *            -> 1日至31日
  月    *            -> 1月至12月
  星期   MON-FRI      -> 周一至周五
```

### 参数

| 命令 | 参数 | 说明 |
| --- | --- | --- |
| `next` | `-n, --count` | 计算次数，默认 5 |
| `next` | `--from` | 起始时间，格式 `YYYY-MM-DD HH:MM[:SS]` |
| `next` | `--json` | 输出 JSON 数组 |
| `validate` | — | 校验并输出含义 |
| `explain` | — | 输出含义与字段明细 |

### 退出码

| 退出码 | 含义 |
| --- | --- |
| `0` | 成功 |
| `1` | 未来 8 年内没有匹配时间（例如 2 月 30 日） |
| `2` | 表达式、时间或参数非法 |

## 语义说明

- 五个字段依次是：分钟、小时、日、月、星期
- 星期采用 cron 惯例：`0` = 周日，`1` = 周一……`6` = 周六，`7` 等同 `0`
- 「日」与「星期」都不是 `*` 时，按标准 cron 语义取**并集**：任一匹配即执行
- 计算结果为本地时区的朴素 `datetime`，暂不处理夏令时（DST）跳变
- 只支持五字段；秒级与年份字段不在范围内

## 实现要点

```
cronit/
├── fields.py      单字段解析：范围、步长、列表、别名
├── expression.py  五字段组合、下次执行时间、中文描述
└── cli.py         命令行入口
```

下次时间的搜索不是逐分钟暴力枚举，而是逐层跳过：

1. 月份不匹配 → 直接跳到下个月 1 日 0 点
2. 日期不匹配 → 跳到下一天 0 点
3. 小时不匹配 → 跳到下一个整点
4. 分钟不匹配 → 加 1 分钟

因此 `0 0 29 2 *` 这种四年一次的表达式也能瞬间算出结果；搜索上限设为 8 年，覆盖所有闰年组合。

## 开发与测试

```bash
python3 -m unittest discover -s tests -v
```

CI 覆盖 Python 3.9 ~ 3.13 与三大操作系统。

## License

[MIT](LICENSE) © 2026 eastyou
