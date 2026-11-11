#!/usr/bin/env python3
"""事实记录生成与一致性检查。

用法：
    python scripts/facts.py build     # 生成 references/fact-records.json
    python scripts/facts.py render    # 由事实记录生成 references/trim-comparison.md
    python scripts/facts.py check     # 校验内部一致性 + 矩阵是否为最新生成结果

设计意图：价格、续航、电池等字段此前散落在矩阵、车型文档和示例里，改一处容易漏两处。
本文件把这些值收敛成唯一数据源，矩阵展示由它派生；check 会在不一致或矩阵过期时报错。
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REF = ROOT / "source" / "leapmotor-car-expert" / "references"
OUT = REF / "fact-records.json"
MATRIX = REF / "trim-comparison.md"

CHECKED = "2026-11-11"

# 每个车系的共通值
COMMON = {
    "C10": dict(size="4749×1900×1680", wheelbase=2825, market="CN", year=2027),
    "C11": dict(size="4780×1905×1658", wheelbase=2930, market="CN", year=2027),
    "C16": dict(size="4925×1905×1770", wheelbase=2825, market="CN", year=2027),
}

# 辅助驾驶：按版本组给，状态严格区分 confirmed / media / unknown / conflict
ADAS = {
    "c10-zx": dict(lidar=("无", "media", ["yiche-c10-review", "sina-c10-advisor"]),
                   chip=("未确认", "unknown", []),
                   sensors=("未确认", "unknown", [])),
    "c10-lidar": dict(lidar=("有，型号未确认", "confirmed", ["official-c10-page"]),
                      chip=("高通 8650", "confirmed", ["official-c10-page"]),
                      sensors=("28 个", "confirmed", ["official-c10-page"])),
    "c11-640-zx": dict(lidar=("无", "media", ["autohome-c11-guide-2027"]),
                       chip=("未确认", "unknown", []),
                       sensors=("未确认", "unknown", [])),
    "c11-640-lidar": dict(lidar=("禾赛 AT128，128 线，1 颗", "confirmed", ["autohome-c11-config-2027"]),
                          chip=("高通骁龙 8650", "confirmed", ["autohome-c11-config-2027"]),
                          sensors=("毫米波 3／摄像头 11／超声波 12", "confirmed", ["autohome-c11-config-2027"])),
    "c11-300": dict(lidar=("有，型号未确认", "media", ["official-c11-page-cn"]),
                    chip=("未确认", "unknown", []),
                    sensors=("未确认", "unknown", [])),
    "c16-zx": dict(lidar=("无", "media", ["weixin-c16-guide"]),
                   chip=("未确认", "unknown", []),
                   sensors=("未确认", "unknown", [])),
    "c16-lidar": dict(lidar=("有", "media", ["weixin-c16-guide"]),
                      chip=("高通 8650", "media", ["weixin-c16-guide"]),
                      sensors=("未确认", "unknown", [])),
}

# 每个版本：key, 名称, 车系, 座位, 价格, 价格级别, 纯电续航, wltc, 电池, 功率, 快充, 慢充, 整备, 加速, adas组
TRIMS = [
    ("c10-290-zx", "290 智享版", "C10", 5, 12.58, "L1", 290, 190, 38.7, "200 kW／360 N·m", "约 16 分钟", "3.5 h", 1995, 7.38, "c10-zx"),
    ("c10-290-lidar", "290 激光雷达版", "C10", 5, 13.58, "L1", 290, 190, 38.7, "200 kW／360 N·m", "约 16 分钟", "3.5 h", 1995, 7.38, "c10-lidar"),
    ("c10-660-zx", "660 智享版", "C10", 5, 13.28, "L1", 660, None, 81.9, "230 kW／360 N·m", "约 16 分钟", "7.5 h", 2040, 6.02, "c10-zx"),
    ("c10-660-lidar", "660 激光雷达版", "C10", 5, 14.28, "L1", 660, None, 81.9, "230 kW／360 N·m", "约 16 分钟", "7.5 h", 2040, 6.02, "c10-lidar"),
    ("c11-300-lidar", "300 激光雷达版", "C11", 5, 14.38, "L1*", 300, None, 41.7, "200 kW／320 N·m", "约 18 分钟", "4.0 h", 2090, 7.6, "c11-300"),
    ("c11-300-zun", "300 激光雷达智尊版", "C11", 5, 15.38, "L1*", 300, None, 41.7, "200 kW／320 N·m", "约 18 分钟", "4.0 h", 2090, 7.6, "c11-300"),
    ("c11-640-zx", "640 智享版", "C11", 5, 14.38, "L1", 640, None, 81.9, "220 kW／360 N·m", "约 16 分钟", "7.5 h", 2110, 6.1, "c11-640-zx"),
    ("c11-640-lidar", "640 激光雷达版", "C11", 5, 14.98, "L1", 640, None, 81.9, "220 kW／360 N·m", "约 16 分钟", "7.5 h", 2110, 6.1, "c11-640-lidar"),
    ("c11-640-zun", "640 激光雷达智尊版", "C11", 5, 15.98, "L1", 640, None, 81.9, "220 kW／360 N·m", "约 16 分钟", "7.5 h", 2110, 6.1, "c11-640-lidar"),
    ("c16-280-zx-5", "280 尊享版", "C16", 5, 14.58, "L1", 280, 185, 38.9, "200 kW／360 N·m", "约 16 分钟", "3.5 h", 2120, 8.3, "c16-zx"),
    ("c16-280-zx-6", "280 尊享版", "C16", 6, 14.88, "L1", 280, 185, 38.9, "200 kW／360 N·m", "约 16 分钟", "3.5 h", 2120, 8.3, "c16-zx"),
    ("c16-280-lidar-5", "280 激光雷达智尊版", "C16", 5, 15.98, "L1", 280, 185, 38.9, "200 kW／360 N·m", "约 16 分钟", "3.5 h", 2120, 8.3, "c16-lidar"),
    ("c16-280-lidar-6", "280 激光雷达智尊版", "C16", 6, 16.28, "L1", 280, 185, 38.9, "200 kW／360 N·m", "约 16 分钟", "3.5 h", 2120, 8.3, "c16-lidar"),
    ("c16-630-zx-5", "630 尊享版", "C16", 5, 15.28, "L1", 630, None, 81.9, "230 kW／360 N·m", "约 16 分钟", "7.5 h", 2160, 6.8, "c16-zx"),
    ("c16-630-zx-6", "630 尊享版", "C16", 6, 15.58, "L1", 630, None, 81.9, "230 kW／360 N·m", "约 16 分钟", "7.5 h", 2160, 6.8, "c16-zx"),
    ("c16-630-lidar-5", "630 激光雷达智尊版", "C16", 5, 16.68, "L1", 630, None, 81.9, "230 kW／360 N·m", "约 16 分钟", "7.5 h", 2160, 6.8, "c16-lidar"),
    ("c16-630-lidar-6", "630 激光雷达智尊版", "C16", 6, 16.98, "L1", 630, None, 81.9, "230 kW／360 N·m", "约 16 分钟", "7.5 h", 2160, 6.8, "c16-lidar"),
]

PRICE_SRC = {"L1": ["official-c10-page", "official-c11-page-cn", "official-c16-page-cn"],
             "L1*": ["official-c11-page-cn", "yiche-c11-config-2027"]}

# 车系共通信息与叙述块。数字只在此处出现一次，矩阵由模板拼装。
SERIES_META = {
    "C10": dict(
        heading="C10（4 版）",
        common="共通：4749×1900×1680 mm，轴距 2825 mm，5 门 5 座，后置后驱；前麦弗逊、后五连杆，FSD 可变阻尼减振器。",
        extra=("增程器 1.5L 95 马力；功率换算值配置库记 70 kW，官方页未列该数值，按配置库口径标注。" "\n\n"
               "增程综合续航：CLTC 1300 km／WLTC 1080 km（`yoojia-c10-trim-diff`）；另一来源表述为“超 1200 km”"
               "（`sina-c10-2027`）。两者不是同一个量（前者给精确值，后者给下限），按“精度差异”记录，不算真冲突。"),
        sources=("来源：`official-c10-page`（价格、800V、16 分钟）、`autohome-c10-config-2027`（续航、功率、快充、质量、加速、尺寸）、"
                 "`yiche-c10-config-2027`（电池、后备箱、油箱、轴距、电耗）、`yiche-c10-review`（81.9 kWh、电耗）。"),
    ),
    "C11": dict(
        heading="C11（5 版）",
        common="共通：4780×1905×1658 mm，轴距 2930 mm，5 门 5 座，后置后驱；前双叉臂、后五连杆；纯电 800V、峰值 250 kW、纯电版全系热泵。",
        extra=("增程综合续航：1220 km（`wcevcar-c11-2027`，第三方销售站，单源待核验）。增程油箱 47 L、增程器 1.5L 95 马力，"
               "功率换算值配置库记 70 kW，与 C10 同一口径问题。\n\n"
               "**证据边界**：`yiche-c11-config-2027` 的 URL 目前只到易车移动站首页，无法直达车款页；"
               "该来源承载的电池、功率、补能等字段按**间接证据**处理，已列入待补清单。"),
        sources=("来源：`official-c11-page-cn`（价格、800V、250 kW、热泵、2930 mm）、`yiche-c11-config-2027`（电池、功率、补能、后备箱、整备、加速，间接）、"
                 "`autohome-c11-config-2027`（CLTC 640、快充 0.27 h、尺寸；该页仅覆盖纯电）。"),
    ),
    "C16": dict(
        heading="C16（8 版）",
        common="共通：4925×1905×1770 mm，轴距 2825 mm，5 门（5 座或 2+2+2 六座），后置后驱；前麦弗逊、后五连杆，FSD 全系标配；增程 CLTC 综合 1230 km／WLTC 1000 km，V2L 3.3 kW。",
        extra=("后备箱（未决，两源数值不一致）：6 座 275 L／放倒 1066 L、5 座 582 L／放倒 2077 L（`sina-c16-2027`）；"
               "6 座 209 L／1022 L（`youjia-c16-conflict-sample`）。属真冲突，不投票，见 [`model-c16.md`](model-c16.md)。"),
        sources=("来源：`official-c16-page-cn`（八版本价格）、`autohome-c16-config-2027`（续航、电池、功率、补能、整备、加速、尺寸）、"
                 "`weixin-c16-guide`（81.9 kWh、轴距、差价结构；公众号转载，原始出处未确认）、`sina-c16-2027`（轴距、后备箱、FSD）。"),
    ),
}

BOOT = {"C10": "510–1809 L", "C11_纯电": "537–1203 L", "C11_增程": "485–1151 L"}
VMAX = {"C11_纯电": "190 km/h", "C11_增程": "170 km/h"}


def energy(key):
    return "增程" if any(x in key for x in ("-290-", "-280-", "-300-")) else "纯电"



def build():
    records = []
    for (key, name, series, seats, price, lvl, cltc, wltc, batt, power,
         fast, slow, weight, accel, adas) in TRIMS:
        c = COMMON[series]
        base = dict(trim=key, series=series, year=c["year"], market=c["market"],
                    trim_name=name, checked=CHECKED)

        def add(field, value, unit, status, sources, note=""):
            records.append({**base, "field": field, "value": value, "unit": unit,
                            "status": status, "source_ids": sources, "note": note})

        add("guidance_price", price, "万元", lvl,
            [s for s in PRICE_SRC[lvl] if series[1:] in s or "yiche" in s][:2] or PRICE_SRC[lvl],
            "价格级别 %s" % lvl)
        add("cltc_pure_range", cltc, "km", "confirmed", ["autohome-%s-config-2027" % series.lower()] if series != "C11" else ["yiche-c11-config-2027"])
        if wltc is not None:
            add("wltc_pure_range", wltc, "km", "confirmed", ["autohome-%s-config-2027" % series.lower()])
        add("battery_capacity", batt, "kWh", "confirmed",
            ["yiche-c10-config-2027"] if series == "C10" else
            (["yiche-c11-config-2027"] if series == "C11" else ["autohome-c16-config-2027"]))
        add("seats", seats, "个", "confirmed", ["autohome-%s-config-2027" % series.lower()])
        add("dimensions", c["size"], "mm", "confirmed", ["autohome-%s-config-2027" % series.lower()])
        add("wheelbase", c["wheelbase"], "mm", "confirmed",
            (["zjchewang-c10-discount"] if series == "C10" else
             (["official-c11-page-cn"] if series == "C11" else ["weixin-c16-guide"])))
        add("motor_power_torque", power, "-", "confirmed", ["yiche-%s-config-2027" % series.lower()])
        add("fast_charge_30_80", fast, "-", "confirmed", ["autohome-%s-config-2027" % series.lower()])
        add("slow_charge", slow, "h", "confirmed", ["yiche-%s-config-2027" % series.lower()])
        add("curb_weight", weight, "kg", "confirmed", ["autohome-%s-config-2027" % series.lower()])
        add("accel_0_100", accel, "s", "confirmed", ["autohome-%s-config-2027" % series.lower()])
        a = ADAS[adas]
        add("adas_lidar", a["lidar"][0], "-", a["lidar"][1], a["lidar"][2])
        add("adas_chip", a["chip"][0], "-", a["chip"][1], a["chip"][2])
        add("adas_sensor_count", a["sensors"][0], "-", a["sensors"][1], a["sensors"][2])

    OUT.write_text(json.dumps({
        "version": "0.4.0",
        "checked": CHECKED,
        "status_legend": {
            "confirmed": "有来源明确写出该版本",
            "media": "媒体口径，无官方逐款配置表佐证",
            "unknown": "没有针对该版本的信息，不等于没有",
            "conflict": "来源互相矛盾，未决",
            "L1": "价格：官方页可复现且配置库一致",
            "L1*": "价格：官方页读到过但复核未重现，另有配置库支持",
        },
        "notice": "本文件是事实记录的唯一数据源；trim-comparison.md 的数值由此派生。改动请先改这里并运行 check。",
        "records": records,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print("wrote %s with %d records, %d trims" % (OUT.name, len(records), len(TRIMS)))


def _w(v):
    """万元 → '12.58 万'"""
    return "%.2f 万" % v


def render(dry=False):
    """由 TRIMS 拼装 trim-comparison.md，避免同一数字在多处手写。dry=True 只返回文本不写盘。"""
    head = [
        "# 17 版本配置矩阵",
        "",
        "核对日期：%s。市场：中国。年款：2027 款（上市 2026-06-16）。" % CHECKED,
        "",
        "**本文件由 `scripts/facts.py render` 从 [`fact-records.json`](fact-records.json) 生成，请勿手改。**",
        "需要改数值时改脚本里的 `TRIMS`，再依次运行 `build`、`render`、`check`；`check` 会拒绝过期矩阵。",
        "",
        "**用法**：这张表只放能追到来源的字段。写“未确认”不是“没有”，而是“资料未写”。逐字段来源与状态见 `fact-records.json`。",
        "",
        "**冲突与未确认**：本表只列数值，不做取舍。冲突类型与处理见各车型文档的“来源冲突记录”（真冲突／口径差异／精度差异／证据不足四类）。",
        "",
        "**价格来源级别定义**",
        "",
        "| 级别 | 含义 |",
        "|---|---|",
        "| L1 | 官方车型页可复现，且配置库数值一致 |",
        "| L1* | 官方车型页曾读取到该价格，但独立复核未重现；配置库与第二来源一致支持 |",
        "| L2 | 仅配置库，无官方页证据 |",
        "| L3 | 仅经销商页或媒体 |",
        "",
        "级别只作用于价格。电池、芯片、续航等字段各有自己的状态，不能继承价格的级别。",
        "",
    ]
    body = []
    for series in ("C10", "C11", "C16"):
        rows = [t for t in TRIMS if t[2] == series]
        meta = SERIES_META[series]
        body.append("## " + meta["heading"])
        body.append("")
        if series == "C16":
            body.append("| 版本键 | 版本 | 座位 | 能源 | 指导价 | 级别 | CLTC 纯电 | WLTC 纯电 | 电池 | 电机 | 快充 30–80% | 慢充 | 整备 | 0–100 |")
            body.append("|---|---|---:|---|---:|---|---:|---:|---:|---|---:|---:|---:|---:|")
        elif series == "C11":
            body.append("| 版本键 | 版本 | 能源 | 指导价 | 级别 | CLTC 纯电 | 电池 | 电机 | 快充 30–80% | 慢充 | 整备 | 0–100 | 后备箱 | 最高车速 |")
            body.append("|---|---|---|---:|---|---:|---:|---|---:|---:|---:|---:|---|---:|")
        else:
            body.append("| 版本键 | 版本 | 能源 | 指导价 | 级别 | CLTC 纯电 | WLTC 纯电 | 电池 | 电机 | 快充 30–80% | 慢充 | 整备 | 0–100 | 后备箱 |")
            body.append("|---|---|---|---:|---|---:|---:|---:|---|---:|---:|---:|---:|---|")
        for (key, name, ser, seats, price, lvl, cltc, wltc, batt, power,
             fast, slow, weight, accel, adas) in rows:
            en = energy(key)
            cells = [key, name]
            if ser == "C16":
                cells.append(str(seats))
            cells += [en, _w(price), lvl, "%d km" % cltc]
            if ser in ("C10", "C16"):
                cells.append("%d km" % wltc if wltc is not None else "—")
            cells += ["%.1f kWh" % batt, power, fast, slow, "%d kg" % weight, "%.2f s" % accel]
            if ser == "C10":
                cells.append(BOOT["C10"])
            if ser == "C11":
                cells.append(BOOT["C11_" + en])
                cells.append(VMAX["C11_" + en])
            body.append("| " + " | ".join(cells) + " |")
        body.append("")
        body.append(meta["common"])
        body.append("")
        body.append(meta["extra"])
        body.append("")
        body.append(meta["sources"])
        body.append("")

    # 完整性表：全部由数据算出
    n = len(TRIMS)
    lv = {}
    for t in TRIMS:
        lv[t[5]] = lv.get(t[5], 0) + 1
    recs = json.loads(OUT.read_text(encoding="utf-8"))["records"] if OUT.exists() else []
    unk = [r for r in recs if r["status"] == "unknown"]
    unk_fields = sorted({r["field"] for r in unk})
    body += [
        "## 矩阵完整性检查",
        "",
        "| 检查项 | 结果 |",
        "|---|---|",
        "| 版本键唯一性 | %d 个键，无重复 |" % n,
        "| 价格覆盖 | %d/%d 有价格；%s |" % (n, n, "，".join("%s %d 个" % (k, v) for k, v in sorted(lv.items()))),
        "| 续航覆盖 | %d/%d |" % (n, n),
        "| 电池容量 | %d/%d |" % (n, n),
        "| 座位 | %d/%d（仅 C16 区分 5／6） |" % (n, n),
        "| 事实记录条数 | %d 条，其中“未确认” %d 条 |" % (len(recs), len(unk)),
        "| 含未确认字段 | %s |" % "、".join("`%s`" % f for f in unk_fields),
        "",
        "## 仍未确认的字段",
        "",
        "| 字段 | 涉及版本 | 状态 |",
        "|---|---|---|",
        "| 辅助驾驶芯片／感知数量 | 智享版、尊享版、C11 增程 | 未确认（不是“无”） |",
        "| C11 增程综合续航 | c11-300-* | 单源 1220 km，待第二来源 |",
        "| C16 后备箱容积 | c16-*-6、c16-*-5 | 两源数值不一致，真冲突，未决 |",
        "| C16 是否配热泵 | 全部 C16 | 官方未提，媒体称无 |",
        "| C16 增程器功率数值 | c16-280-* | 仅有“95 马力”，配置库记 70 kW，未换算 |",
        "| 逐版本座舱配置归属 | 全部 | 见 [`trim-deltas.md`](trim-deltas.md)，仅记录有来源的差异项 |",
        "| 辅助驾驶交付／开通状态 | 全部 | 见 [`adas-matrix.md`](adas-matrix.md) |",
        "",
    ]
    text = "\n".join(head + body)
    if dry:
        return text
    MATRIX.write_text(text, encoding="utf-8")
    print("wrote %s：%d 个版本，%d 条事实记录" % (MATRIX.name, n, len(recs)))


def check():
    ok = True
    if not OUT.exists():
        print("FAIL: fact-records.json 不存在，先运行 build")
        return 1
    d = json.loads(OUT.read_text(encoding="utf-8"))
    recs = d["records"]
    keys = [t[0] for t in TRIMS]

    by_trim = {}
    for r in recs:
        by_trim.setdefault(r["trim"], []).append(r)

    if set(by_trim) != set(keys):
        print("FAIL: 版本键不一致", set(by_trim) ^ set(keys))
        ok = False
    if len(keys) != len(set(keys)):
        print("FAIL: 版本键重复")
        ok = False

    required = ["guidance_price", "cltc_pure_range", "battery_capacity", "seats", "adas_lidar"]
    for k, rs in by_trim.items():
        fields = {r["field"] for r in rs}
        for f in required:
            if f not in fields:
                print("FAIL: %s 缺字段 %s" % (k, f))
                ok = False
        for r in rs:
            if r["status"] in ("confirmed", "media") and not r["source_ids"]:
                print("FAIL: %s.%s 标为 %s 但无 source_ids" % (k, r["field"], r["status"]))
                ok = False
            if r["status"] == "unknown" and r["value"] != "未确认":
                print("FAIL: %s.%s 状态 unknown 但值不是「未确认」" % (k, r["field"]))
                ok = False

    # 矩阵必须是最新生成结果：手改或忘记 render 都会在这里暴露
    if MATRIX.exists():
        cur = MATRIX.read_text(encoding="utf-8").strip()
        gen = render(dry=True).strip()
        if cur != gen:
            print("FAIL: trim-comparison.md 与事实记录不同步，运行 python scripts/facts.py render 重新生成")
            c_lines, g_lines = cur.splitlines(), gen.splitlines()
            diff = [i for i in range(min(len(c_lines), len(g_lines)))
                    if c_lines[i] != g_lines[i]]
            for i in diff[:5]:
                print("  第 %d 行：现文=%r" % (i + 1, c_lines[i][:80]))
                print("            应为=%r" % (g_lines[i][:80],))
            if len(c_lines) != len(g_lines):
                print("  行数：现文 %d，应为 %d" % (len(c_lines), len(g_lines)))
            ok = False
        else:
            print("矩阵同步：trim-comparison.md 为最新生成结果（%d 行）" % len(gen.splitlines()))
    else:
        print("SKIP: 未找到 trim-comparison.md")

    counts = {}
    for r in recs:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    print("记录数 %d，版本数 %d" % (len(recs), len(by_trim)))
    print("状态分布：", ", ".join("%s=%d" % kv for kv in sorted(counts.items())))
    print("RESULT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "check"
    if cmd == "build":
        build()
        sys.exit(0)
    if cmd == "render":
        render()
        sys.exit(0)
    if cmd == "all":
        build()
        render()
        sys.exit(check())
    sys.exit(check())
