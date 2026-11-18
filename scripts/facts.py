#!/usr/bin/env python3
"""事实数据校验与视图生成。

设计原则：**产品数值只存在于 references/fact-records.json**，**预算用例只存在于
references/budget-cases.json**。本文件不持有任何车型参数，只负责读取、校验、渲染。

    python scripts/facts.py render   # 生成 trim-comparison.md、purchase-cost.md 税表、test-cases.md 预算表
    python scripts/facts.py check    # 严格校验；任一问题返回非零
    python scripts/facts.py budget   # 打印预算用例实算明细
    python scripts/facts.py tax      # 打印税额明细
    python scripts/facts.py selftest # 注入错误，确认检查器真的会报错（打印实际场景数）
    python scripts/facts.py atest    # 确定性反例断言

check 会拒绝：悬空来源 ID、来源适用范围不覆盖该版本字段、**证据等级高于"真正覆盖该字段"的来源上限**
（挂无关来源抬等级不再可行）、状态枚举非法、主键重复、**非法日期**、**数值类型或值域非法**、
**同一版本元数据不一致**、来源 ID 重复、冲突主张缺来源、必需字段缺失、视图缺失或过期、
税表与算法不符、预算用例的候选集合或金额与独立预期不符。

边界：本文件只能守住"声明的结构、范围与等级"，不能证明网页内容本身正确。
"""

import argparse
import json
import re
import shutil
import sys
import tempfile
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REF = ROOT / "source" / "leapmotor-car-expert" / "references"
FACTS = REF / "fact-records.json"
SOURCES = REF / "sources.json"
BUDGET = REF / "budget-cases.json"
MATRIX = REF / "trim-comparison.md"
COST = REF / "purchase-cost.md"
TESTCASES = ROOT / "test-cases.md"

MATRIX_BEGIN = "<!-- MATRIX:BEGIN -->"
MATRIX_END = "<!-- MATRIX:END -->"
TAX_BEGIN = "<!-- TAX-TABLE:BEGIN -->"
TAX_END = "<!-- TAX-TABLE:END -->"
BUDGET_BEGIN = "<!-- BUDGET-CASES:BEGIN -->"
BUDGET_END = "<!-- BUDGET-CASES:END -->"
CASHFLOW_BEGIN = "<!-- CASHFLOW-CASES:BEGIN -->"
CASHFLOW_END = "<!-- CASHFLOW-CASES:END -->"

FIELD_UNITS = {
    "guidance_price": "万元",
    "cltc_pure_range": "km",
    "wltc_pure_range": "km",
    "battery_capacity": "kWh",
    "seats": "个",
    "dimensions": "mm",
    "wheelbase": "mm",
    "motor_power_torque": "-",
    "fast_charge_30_80": "-",
    "slow_charge": "h",
    "curb_weight": "kg",
    "accel_0_100": "s",
    "boot_capacity_l": "L",
    "adas_lidar": "-",
    "adas_chip": "-",
    "adas_sensor_count": "-",
    "ar_hud_60in": "-",
}

# 数值字段：(最小值, 最大值, 是否必须整数)。字符串型字段不在其中，按"非空字符串"校验。
NUMERIC_RANGE = {
    "guidance_price": (Decimal("1"), Decimal("1000"), False),      # 万元
    "cltc_pure_range": (Decimal("50"), Decimal("2000"), False),    # km
    "wltc_pure_range": (Decimal("30"), Decimal("2000"), False),
    "battery_capacity": (Decimal("5"), Decimal("300"), False),     # kWh
    "seats": (Decimal("2"), Decimal("9"), True),
    "wheelbase": (Decimal("1800"), Decimal("3500"), True),         # mm
    "curb_weight": (Decimal("800"), Decimal("4000"), False),       # kg
    "accel_0_100": (Decimal("1"), Decimal("30"), False),           # s
    "slow_charge": (Decimal("0.5"), Decimal("30"), False),         # h，超时为"未确认"并标 unknown
}

# 文本型字段：必须是字符串形态的规格描述，不接受裸数字（"41.7" 之类含糊写法）。
TEXT_FIELDS = {"dimensions", "motor_power_torque", "fast_charge_30_80", "adas_chip",
               "ar_hud_60in", "adas_sensor_count", "boot_capacity_l", "adas_lidar"}

# 文本字段里允许"无数值的定性取值"（如激光雷达"有／无"）
TEXT_ALLOW_NO_DIGIT = {"adas_lidar", "ar_hud_60in"}
# 文本字段必须带指定单位标记
TEXT_REQUIRE_UNIT = {"boot_capacity_l": "L"}

PRICE_STATUS = {"L1", "L1*", "L2", "L3"}
VALUE_STATUS = {"confirmed", "media", "unknown", "conflict"}
EVIDENCE_RANK = {"direct": 3, "partial": 2, "indirect": 1}

REQUIRED_FIELDS = ["guidance_price", "cltc_pure_range", "battery_capacity", "seats",
                   "dimensions", "wheelbase", "motor_power_torque", "fast_charge_30_80",
                   "curb_weight", "accel_0_100", "boot_capacity_l", "adas_lidar"]

# 只有部分动力形式才有的字段，不参与"字段集合一致"比较
OPTIONAL_FIELDS = {"wltc_pure_range"}

SERIES_ORDER = {"C10": 0, "C11": 1, "C16": 2}

YEAR_RANGE = (2024, 2035)

# 购置税规则参数（政策常量，不是车型数据）
TAX_RULES = {
    "vat": Decimal("0.13"),
    "rate": Decimal("0.10"),
    "half": Decimal("0.5"),
    "cap": Decimal("15000"),      # 每辆乘用车减税额上限，单位元
    "window": ("2026-01-01", "2027-12-31"),
    "basis": "财政部 税务总局 工信部公告 2023 年第 10 号",
}

# 独立预期值：来自财政部政策解读（不含税 50 万），不取自本文件算法
TAX_EXPECTED = [
    # (含增值税车价元, 原税额元, 减税额元, 实缴元)
    (Decimal("565000"), Decimal("50000"), Decimal("15000"), Decimal("35000")),   # 财政部示例：不含税 50 万
    (Decimal("339000"), Decimal("30000"), Decimal("15000"), Decimal("15000")),   # A05：含税 33.9 万触顶
    (Decimal("125800"), Decimal("11132.74"), Decimal("5566.37"), Decimal("5566.37")),
]


def q2(x):
    return Decimal(x).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def q4(x):
    return Decimal(x).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


def compute_tax(inclusive_yuan):
    """含增值税车价 → 不含税计税价、原税额、减税额、实缴税额（元）。

    cap_state 用未取整的半税额与上限比较，三态：
      none   —— 半税额 < 上限，实缴恰为原税一半；
      exact  —— 半税额 = 上限，减税额触顶但实缴仍等于原税一半（原税恰为 3 万）；
      capped —— 半税额 > 上限，减税额取上限，实缴大于原税一半。
    """
    inc = Decimal(inclusive_yuan)
    base = inc / (Decimal("1") + TAX_RULES["vat"])
    original = base * TAX_RULES["rate"]
    raw_half = original * TAX_RULES["half"]
    if raw_half < TAX_RULES["cap"]:
        cap_state = "none"
    elif raw_half == TAX_RULES["cap"]:
        cap_state = "exact"
    else:
        cap_state = "capped"
    reduction = min(raw_half, TAX_RULES["cap"])
    due = original - reduction
    return dict(inclusive=inc, base=q2(base), original=q2(original),
                reduction=q2(reduction), due=q2(due), cap_state=cap_state)


CAP_LABEL = {
    "none": "否（实缴＝原税×50%）",
    "exact": "是·恰好触顶（实缴仍等于原税×50%）",
    "capped": "是（实缴＝原税−15,000）",
}


# ---------------------------------------------------------------- 确定性约束（预算／税费／补能）

def budget_gap(budget_yuan, price_yuan):
    """落地口径下的余额：预算 − 裸车 − 购置税。单位元。未扣保险、上牌、贷款费用。"""
    tax = compute_tax(Decimal(price_yuan))
    total = Decimal(price_yuan) + tax["due"]
    return dict(price=Decimal(price_yuan), tax=tax["due"], total=total,
                balance=Decimal(budget_yuan) - total)


def charge_stops(distance_km, usable_km):
    """按可用续航估算需要的中途补能次数，至少为 0。"""
    d, u = Decimal(str(distance_km)), Decimal(str(usable_km))
    if u <= 0:
        raise ValueError("可用续航必须为正")
    if d <= u:
        return 0
    return int((d / u).to_integral_value(rounding="ROUND_CEILING")) - 1


def parse_date(s):
    """严格解析 YYYY-MM-DD；非法日期抛 ValueError。"""
    if not isinstance(s, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
        raise ValueError("日期格式必须是 YYYY-MM-DD：%r" % (s,))
    return date.fromisoformat(s)


def tax_applicable(invoice_date):
    """仅回答"开票日是否落在 2026-01-01～2027-12-31 窗口内"。

    返回 True 只代表日期在窗口内，**不代表**车辆符合减免资格（车型目录、乘用车定义、
    免税额度等需另行核对）。非法日期直接抛 ValueError，不再静默返回 True。
    """
    d = parse_date(str(invoice_date))
    lo, hi = parse_date(TAX_RULES["window"][0]), parse_date(TAX_RULES["window"][1])
    return lo <= d <= hi


# ---------------------------------------------------------------- 载入


def load(root=ROOT):
    ref = Path(root) / "source" / "leapmotor-car-expert" / "references"
    facts = json.loads((ref / "fact-records.json").read_text(encoding="utf-8"))
    sources = json.loads((ref / "sources.json").read_text(encoding="utf-8"))
    budget = json.loads((ref / "budget-cases.json").read_text(encoding="utf-8"))
    return facts, sources, budget


def src_map(sources):
    return {s["id"]: s for s in sources["sources"]}


def glob_match(pattern, value):
    if pattern == "*":
        return True
    if pattern.endswith("*"):
        return value.startswith(pattern[:-1])
    return pattern == value


def source_covers(src, trim, field):
    cov = src.get("covers") or {}
    trims = cov.get("trims") or []
    fields = cov.get("fields") or []
    if not any(glob_match(t, trim) for t in trims):
        return False
    if not any(glob_match(f, field) for f in fields):
        return False
    for u in cov.get("unsupported") or []:
        if any(glob_match(t, trim) for t in u.get("trims", [])) and \
           any(glob_match(f, field) for f in u.get("fields", [])):
            return False
    return True


# ---------------------------------------------------------------- 校验

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _num(v):
    """把数值字段转成 Decimal；不是数字则返回 None。"""
    if isinstance(v, bool) or not isinstance(v, (int, float, Decimal, str)):
        return None
    try:
        if isinstance(v, str):
            if not re.fullmatch(r"-?\d+(\.\d+)?", v.strip()):
                return None
        return Decimal(str(v))
    except Exception:
        return None


def validate(facts, sources):
    e = []
    smap = src_map(sources)
    top_checked = facts.get("checked")
    try:
        parse_date(str(top_checked))
    except Exception:
        e.append("顶层 checked 缺失或不是合法日期：%r" % (top_checked,))

    # 来源自身：ID 非空且唯一
    seen_sid = set()
    for s in sources.get("sources") or []:
        sid = s.get("id")
        if not sid or not isinstance(sid, str):
            e.append("来源 id 缺失或不是字符串：%r" % (sid,))
            continue
        if sid in seen_sid:
            e.append("来源 id 重复：%s" % sid)
        seen_sid.add(sid)
        if s.get("evidence_max") not in EVIDENCE_RANK:
            e.append("来源 %s 的 evidence_max 非法：%r" % (sid, s.get("evidence_max")))
        # 文档类来源的"适用年款是否已核实"必须显式声明，避免把旧版 PDF 当现行条款
        st = s.get("applicable_year_status")
        if st is not None and st not in ("unverified", "confirmed_current", "superseded"):
            e.append("来源 %s 的 applicable_year_status 非法：%r" % (sid, st))
        fm = s.get("file_metadata") or {}
        for k in ("pdf_creation_date", "pdf_mod_date", "http_last_modified"):
            if k in fm:
                try:
                    parse_date(str(fm[k]))
                except Exception:
                    e.append("来源 %s 的 file_metadata.%s 不是合法日期：%r" % (sid, k, fm[k]))

    recs = facts.get("records") or []
    if not recs:
        e.append("records 为空")
        return e

    seen = {}
    trims = {}
    trim_meta = {}
    for i, r in enumerate(recs):
        tag = "记录#%d(%s/%s)" % (i, r.get("trim"), r.get("field"))
        for k in ("market", "year", "series", "trim", "trim_name", "energy", "field",
                  "value", "unit", "status", "evidence", "source_ids", "checked"):
            if k not in r:
                e.append("%s 缺字段 %s" % (tag, k))
        if "field" not in r or "trim" not in r:
            continue
        key = (r.get("market"), r.get("year"), r.get("trim"), r.get("field"))
        if key in seen:
            e.append("%s 主键重复（market/year/trim/field），与记录#%d 冲突" % (tag, seen[key]))
        else:
            seen[key] = i

        f, st = r.get("field"), r.get("status")
        if f not in FIELD_UNITS:
            e.append("%s 未定义的字段名" % tag)
            continue
        if r.get("unit") != FIELD_UNITS[f]:
            e.append("%s 单位应为 %s，实际 %r" % (tag, FIELD_UNITS[f], r.get("unit")))
        if f == "guidance_price":
            if st not in PRICE_STATUS:
                e.append("%s 价格状态非法：%r" % (tag, st))
        else:
            if st not in VALUE_STATUS:
                e.append("%s 状态非法：%r" % (tag, st))
        if r.get("evidence") not in EVIDENCE_RANK:
            e.append("%s 证据等级非法：%r" % (tag, r.get("evidence")))

        try:
            parse_date(str(r.get("checked")))
        except Exception:
            e.append("%s checked 缺失或不是合法日期：%r" % (tag, r.get("checked")))
        else:
            if top_checked and r["checked"] != top_checked:
                e.append("%s checked 与顶层不一致：%s vs %s" % (tag, r.get("checked"), top_checked))

        # 年款：范围 + 同版本一致性
        yr = r.get("year")
        if not isinstance(yr, int) or not (YEAR_RANGE[0] <= yr <= YEAR_RANGE[1]):
            e.append("%s 年款非法或超出 %d–%d：%r" % (tag, YEAR_RANGE[0], YEAR_RANGE[1], yr))
        meta = (r.get("market"), yr, r.get("series"), r.get("trim_name"), r.get("energy"))
        if r["trim"] in trim_meta and trim_meta[r["trim"]] != meta:
            e.append("%s 与同版本其他记录的元数据不一致：%r vs %r"
                     % (tag, meta, trim_meta[r["trim"]]))
        trim_meta.setdefault(r["trim"], meta)

        if st == "unknown" and r.get("value") != "未确认":
            e.append("%s 状态 unknown 但值不是“未确认”" % tag)
        if st == "conflict" and r.get("value") != "未决":
            e.append("%s 状态 conflict 但值不是“未决”" % tag)

        # 数值类型与值域
        v = r.get("value")
        if st not in ("unknown", "conflict"):
            if f in NUMERIC_RANGE:
                d = _num(v)
                lo, hi, is_int = NUMERIC_RANGE[f]
                if d is None:
                    e.append("%s 字段 %s 必须是数值，实际 %r" % (tag, f, v))
                else:
                    if d < lo or d > hi:
                        e.append("%s 字段 %s 超出合理范围 %s–%s：%s" % (tag, f, lo, hi, d))
                    if is_int and d != d.to_integral_value():
                        e.append("%s 字段 %s 必须是整数，实际 %s" % (tag, f, d))
            elif f in TEXT_FIELDS:
                if not isinstance(v, str) or not v.strip():
                    e.append("%s 字段 %s 必须是非空字符串描述，实际 %r" % (tag, f, v))
                elif _num(v) is not None:
                    e.append("%s 字段 %s 是规格描述字段，不接受裸数字 %r（应带单位或说明）"
                             % (tag, f, v))
                elif f not in TEXT_ALLOW_NO_DIGIT and not any(ch.isdigit() for ch in v):
                    e.append("%s 字段 %s 的描述里没有任何数值，疑似残缺：%r" % (tag, f, v))
                elif f in TEXT_REQUIRE_UNIT and TEXT_REQUIRE_UNIT[f] not in v:
                    e.append("%s 字段 %s 缺少单位 %s：%r" % (tag, f, TEXT_REQUIRE_UNIT[f], v))

        sids = r.get("source_ids") or []
        for sid in sids:
            if sid not in smap:
                e.append("%s 引用不存在的来源 ID：%s" % (tag, sid))

        need_evidence = st in PRICE_STATUS or st in ("confirmed", "media")
        if need_evidence and not sids:
            e.append("%s 状态 %s 必须有来源，实际为空" % (tag, st))
        if not need_evidence and sids:
            e.append("%s 状态 %s 不应挂来源（应留空或改状态）" % (tag, st))

        if sids:
            # 只有"真正覆盖该版本该字段"的来源才能支撑证据等级；
            # 挂一个无关来源把等级抬上去，在这里会被拦下。
            covering = [s for s in sids if s in smap and source_covers(smap[s], r["trim"], f)]
            if need_evidence and not covering:
                e.append("%s 的来源 %s 均未声明覆盖该版本该字段（适用范围越界）"
                         % (tag, ",".join(sids)))
            ranks = [EVIDENCE_RANK[smap[s]["evidence_max"]] for s in covering]
            if ranks and EVIDENCE_RANK[r["evidence"]] > max(ranks):
                best = max(ranks)
                label = [k for k, v in EVIDENCE_RANK.items() if v == best][0]
                e.append("%s 证据等级 %s 高于覆盖该字段的来源上限 %s（无关来源不能抬等级）"
                         % (tag, r["evidence"], label))
        else:
            if r.get("evidence") != "indirect":
                e.append("%s 无来源，证据等级应为 indirect" % tag)

        trims.setdefault(r["trim"], {"fields": set(), "series": r.get("series")})
        trims[r["trim"]]["fields"].add(f)

    # 版本完整性与一致性
    all_fields = set()
    for t, info in trims.items():
        missing = [f for f in REQUIRED_FIELDS if f not in info["fields"]]
        if missing:
            e.append("版本 %s 缺必需字段：%s" % (t, ",".join(missing)))
        all_fields.add(frozenset(info["fields"] - OPTIONAL_FIELDS))
    if len(all_fields) > 1:
        e.append("各版本字段集合不一致，共 %d 种" % len(all_fields))

    # 冲突记录
    cids = set()
    for c in facts.get("conflicts") or []:
        cid = c.get("id")
        if not cid or cid in cids:
            e.append("冲突 id 缺失或重复：%r" % cid)
        cids.add(cid)
        if c.get("field") not in FIELD_UNITS:
            e.append("冲突 %s 字段未定义：%r" % (cid, c.get("field")))
        claims = c.get("claims") or []
        if len(claims) < 2:
            e.append("冲突 %s 的主张少于两条" % cid)
        for cl in claims:
            if not str(cl.get("value") or "").strip():
                e.append("冲突 %s 存在空主张值" % cid)
            csl = cl.get("source_ids") or []
            if not csl:
                e.append("冲突 %s 的主张「%s」没有来源" % (cid, cl.get("value")))
            for sid in csl:
                if sid not in smap:
                    e.append("冲突 %s 引用不存在的来源 %s" % (cid, sid))
        for t in c.get("trim_scope") or []:
            if t not in trims:
                e.append("冲突 %s 的 trim_scope 含未知版本 %s" % (cid, t))

    # 状态为 conflict 的记录必须能在 conflicts 里找到同类
    for r in recs:
        if r.get("status") == "conflict":
            ok = any(r["field"] == c.get("field") and r["trim"] in (c.get("trim_scope") or [])
                     for c in facts.get("conflicts") or [])
            if not ok:
                e.append("记录 %s/%s 标为 conflict，但 conflicts 中没有对应条目"
                         % (r["trim"], r["field"]))

    # 税表算法与独立预期值对齐
    for inc, orig, red, due in TAX_EXPECTED:
        got = compute_tax(inc)
        if got["original"] != orig or got["reduction"] != red or got["due"] != due:
            e.append("税额算法与独立预期值不符：含税 %s 应为 原税%s/减%s/实缴%s，实得 %s/%s/%s"
                     % (inc, orig, red, due, got["original"], got["reduction"], got["due"]))
    return e


# ---------------------------------------------------------------- 预算用例

def trim_facts(facts):
    """trim → {price_yuan, seats, has_lidar, name}。"""
    out = {}
    for r in facts["records"]:
        t = r["trim"]
        d = out.setdefault(t, {"name": "%s %s" % (r["series"], r["trim_name"]),
                               "series": r["series"], "energy": r["energy"]})
        if r["field"] == "guidance_price" and isinstance(r["value"], (int, float)):
            d["price_yuan"] = int(round(Decimal(str(r["value"])) * 10000))
        elif r["field"] == "seats" and isinstance(r["value"], (int, float)):
            d["seats"] = int(r["value"])
        elif r["field"] == "adas_lidar":
            v = str(r["value"])
            d["has_lidar"] = v not in ("无", "未确认", "未决") and not v.startswith("无")
    for t, d in out.items():
        if d.get("seats") == 6:
            d["name"] += " 六座"
        elif d.get("seats") == 5 and d["series"] == "C16":
            d["name"] += " 五座"
    return out


def _in_scope(t, info, flt):
    if flt.get("series"):
        want = {str(s).upper() for s in flt["series"]}
        if str(info["series"]).upper() not in want:
            return False
    if flt.get("min_seats") and (info.get("seats") or 0) < flt["min_seats"]:
        return False
    if flt.get("require_lidar") and not info.get("has_lidar"):
        return False
    return True


def solve_case(case, tinfo):
    """按算法求合格集；返回 (合格 trim 列表, {trim: (price, tax, balance)})。"""
    budget, basis = int(case["budget_yuan"]), case["basis"]
    flt = case.get("filter") or {}
    qual, nums = [], {}
    for t, info in tinfo.items():
        if not _in_scope(t, info, flt):
            continue
        p = info.get("price_yuan")
        if p is None:
            continue
        g = budget_gap(budget, p)
        nums[t] = (p, g["tax"], g["balance"])
        if basis == "裸车":
            if p <= budget:
                qual.append(t)
        elif g["balance"] >= 0:
            qual.append(t)
    return sorted(qual), nums


def validate_budget(cases, facts):
    e = []
    tinfo = trim_facts(facts)
    seen = set()
    all_cases = cases.get("cases") or []
    by_id = {c["id"]: c for c in all_cases if c.get("id")}
    for c in all_cases:
        cid = c.get("id")
        if not cid or cid in seen:
            e.append("预算用例 id 缺失或重复：%r" % (cid,))
            continue
        seen.add(cid)
        if c.get("basis") not in ("裸车", "落地"):
            e.append("预算用例 %s 的 basis 非法：%r" % (cid, c.get("basis")))
            continue
        if not isinstance(c.get("budget_yuan"), int) or c["budget_yuan"] <= 0:
            e.append("预算用例 %s 的 budget_yuan 必须是正整数" % cid)
            continue

        try:
            parse_date(str(cases.get("checked")))
        except Exception:
            e.append("预算用例顶层 checked 不是合法日期：%r" % (cases.get("checked"),))

        # scope 三态：open=原题无硬条件；stated=原题明写的条件；branch=用户后续确认的分支
        scope = c.get("scope", "open")
        if scope not in ("open", "stated", "branch"):
            e.append("预算用例 %s 的 scope 非法：%r（只允许 open / stated / branch）" % (cid, scope))
            continue
        if scope == "open" and c.get("filter"):
            e.append("预算用例 %s 标为 open，却带了过滤条件 %r："
                     "原题没写的硬条件不得由模型补上，应改标 branch 并写 precondition" % (cid, c["filter"]))
        if scope == "stated" and not str(c.get("precondition") or "").strip():
            e.append("预算用例 %s 标为 stated，但缺少 precondition（原题里的那句条件）" % cid)
        if scope == "branch":
            if not str(c.get("precondition") or "").strip():
                e.append("预算用例 %s 标为 branch，但缺少 precondition（用户已确认的那句话）" % cid)
            fb = c.get("fallback_case")
            if not fb:
                e.append("预算用例 %s 标为 branch，但缺少 fallback_case（撤销过滤后的基线用例）" % cid)
            elif fb not in by_id:
                e.append("预算用例 %s 的 fallback_case %r 不存在" % (cid, fb))
            elif c.get("kind") != "price_ceiling":
                base = by_id[fb]
                if base.get("basis") != c.get("basis") or base.get("budget_yuan") != c.get("budget_yuan"):
                    e.append("预算用例 %s 与 fallback %s 的 basis／budget_yuan 不一致" % (cid, fb))
                else:
                    try:
                        bq, _ = solve_case(base, tinfo)
                        q, _ = solve_case(c, tinfo)
                    except Exception as ex:
                        e.append("预算用例 %s 与 fallback 无法比较：%s" % (cid, ex))
                    else:
                        extra = sorted(set(q) - set(bq))
                        if extra:
                            e.append("预算用例 %s 的候选 %s 不在 fallback 集合内（"
                                     "过滤只能收缩候选，不能扩增）" % (cid, ", ".join(extra)))

        if c.get("kind") == "price_ceiling":
            exp = Decimal(str(c.get("expected_max_price_yuan")))
            got = q2(Decimal(c["budget_yuan"]) * (1 + TAX_RULES["vat"]) /
                     (1 + TAX_RULES["vat"] + TAX_RULES["rate"] / 2))
            if got != exp:
                e.append("用例 %s 裸车上限应为 %s，算得 %s" % (cid, exp, got))
            continue

        qual, nums = solve_case(c, tinfo)
        exp_qual = sorted(c.get("expected_qualified") or [])
        if qual != exp_qual:
            e.append("用例 %s 合格集合不符：算得 %s，预期 %s" % (cid, qual, exp_qual))
        for row in c.get("expected_excluded") or []:
            t = row.get("trim")
            if t not in nums:
                e.append("用例 %s 的边界反例 %s 不在该用例范围内" % (cid, t))
                continue
            p, tax, bal = nums[t]
            if t in qual:
                e.append("用例 %s 的边界反例 %s 实际在合格集内（预期应被排除）" % (cid, t))
            if "price" in row and Decimal(str(row["price"])) != p:
                e.append("用例 %s / %s 裸车价不符：%s vs %s" % (cid, t, row["price"], p))
            if "tax" in row and q2(Decimal(str(row["tax"]))) != tax:
                e.append("用例 %s / %s 购置税不符：%s vs %s" % (cid, t, row["tax"], tax))
            if "balance" in row and q2(Decimal(str(row["balance"]))) != bal:
                e.append("用例 %s / %s 余额不符：%s vs %s" % (cid, t, row["balance"], bal))
    return e


def _gap(v):
    """预算结余显示：正数写"余"，负数写"超"，避免把两种口径混成一个数。"""
    d = Decimal(str(v))
    return ("余 %s" if d >= 0 else "超 %s") % "{:,.2f}".format(abs(d))


SCOPE_LABEL = {"open": "基线", "stated": "原题条件", "branch": "分支（须先确认）"}


def render_budget(facts, cases):
    tinfo = trim_facts(facts)
    out = [BUDGET_BEGIN,
           "**本区块由 `scripts/facts.py render` 从 [`budget-cases.json`](source/leapmotor-car-expert/references/budget-cases.json) 生成，请勿手改。**",
           "",
           "金额单位元。**两个口径分别算**：裸车口径只比 `预算 − 裸车价`，不计购置税；"
           "落地口径算 `预算 − 裸车 − 购置税`（2026–2027 年减半后），**未扣保险、上牌、贷款费用**。"
           "结余为正不等于可成交，仍需保险上牌报价。",
           "",
           "「性质」列区分三类用例：**基线**＝原题没有硬条件，全系比较；"
           "**原题条件**＝条件由用户在原题里明写（如「必须六座」）；"
           "**分支**＝条件由用户后续确认，未经确认**不得**把该行集合当原题答案。",
           "",
           "| 用例 | 性质 | 口径 | 预算 | 合格候选（预算结余） | 边界反例（预算结余） |",
           "|---|---|---|---:|---|---|"]
    for c in cases["cases"]:
        budget = "{:,}".format(c["budget_yuan"])
        nature = SCOPE_LABEL[c.get("scope", "open")]
        if c.get("kind") == "price_ceiling":
            out.append("| %s %s | %s | %s | %s | 裸车上限 **%s 元**（约 %.2f 万） | — |" % (
                c["question"], c["label"], nature, c["basis"], budget,
                "{:,.2f}".format(Decimal(c["expected_max_price_yuan"])),
                Decimal(c["expected_max_price_yuan"]) / 10000))
            continue
        qual, nums = solve_case(c, tinfo)
        basis = c["basis"]
        if qual:
            cells = []
            for t in sorted(qual, key=lambda x: (nums[x][0], x)):
                p, tax, bal = nums[t]
                gap = Decimal(c["budget_yuan"]) - p if basis == "裸车" else bal
                cells.append("%s %.2f 万＝%s" % (tinfo[t]["name"], p / 10000, _gap(gap)))
            qtxt = "<br>".join(cells)
        else:
            qtxt = "**无合格候选**"
        ex = []
        for row in c.get("expected_excluded") or []:
            t = row["trim"]
            p, tax, bal = nums.get(t, (row.get("price"), None, None))
            if bal is None:
                ex.append("%s %.2f 万（裸车已超 %s 元）" % (
                    tinfo[t]["name"], Decimal(str(p)) / 10000,
                    "{:,}".format(Decimal(str(p)) - c["budget_yuan"])))
            else:
                gap = Decimal(c["budget_yuan"]) - Decimal(str(p)) if basis == "裸车" else bal
                ex.append("%s %.2f 万＝%s" % (tinfo[t]["name"], Decimal(str(p)) / 10000, _gap(gap)))
        out.append("| %s %s | %s | %s | %s | %s | %s |" % (
            c["question"], c["label"], nature, basis, budget, qtxt,
            "<br>".join(ex) if ex else "—"))

    br = [c for c in cases["cases"] if c.get("scope") == "branch"]
    if br:
        out.append("")
        out.append("**分支用例的前提**（用户没确认之前不得使用这些集合，只能先问诊）：")
        out.append("")
        for c in br:
            out.append("- `%s`：%s 撤销该条件后回到基线 `%s`，候选只会增多不会减少。" % (
                c["id"], c.get("precondition", "").strip(), c.get("fallback_case")))
    out.append(BUDGET_END)
    return "\n".join(out)


# ---------------------------------------------------------------- 分期现金流（按时点分栏）

CASHFLOW_CASES = [
    {
        "id": "A-full-payment",
        "label": "全款，税费保险待报价",
        "inputs": {"price": 200000, "down_total": 200000},
        "expected": {"paid_before": "0", "today": "200000", "cumulative": "200000",
                     "future": "0", "lender_total": "0", "total": "200000"},
        "note": "① 与 ③ 均为 0；当天尚需即车价",
    },
    {
        "id": "B-deposit-and-store-fee",
        "label": "首付共 6 万（已付定金 5,000）、门店当日另收 3,000、36 期月供 4,300",
        "inputs": {"price": 200000, "down_total": 60000, "deposit_paid": 5000,
                   "store_fee_today": 3000, "monthly": 4300, "months": 36,
                   "loan_principal": 140000},
        "expected": {"paid_before": "5000", "today": "58000", "cumulative": "63000",
                     "future": "154800", "lender_total": "154800", "total": "217800"},
        "note": "定金只能在 ①；② = (60000−5000)+3000；门店手续费不进⑤",
    },
    {
        "id": "C-balloon-and-lender-fee",
        "label": "首付 6 万此前未付、贷款方当日收 2,000、36 期每期 3,200、末期尾款 5 万",
        "inputs": {"price": 200000, "down_total": 60000, "lender_fee_today": 2000,
                   "monthly": 3200, "months": 36, "balloon": 50000,
                   "loan_principal": 140000},
        "expected": {"paid_before": "0", "today": "62000", "cumulative": "62000",
                     "future": "165200", "lender_total": "167200", "total": "227200"},
        "note": "⑤=2000+165200 是另一视角；把它加进②③会重复",
    },
]


def cashflow(price, down_total, deposit_paid=0, store_fee_today=0, lender_fee_today=0,
             monthly=0, months=0, balloon=0, loan_principal=None):
    """按付款时点分栏的现金流（不含税费保险与补贴）。单位元。

    ① paid_before  此前已付（定金等）
    ② today        提车当天尚需（首付余款 + 门店当日费 + 贷款方当日费）
       cumulative  截至提车累计自付 = ①+②
    ③ future       未来各期（月供×期数 + 尾款）
       lender_total ⑤ 对贷款方累计付款 = 贷款方当日费 + ③（另一视角，不得与②③相加）
       total        全期总支出 = ①+②+③
    """
    D = Decimal
    price, down_total = D(str(price)), D(str(down_total))
    before = D(str(deposit_paid))
    if before < 0:
        raise ValueError("已付定金不能为负")
    if before > down_total:
        raise ValueError("已付定金不能大于首付合计")
    today = (down_total - before) + D(str(store_fee_today)) + D(str(lender_fee_today))
    future = D(str(monthly)) * int(months) + D(str(balloon))
    if loan_principal is not None and down_total + D(str(loan_principal)) != price:
        raise ValueError("首付合计 + 贷款本金 应等于车价")
    return dict(paid_before=q2(before), today=q2(today),
                cumulative=q2(before + today), future=q2(future),
                lender_total=q2(D(str(lender_fee_today)) + future),
                total=q2(before + today + future))


def validate_cashflow():
    """三个算例的期望值由手算给出，此处用另一条路径复算并逐项比对。

    每个算例都必须把六个字段写全。v0.5.3 早期版本里 A 例只写了 inputs、没有
    expected，`if not exp: continue` 就把它整个跳过了——表里看得见、断言里没有，
    等于"未验证却计入算例数"。现在缺字段直接判失败。
    """
    e = []
    need = {k for k, _ in CF_COLS}
    for c in CASHFLOW_CASES:
        try:
            got = cashflow(**c["inputs"])
        except Exception as ex:
            e.append("分期算例 %s 无法计算：%s" % (c["id"], ex))
            continue
        exp = c.get("expected") or {}
        miss = sorted(need - set(exp))
        if miss:
            e.append("分期算例 %s 的期望值缺字段 %s：六个字段必须写全，不能留空跳过断言"
                     % (c["id"], "、".join(miss)))
            continue
        for k, v in exp.items():
            if got[k] != q2(Decimal(str(v))):
                e.append("分期算例 %s 的 %s 应为 %s，算得 %s" % (c["id"], k, v, got[k]))
        if got["cumulative"] != got["paid_before"] + got["today"]:
            e.append("分期算例 %s 的 A 累计不等于 ①+②" % c["id"])
        if got["total"] != got["cumulative"] + got["future"]:
            e.append("分期算例 %s 的全期总支出不等于 A+③" % c["id"])
    return e


CF_COLS = [("paid_before", "① 此前已付"), ("today", "② 当天尚需"),
           ("cumulative", "A 累计自付"), ("future", "③ 未来各期"),
           ("lender_total", "⑤ 贷款方视角"), ("total", "B 全期总支出")]


def render_cashflow():
    out = [CASHFLOW_BEGIN,
           "金额单位元，**忽略税费、保险、上牌、选装与补贴**，只验分栏与重计。"
           "本表由 `scripts/facts.py render` 生成，`atest` 逐项断言。",
           "",
           "| 情形 | " + " | ".join(t for _, t in CF_COLS) + " |",
           "|---|" + "---:|" * len(CF_COLS)]
    for c in CASHFLOW_CASES:
        got = cashflow(**c["inputs"])
        cells = ["%s" % "{:,.0f}".format(got[k]) for k, _ in CF_COLS]
        out.append("| %s | %s |" % (c["label"], " | ".join(cells)))
    out.append("")
    for c in CASHFLOW_CASES:
        out.append("- **%s**：%s" % (c["id"], c["note"]))
    out.append(CASHFLOW_END)
    return "\n".join(out)


# ---------------------------------------------------------------- 渲染


def price_list(facts):
    seen = []
    for r in facts["records"]:
        if r["field"] == "guidance_price" and r["value"] not in seen:
            seen.append(r["value"])
    return sorted(seen)


def render_tax(facts):
    out = [TAX_BEGIN,
           "| 指导价（万元） | 不含税计税价 | 原应纳税额 | 减税额 | 实缴购置税 | 是否触及减税上限 |",
           "|---:|---:|---:|---:|---:|---|"]
    for p in price_list(facts):
        t = compute_tax(Decimal(str(p)) * 10000)
        out.append("| %.2f | %s | %s | %s | %s | %s |" % (
            p, q4(t["base"] / 10000), q4(t["original"] / 10000),
            q4(t["reduction"] / 10000), q4(t["due"] / 10000), CAP_LABEL[t["cap_state"]]))
    out.append(TAX_END)
    return "\n".join(out)


def by_trim(facts):
    order, d = [], {}
    for r in facts["records"]:
        if r["trim"] not in d:
            order.append(r["trim"])
            d[r["trim"]] = {"meta": {k: r[k] for k in ("trim_name", "series", "energy")},
                            "f": {}}
        d[r["trim"]]["f"][r["field"]] = r
    order.sort(key=lambda t: SERIES_ORDER.get(d[t]["meta"]["series"], 9))
    return order, d


def fmt(v, unit=""):
    if isinstance(v, str):
        return v
    if isinstance(v, float):
        return ("%g" % v)
    return str(v)


def marker(rec):
    """矩阵单元格的证据标记：只看证据等级，状态已由“未确认/未决”文字表达。"""
    if not rec:
        return ""
    ev = rec.get("evidence")
    if ev == "indirect":
        return "†"
    if rec.get("status") == "media":
        return "*"
    return ""


def render_matrix(facts):
    order, d = by_trim(facts)
    out = [MATRIX_BEGIN,
           "**本区块由 `scripts/facts.py render` 从 [`fact-records.json`](fact-records.json) 生成，请勿手改。**",
           "",
           "核对日期：%s。市场：中国。年款：2027 款。" % facts["checked"],
           "",
           "**读表先看标记**：`†` = 间接证据（未直读原始页面）；`*` = 媒体口径；"
           "“未确认” = 资料没写，**不等于没有**；“未决” = 来源冲突未裁决。"
           "带标记的值请在引用时一并说明，逐字段来源见 [`fact-records.json`](fact-records.json)。",
           ""]
    for series in ("C10", "C11", "C16"):
        rows = [t for t in order if d[t]["meta"]["series"] == series]
        if not rows:
            continue
        out.append("### %s（%d 版）" % (series, len(rows)))
        out.append("")
        if series == "C16":
            out.append("| 版本键 | 版本 | 座位 | 能源 | 指导价 | 级别 | CLTC | WLTC | 电池 | 电机 | 快充 | 慢充 | 整备 | 0–100 | 后备箱 |")
            out.append("|---|---|---:|---|---:|---|---:|---:|---:|---|---:|---:|---:|---:|---|")
        elif series == "C11":
            out.append("| 版本键 | 版本 | 能源 | 指导价 | 级别 | CLTC | 电池 | 电机 | 快充 | 慢充 | 整备 | 0–100 | 后备箱 | 轴距 |")
            out.append("|---|---|---|---:|---|---:|---:|---|---:|---:|---:|---:|---|---:|")
        else:
            out.append("| 版本键 | 版本 | 能源 | 指导价 | 级别 | CLTC | WLTC | 电池 | 电机 | 快充 | 慢充 | 整备 | 0–100 | 后备箱 |")
            out.append("|---|---|---|---:|---|---:|---:|---:|---|---:|---:|---:|---:|---|")
        for t in rows:
            m, f = d[t]["meta"], d[t]["f"]

            def g(k, suffix="", default="—"):
                r = f.get(k)
                if not r or r["value"] == "未确认":
                    return ("未确认" if r else default)
                return fmt(r["value"]) + suffix + marker(r)

            cells = [t, m["trim_name"]]
            if series == "C16":
                cells.append(str(f["seats"]["value"]) + marker(f["seats"]))
            pr = f["guidance_price"]
            cells += [m["energy"],
                      "%.2f 万%s" % (pr["value"], marker(pr)), pr["status"],
                      g("cltc_pure_range", " km")]
            if series in ("C10", "C16"):
                cells.append(g("wltc_pure_range", " km"))
            cells += [g("battery_capacity", " kWh"), g("motor_power_torque"), g("fast_charge_30_80"),
                      g("slow_charge", " h"), g("curb_weight", " kg"), g("accel_0_100", " s"),
                      g("boot_capacity_l")]
            if series == "C11":
                cells.append(g("wheelbase", " mm"))
            out.append("| " + " | ".join(cells) + " |")
        out.append("")

    # 逐字段证据提示：把 JSON 里的限制搬到读者眼前
    flagged = [r for r in facts["records"]
               if r["evidence"] != "direct" or r["status"] in ("unknown", "conflict", "media")]
    if flagged:
        out += ["### 字段证据提示（非直读或非确定）", "",
                "下表列出主矩阵中**不能当作直读确定值**的字段。同一版本内按“证据/状态 + 来源”合并；"
                "完整逐字段来源见 [`fact-records.json`](fact-records.json)。", "",
                "| 版本键 | 字段 | 状态/证据 | 来源 |", "|---|---|---|---|"]
        groups = {}
        order_idx = {t: i for i, t in enumerate(order)}
        for r in flagged:
            key = (r["trim"], r["evidence"], r["status"], tuple(r.get("source_ids") or []))
            groups.setdefault(key, []).append(r["field"])
        for key in sorted(groups, key=lambda k: (order_idx.get(k[0], 99), k[1], k[2])):
            trim, ev, st, sids = key
            fields = groups[key]
            shown = "、".join(fields[:8])
            if len(fields) > 8:
                shown += " 等 %d 项" % len(fields)
            out.append("| %s | %s | %s / %s | %s |" % (
                trim, shown, st, ev,
                "、".join("`%s`" % s for s in sids) if sids else "—（无来源，不得作确定值）"))
        out.append("")

    # 汇总（全部由数据计算）
    n = len(order)
    lv = {}
    for r in facts["records"]:
        if r["field"] == "guidance_price":
            lv[r["status"]] = lv.get(r["status"], 0) + 1
    unknown = [r for r in facts["records"] if r["status"] == "unknown"]
    conflicted = [r for r in facts["records"] if r["status"] == "conflict"]
    conflicts = facts.get("conflicts") or []
    if conflicts:
        out += ["### 冲突（未决，不取中值）", "",
                "| 冲突 | 字段 | 涉及版本 | 各方主张 | 状态 |", "|---|---|---|---|---|"]
        for c in conflicts:
            claims = "；".join("%s（%s）" % (cl["value"], "、".join("`%s`" % s for s in cl["source_ids"]))
                              for cl in c["claims"])
            out.append("| %s | %s | %s | %s | %s |" % (
                c["id"], c["field"], "、".join(c["trim_scope"]), claims, c["status"]))
        out.append("")

    out += ["### 数据完整性（程序计算）", "",
            "| 项目 | 结果 |", "|---|---|",
            "| 版本数 | %d |" % n,
            "| 事实记录 | %d 条 |" % len(facts["records"]),
            "| 价格级别 | %s |" % "，".join("%s %d 个" % (k, lv[k]) for k in sorted(lv)),
            "| 未确认 | %d 条 |" % len(unknown),
            "| 争议未决 | %d 条（%d 组冲突） |" % (len(conflicted), len(conflicts)),
            "| 非直读证据 | %d 条 |" % sum(1 for r in facts["records"] if r["evidence"] != "direct"),
            ""]
    return "\n".join(out)


def patch_region(text, begin, end, block):
    i, j = text.find(begin), text.find(end)
    if i < 0 or j < 0:
        raise SystemExit("找不到区块标记 %s / %s" % (begin, end))
    return text[:i] + block + text[j + len(end):]


def write_views(facts, budget, root=ROOT):
    ref = Path(root) / "source" / "leapmotor-car-expert" / "references"
    mat = render_matrix(facts)
    (ref / "trim-comparison.md").write_text(
        "# 17 版本配置矩阵\n\n"
        "**用法**：只放能追到来源的字段。写“未确认”是“资料未写”，不是“没有”。\n\n"
        "**标记**：`†` 间接证据，`*` 媒体口径。带标记的值引用时必须一并说明，"
        "逐字段来源、状态与证据等级见 [`fact-records.json`](fact-records.json)。\n\n"
        "**冲突**：数值冲突不在本表裁决，见 fact-records.json 的 `conflicts`。\n\n"
        "**级别只作用于价格**，电池、芯片等字段各有独立状态，不继承价格级别。\n\n"
        + mat + "\n", encoding="utf-8", newline="\n")

    cost = (ref / "purchase-cost.md").read_text(encoding="utf-8")
    cost = patch_region(cost, TAX_BEGIN, TAX_END, render_tax(facts))
    if CASHFLOW_BEGIN in cost:
        cost = patch_region(cost, CASHFLOW_BEGIN, CASHFLOW_END, render_cashflow())
    (ref / "purchase-cost.md").write_text(cost, encoding="utf-8", newline="\n")

    tc = Path(root) / "test-cases.md"
    if tc.exists():
        text = tc.read_text(encoding="utf-8")
        (tc).write_text(patch_region(text, BUDGET_BEGIN, BUDGET_END, render_budget(facts, budget)),
                        encoding="utf-8", newline="\n")
    return mat


# ---------------------------------------------------------------- 命令


def cmd_check(root=ROOT):
    facts, sources, budget = load(root)
    ref = Path(root) / "source" / "leapmotor-car-expert" / "references"
    errs = validate(facts, sources) + validate_budget(budget, facts) + validate_cashflow()

    for name in ("trim-comparison.md", "purchase-cost.md", "budget-cases.json"):
        if not (ref / name).exists():
            errs.append("必需文件缺失：%s" % name)
    if not TESTCASES.exists():
        errs.append("必需视图缺失：test-cases.md")

    if (ref / "trim-comparison.md").exists():
        cur = (ref / "trim-comparison.md").read_text(encoding="utf-8")
        if MATRIX_BEGIN not in cur:
            errs.append("trim-comparison.md 缺少生成区块标记")
        elif render_matrix(facts) not in cur:
            errs.append("trim-comparison.md 与事实数据不同步，运行 render 重新生成")
    if (ref / "purchase-cost.md").exists():
        cur = (ref / "purchase-cost.md").read_text(encoding="utf-8")
        if TAX_BEGIN not in cur:
            errs.append("purchase-cost.md 缺少税表区块标记")
        elif render_tax(facts) not in cur:
            errs.append("purchase-cost.md 税表与算法输出不同步，运行 render 重新生成")
        if CASHFLOW_BEGIN not in cur:
            errs.append("purchase-cost.md 缺分区块标记")
        elif render_cashflow() not in cur:
            errs.append("purchase-cost.md 分期算例与 cashflow() 输出不同步，运行 render 重新生成")
    if TESTCASES.exists():
        cur = TESTCASES.read_text(encoding="utf-8")
        if BUDGET_BEGIN not in cur:
            errs.append("test-cases.md 缺少预算用例区块标记")
        elif render_budget(facts, budget) not in cur:
            errs.append("test-cases.md 预算表与预算用例不同步，运行 render 重新生成")

    if errs:
        for x in errs:
            print("FAIL:", x)
        print("共 %d 项问题" % len(errs))
        print("RESULT: FAIL")
        return 1
    print("记录 %d 条，版本 %d 个，冲突 %d 组，预算用例 %d 个，分期算例 %d 个"
          % (len(facts["records"]), len({r["trim"] for r in facts["records"]}),
             len(facts.get("conflicts") or []), len(budget.get("cases") or []),
             len(CASHFLOW_CASES)))
    print("视图：trim-comparison.md / purchase-cost.md 税表＋分期算例 / test-cases.md 预算表 均为最新")
    print("RESULT: PASS")
    return 0


def cmd_tax(root=ROOT):
    facts, _, _ = load(root)
    for p in price_list(facts):
        t = compute_tax(Decimal(str(p)) * 10000)
        print("指导价 %6.2f 万 → 不含税 %8.4f 万，原税 %7.4f 万，减 %7.4f 万，实缴 %7.4f 万"
              % (p, t["base"] / 10000, t["original"] / 10000,
                 t["reduction"] / 10000, t["due"] / 10000))
    return 0


def cmd_budget(root=ROOT):
    facts, _, budget = load(root)
    tinfo = trim_facts(facts)
    for c in budget["cases"]:
        if c.get("kind") == "price_ceiling":
            print("%-24s %s 裸车上限 %s 元" % (c["id"], c["basis"], c["expected_max_price_yuan"]))
            continue
        qual, nums = solve_case(c, tinfo)
        print("%-24s 预算 %d %s → 合格 %d 个：%s" % (
            c["id"], c["budget_yuan"], c["basis"], len(qual),
            "、".join(qual) if qual else "无"))
        for t in qual:
            print("    %-18s %8d 税 %9s 余额 %12s" % (t, nums[t][0], nums[t][1], nums[t][2]))
    return 0


def cmd_selftest():
    """在临时副本中注入错误，确认 check 全部拒绝。场景数由 cases 列表统计。"""
    cases = []

    def prep():
        tmp = Path(tempfile.mkdtemp())
        dst = tmp / "source" / "leapmotor-car-expert" / "references"
        dst.mkdir(parents=True)
        for n in ("fact-records.json", "sources.json", "budget-cases.json",
                  "trim-comparison.md", "purchase-cost.md"):
            shutil.copy(REF / n, dst / n)
        shutil.copy(TESTCASES, tmp / "test-cases.md")
        return tmp, dst

    def run(root):
        import contextlib
        import io
        with contextlib.redirect_stdout(io.StringIO()):
            return cmd_check(root)

    tmp, _ = prep()
    cases.append(("baseline", run(tmp), 0))
    shutil.rmtree(tmp, ignore_errors=True)

    def mutate(name, fn, expect=1):
        tmp, ref = prep()
        fn(ref)
        rc = run(tmp)
        cases.append((name, rc, expect))
        shutil.rmtree(tmp, ignore_errors=True)

    def edit_facts(ref, fn):
        p = ref / "fact-records.json"
        d = json.loads(p.read_text(encoding="utf-8"))
        fn(d)
        p.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")

    def edit_sources(ref, fn):
        p = ref / "sources.json"
        d = json.loads(p.read_text(encoding="utf-8"))
        fn(d)
        p.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")

    def edit_budget(ref, fn):
        p = ref / "budget-cases.json"
        d = json.loads(p.read_text(encoding="utf-8"))
        fn(d)
        p.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")

    def rec(d, trim, field):
        for r in d["records"]:
            if r["trim"] == trim and r["field"] == field:
                return r
        raise KeyError((trim, field))

    mutate("price_changed_to_1",
           lambda ref: edit_facts(ref, lambda d: d["records"][0].__setitem__("value", 1)))
    mutate("invalid_source_id",
           lambda ref: edit_facts(ref, lambda d: d["records"][0].__setitem__("source_ids", ["no-such-source"])))
    mutate("L1_without_source",
           lambda ref: edit_facts(ref, lambda d: d["records"][0].__setitem__("source_ids", [])))
    mutate("missing_checked_date",
           lambda ref: edit_facts(ref, lambda d: d["records"][3].pop("checked", None)))
    mutate("invalid_status",
           lambda ref: edit_facts(ref, lambda d: d["records"][5].__setitem__("status", "totally-made-up")))
    mutate("missing_matrix", lambda ref: (ref / "trim-comparison.md").unlink())
    mutate("duplicate_primary_key",
           lambda ref: edit_facts(ref, lambda d: d["records"].append(dict(d["records"][0]))))

    # —— v0.5.1 新增：来源越界、类型/值域、日期、元数据、来源唯一性、冲突主张
    mutate("negative_seats",
           lambda ref: edit_facts(ref, lambda d: rec(d, "c16-630-zx-6", "seats").__setitem__("value", -3)))
    mutate("non_numeric_battery",
           lambda ref: edit_facts(ref, lambda d: rec(d, "c11-300-lidar", "battery_capacity").__setitem__("value", "四十一点七")))
    mutate("invalid_date_99",
           lambda ref: edit_facts(ref, lambda d: d["records"][2].__setitem__("checked", "2026-99-99")))
    mutate("year_changed_to_1900",
           lambda ref: edit_facts(ref, lambda d: rec(d, "c11-640-zx", "seats").__setitem__("year", 1900)))
    mutate("duplicate_source_id",
           lambda ref: edit_sources(ref, lambda d: d["sources"].append(dict(d["sources"][0]))))
    mutate("conflict_claims_cleared",
           lambda ref: edit_facts(ref, lambda d: d["conflicts"][0].__setitem__("claims", [])))

    def unrelated_source_boosts_rank(d):
        # C11 增程电池原本只有易车间接来源；挂一个无关的 C16 官方来源并把等级改成 direct
        r = rec(d, "c11-300-lidar", "battery_capacity")
        r["source_ids"] = ["yiche-c11-config-2027", "official-c16-page-cn"]
        r["evidence"] = "direct"
    mutate("unrelated_source_boosts_rank", lambda ref: edit_facts(ref, unrelated_source_boosts_rank))

    def overbroad_marketing_covers(d):
        # 把官方宣传页的覆盖范围当成覆盖智享版的高阶硬件
        r = rec(d, "c10-290-zx", "adas_chip")
        r["value"] = "高通 8650"
        r["status"] = "confirmed"
        r["evidence"] = "direct"
        r["source_ids"] = ["official-c10-page"]
    mutate("low_trim_chip_from_marketing", lambda ref: edit_facts(ref, overbroad_marketing_covers))

    # 预算用例：改预算 → 合格集合变 → 必须失败
    mutate("budget_case_input_changed",
           lambda ref: edit_budget(ref, lambda d: d["cases"][3].__setitem__("budget_yuan", 140000)))
    # 预算用例：改 Q19 的六座过滤条件 → 合格集合变 → 必须失败
    def tamper_q19_filter(d):
        d["cases"][4]["filter"]["min_seats"] = 5
    mutate("budget_case_q19_filter_changed", lambda ref: edit_budget(ref, tamper_q19_filter))
    # 预算用例：改期望金额 → 与算法不符 → 必须失败
    def tamper_balance(d):
        d["cases"][3]["expected_excluded"][0]["balance"] = "-9999.99"
    mutate("budget_case_expected_tampered", lambda ref: edit_budget(ref, tamper_balance))

    # —— v0.5.2 新增：用例性质（open / stated / branch）不得被改写
    def find_case(d, cid):
        for c in d["cases"]:
            if c.get("id") == cid:
                return c
        raise KeyError(cid)

    # 分支用例去掉前提 → 就等于把"用户没说过的条件"当成既定条件，必须失败
    mutate("branch_precondition_removed",
           lambda ref: edit_budget(ref, lambda d: find_case(d, "Q21-price-150000").pop("precondition", None)))
    # 分支用例指向不存在的基线 → 无法证明"撤销过滤后候选只增不减"，必须失败
    mutate("branch_fallback_missing",
           lambda ref: edit_budget(ref, lambda d: find_case(d, "Q22-landing-160000").__setitem__(
               "fallback_case", "Q99-not-exist")))
    # 分期算例表被手改（把 ② 当天尚需写成全额车价）→ 与 cashflow() 不同步 → 必须失败
    def tamper_cashflow_table(ref):
        p2 = ref / "purchase-cost.md"
        s = p2.read_text(encoding="utf-8")
        s = s.replace("| 5,000 | 58,000 | 63,000 |", "| 5,000 | 60,000 | 63,000 |")
        p2.write_text(s, encoding="utf-8", newline="\n")
    mutate("cashflow_table_hand_edited", tamper_cashflow_table)

    # 分期算例缺 expected（表里看得见、断言里没有）→ 必须失败，不能"看着有 3 个算例"。
    # 这一例改的是模块内常量而不是文件，所以不能用 mutate()，要自己管临时目录与恢复。
    def cashflow_expected_missing():
        tmp, _ = prep()
        saved = CASHFLOW_CASES[1].pop("expected")
        try:
            rc = run(tmp)
        finally:
            CASHFLOW_CASES[1]["expected"] = saved
            shutil.rmtree(tmp, ignore_errors=True)
        cases.append(("cashflow_expected_missing", rc, 1))
    cashflow_expected_missing()

    # 把原题没写的硬条件塞进基线用例（模型擅自加条件）→ 必须失败
    def open_case_gains_filter(d):
        find_case(d, "Q18-landing-150000")["filter"] = {"require_lidar": True}
    mutate("open_case_gains_filter", lambda ref: edit_budget(ref, open_case_gains_filter))

    # 合法更新：改一个与预算无关的字段（整备质量 +1 kg），重新渲染后应通过。
    # 注意不能改价格——预算用例的期望值依赖指导价，改价就不是"合法更新"而是数据不一致。
    def legal(ref):
        def bump(d):
            rec(d, "c10-290-zx", "curb_weight")["value"] = 1996
        edit_facts(ref, bump)
        root = ref.parent.parent.parent
        facts, sources, budget = load(root)
        write_views(facts, budget, root)
    tmp, ref = prep()
    legal(ref)
    cases.append(("legal_update_after_render", run(tmp), 0))
    shutil.rmtree(tmp, ignore_errors=True)

    ok = True
    neg = 0
    for name, rc, expect in cases:
        good = (rc == 0) if expect == 0 else (rc != 0)
        ok = ok and good
        if expect != 0:
            neg += 1
        print("%-32s exit=%d 期望%s  %s" % (name, rc, "0" if expect == 0 else "非0",
                                            "OK" if good else "**不符合预期**"))
    print("场景合计 %d 个：错误注入 %d 个 + 基线 1 个 + 合法更新 1 个" % (len(cases), neg))
    print("SELFTEST:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def cmd_atest(root=ROOT):
    """确定性反例：预算用例（Q17–Q22、B01、B07）＋税／余额／补能／日期。

    期望值来自 budget-cases.json（由独立算式 p/1.13×5% 得出并与复核表核对），
    算法侧走 compute_tax 的另一条路径（原税 − 减税）。两条路径互为校验。
    """
    facts, _, budget = load(root)
    tinfo = trim_facts(facts)
    rows = []

    def chk(name, got, expect, note=""):
        if isinstance(got, Decimal) or isinstance(expect, Decimal):
            ok = q2(Decimal(str(got))) == q2(Decimal(str(expect)))
        else:
            ok = got == expect
        rows.append((name, got, expect, ok, note))

    # —— 预算用例全覆盖
    for c in budget["cases"]:
        cid = c["id"]
        if c.get("kind") == "price_ceiling":
            got = q2(Decimal(c["budget_yuan"]) * (1 + TAX_RULES["vat"]) /
                     (1 + TAX_RULES["vat"] + TAX_RULES["rate"] / 2))
            chk("%s 裸车上限(元)" % cid, got, Decimal(c["expected_max_price_yuan"]),
                "13 万落地 → 裸车约 12.45 万")
            continue
        qual, nums = solve_case(c, tinfo)
        chk("%s 候选集合" % cid, qual, sorted(c["expected_qualified"]),
            "精确比较集合，不只看个数")
        for row in c.get("expected_excluded") or []:
            t = row["trim"]
            if t not in nums:
                chk("%s/%s 在范围内" % (cid, t), False, True)
                continue
            p, tax, bal = nums[t]
            if "tax" in row:
                chk("%s/%s 购置税(元)" % (cid, t), tax, Decimal(str(row["tax"])),
                    "独立算式 含税÷1.13×5%")
            if "balance" in row:
                chk("%s/%s 余额(元)" % (cid, t), bal, Decimal(str(row["balance"])),
                    "预算−裸车−购置税，未扣保险")

    # —— 分支用例：撤销过滤后必须是基线的超集
    by_id = {c["id"]: c for c in budget["cases"] if c.get("id")}
    for c in budget["cases"]:
        if c.get("scope") != "branch":
            continue
        fb = by_id.get(c.get("fallback_case"))
        if not fb:
            chk("%s fallback 存在" % c["id"], False, True, "分支必须有基线用例")
            continue
        q, _ = solve_case(c, tinfo)
        bq, _ = solve_case(fb, tinfo)
        chk("%s 撤销过滤后只增不减" % c["id"], sorted(set(q) - set(bq)), [],
            "基线 %s 必须包含分支全部候选" % fb["id"])

    # —— 分期现金流：按时点分栏，⑤ 不得与 ②③ 相加
    for c in CASHFLOW_CASES:
        got = cashflow(**c["inputs"])
        for k, v in (c.get("expected") or {}).items():
            chk("%s %s(元)" % (c["id"], k), got[k], Decimal(str(v)),
                "①先前已付／②当天／A累计／③未来／⑤贷款方／B全期")
        if c.get("expected"):
            chk("%s ⑤已含当日费" % c["id"],
                got["lender_total"] - got["future"],
                Decimal(str(c["inputs"].get("lender_fee_today", 0))),
                "⑤ = 当日贷款方费用 + ③")

    # —— 税费上限与跨年
    chk("A05 含税33.9万 实缴(元)", compute_tax(Decimal("339000"))["due"], Decimal("15000"))
    chk("A05 含税56.5万 实缴(元)", compute_tax(Decimal("565000"))["due"], Decimal("35000"))
    chk("A05 含税56.5万 原税(元)", compute_tax(Decimal("565000"))["original"], Decimal("50000"))
    chk("A05 未触顶时实缴=原税一半", compute_tax(Decimal("125800"))["due"],
        q2(compute_tax(Decimal("125800"))["original"] / 2))
    # 边界三态：触顶 ≠ 实缴多于半额
    chk("A05 33.9万 判定=恰好触顶", compute_tax(Decimal("339000"))["cap_state"], "exact")
    chk("A05 33.9万 实缴仍等于半额",
        q2(compute_tax(Decimal("339000"))["due"] * 2),
        compute_tax(Decimal("339000"))["original"], "原税恰 3 万，两算式同值")
    chk("A05 56.5万 判定=封顶生效", compute_tax(Decimal("565000"))["cap_state"], "capped")
    chk("A05 12.58万 判定=未触顶", compute_tax(Decimal("125800"))["cap_state"], "none")
    chk("A06 2027-12-31 在窗口内", tax_applicable("2027-12-31"), True)
    chk("A06 2028-01-01 不在窗口内", tax_applicable("2028-01-01"), False)
    try:
        tax_applicable("2026-99-99")
        chk("A06 非法日期被拒绝", False, True, "2026-99-99 不应返回 True")
    except ValueError:
        chk("A06 非法日期被拒绝", True, True)

    # —— 补能次数
    chk("A10 距离<可用续航", charge_stops(300, 400), 0)
    chk("A10 距离=可用续航", charge_stops(400, 400), 0)
    chk("A10 距离=2倍续航", charge_stops(800, 400), 1)

    bad = 0
    for name, got, expect, ok, note in rows:
        if not ok:
            bad += 1
        print("%-34s 实得 %-28s 期望 %-20s %s %s"
              % (name, got, expect, "OK" if ok else "**FAIL**",
                 ("(" + note + ")") if note else ""))
    print("断言 %d 条，失败 %d 条" % (len(rows), bad))
    print("A-TESTS:", "PASS" if bad == 0 else "FAIL %d 项" % bad)
    return 0 if bad == 0 else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["check", "render", "tax", "budget", "selftest", "atest"])
    ap.add_argument("--root", default=str(ROOT))
    a = ap.parse_args()
    if a.cmd == "check":
        return cmd_check(Path(a.root))
    if a.cmd == "render":
        facts, sources, budget = load(Path(a.root))
        errs = validate(facts, sources) + validate_budget(budget, facts)
        if errs:
            for x in errs:
                print("FAIL:", x)
            print("数据不合法，拒绝渲染视图")
            return 1
        write_views(facts, budget, Path(a.root))
        print("已生成 trim-comparison.md、purchase-cost.md 税表、test-cases.md 预算表")
        return 0
    if a.cmd == "tax":
        return cmd_tax(Path(a.root))
    if a.cmd == "budget":
        return cmd_budget(Path(a.root))
    if a.cmd == "atest":
        return cmd_atest(Path(a.root))
    return cmd_selftest()


if __name__ == "__main__":
    sys.exit(main())
