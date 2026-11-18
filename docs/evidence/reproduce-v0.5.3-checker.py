#!/usr/bin/env python3
"""复现复核清单列出的 12 类绕过反例，并打印检查器给出的具体理由。

第 1–8 类来自 v0.5.1 复核（P1-2：事实与来源校验可被绕过）；
第 9–11 类来自 v0.5.2 复核（预算用例擅自加条件）；
第 12 类来自 v0.5.3 复核（分期算例表与 cashflow() 不同步 —— 表被手改成"当天＝全额车价"）。

用法：python docs/evidence/reproduce-v0.5.3-checker.py

做法与 scripts/facts.py selftest 相同：把 references 复制到临时目录，注入一处改动，
调用 cmd_check(root)，**打印触发原因**，用于说明"是被哪条规则拦下的"，而不是只看 exit code。

与 v0.5.2 版脚本的两点区别：
1. 判定改为看 cmd_check 的退出码 + FAIL 行，不再只调 validate/validate_budget。
   第 12 类的拦截点在视图同步校验里（cmd_check 内），不在 validate_* 里，旧写法会漏判。
2. 反例从 11 类增到 12 类。
"""

import contextlib
import io
import json
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import facts  # noqa: E402

REF = ROOT / "source" / "leapmotor-car-expert" / "references"
FILES = ("fact-records.json", "sources.json", "budget-cases.json",
         "trim-comparison.md", "purchase-cost.md")


def prep():
    tmp = Path(tempfile.mkdtemp())
    dst = tmp / "source" / "leapmotor-car-expert" / "references"
    dst.mkdir(parents=True)
    for n in FILES:
        shutil.copy(REF / n, dst / n)
    shutil.copy(ROOT / "test-cases.md", tmp / "test-cases.md")
    return tmp, dst


def edit(path, fn):
    d = json.loads(path.read_text(encoding="utf-8"))
    fn(d)
    path.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")


def rec(d, trim, field):
    for r in d["records"]:
        if r["trim"] == trim and r["field"] == field:
            return r
    raise KeyError((trim, field))


def run(errs_fn):
    """注入一处改动后跑完整 check，返回 (是否被拦下, 拦截理由列表)。"""
    tmp, ref = prep()
    errs_fn(ref)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = facts.cmd_check(tmp)
    shutil.rmtree(tmp, ignore_errors=True)
    fails = [ln[len("FAIL: "):] for ln in buf.getvalue().splitlines()
             if ln.startswith("FAIL: ")]
    return code != 0 or bool(fails), fails


CASES = [
    ("1 负座位数（-3）", lambda ref: edit(ref / "fact-records.json",
        lambda d: rec(d, "c16-630-zx-6", "seats").__setitem__("value", -3))),
    ("2 非数值电池容量（'四十一点七'）", lambda ref: edit(ref / "fact-records.json",
        lambda d: rec(d, "c11-300-lidar", "battery_capacity").__setitem__("value", "四十一点七"))),
    ("3 非法日期 2026-99-99", lambda ref: edit(ref / "fact-records.json",
        lambda d: d["records"][2].__setitem__("checked", "2026-99-99"))),
    ("4 同版本一条记录年款改 1900", lambda ref: edit(ref / "fact-records.json",
        lambda d: rec(d, "c11-640-zx", "seats").__setitem__("year", 1900))),
    ("5 重复来源 ID", lambda ref: edit(ref / "sources.json",
        lambda d: d["sources"].append(dict(d["sources"][0])))),
    ("6 冲突主张清空", lambda ref: edit(ref / "fact-records.json",
        lambda d: d["conflicts"][0].__setitem__("claims", []))),
]


def boost_rank(ref):
    # C11 增程电池原本只有易车间接来源；挂一个无关的 C16 官方来源并把等级改成 direct
    def fn(d):
        r = rec(d, "c11-300-lidar", "battery_capacity")
        r["source_ids"] = ["yiche-c11-config-2027", "official-c16-page-cn"]
        r["evidence"] = "direct"
    edit(ref / "fact-records.json", fn)


def broad_covers(ref):
    # 用 C10 官方宣传页支撑"智享版也有 8650"，属于 covers 过宽
    def fn(d):
        r = rec(d, "c10-290-zx", "adas_chip")
        r["value"] = "高通 8650"
        r["status"] = "confirmed"
        r["evidence"] = "direct"
        r["source_ids"] = ["official-c10-page"]
    edit(ref / "fact-records.json", fn)


CASES += [
    ("7 无关来源把间接证据抬成 direct", boost_rank),
    ("8 过宽 covers：宣传页支撑低配芯片", broad_covers),
]


def find_case(d, cid):
    for c in d["cases"]:
        if c.get("id") == cid:
            return c
    raise KeyError(cid)


def branch_without_precondition(ref):
    edit(ref / "budget-cases.json",
         lambda d: find_case(d, "Q21-price-150000").pop("precondition", None))


def branch_bad_fallback(ref):
    edit(ref / "budget-cases.json",
         lambda d: find_case(d, "Q22-landing-160000").__setitem__(
             "fallback_case", "Q99-not-exist"))


def baseline_gains_filter(ref):
    # 把原题没写过的"必须带激光雷达"塞进 15 万落地基线用例
    edit(ref / "budget-cases.json",
         lambda d: find_case(d, "Q18-landing-150000").__setitem__(
             "filter", {"require_lidar": True}))


CASES += [
    ("9 分支用例删掉用户确认的前提", branch_without_precondition),
    ("10 分支用例的基线指向不存在", branch_bad_fallback),
    ("11 基线用例被塞进推断出的过滤条件", baseline_gains_filter),
]


def cashflow_table_edited(ref):
    # 把 B 例「② 提车当天尚需」从 58,000 手改成 60,000（等于把已付定金又算进当天）
    p = ref / "purchase-cost.md"
    s = p.read_text(encoding="utf-8")
    if "| 5,000 | 58,000 | 63,000 |" not in s:
        raise RuntimeError("分期算例表里找不到待改的行，反例失效，请检查 purchase-cost.md")
    s = s.replace("| 5,000 | 58,000 | 63,000 |", "| 5,000 | 60,000 | 63,000 |")
    p.write_text(s, encoding="utf-8", newline="\n")


CASES += [
    ("12 分期算例表手改（当天＝含定金）", cashflow_table_edited),
]


def main():
    base_ok, base = run(lambda ref: None)
    print("基线：%s" % ("通过，无错误" if not base_ok else "有 %d 项错误" % len(base)))
    print()
    bad = 0
    for name, fn in CASES:
        hit, errs = run(fn)
        if not hit:
            bad += 1
        print("%-40s %s" % (name, "拦住" if hit else "**未拦住**"))
        for x in errs[:3]:
            print("    - " + x)
        print()
    print("结论：%d/%d 个反例被拦下" % (len(CASES) - bad, len(CASES)))
    ok = (not base_ok) and bad == 0
    print("RESULT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
