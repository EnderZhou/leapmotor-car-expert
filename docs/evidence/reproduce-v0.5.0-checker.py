"""Run v0.5.0 validation counterexamples on isolated copies only.

Expected on a corrected checker: reject each injected case before rendering.
Exit 1 means at least one invalid mutation was accepted.
"""
import contextlib
import copy
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile

sys.dont_write_bytecode = True
root = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("review05", root / "scripts/facts.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
facts, sources = module.load(root)
results = []

for case in ["negative_seats", "indirect_upgraded_by_unrelated_source", "low_trim_chip_overreach"]:
    with tempfile.TemporaryDirectory(prefix="leap-v05-review-") as temp:
        target = Path(temp)
        ref = target / "source/leapmotor-car-expert/references"
        ref.mkdir(parents=True)
        data, source_data = copy.deepcopy(facts), copy.deepcopy(sources)
        if case == "negative_seats":
            next(r for r in data["records"] if r["field"] == "seats")["value"] = -3
        elif case == "indirect_upgraded_by_unrelated_source":
            item = next(r for r in data["records"]
                        if r["field"] == "battery_capacity" and r["trim"] == "c11-300-lidar")
            item["source_ids"].append("official-c16-page-cn")
            item["evidence"] = "direct"
        else:
            item = next(r for r in data["records"]
                        if r["field"] == "adas_chip" and r["trim"] == "c10-290-zx")
            item.update(value="高通 8650", status="confirmed", evidence="direct",
                        source_ids=["official-c10-page"])
        (ref / "fact-records.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        (ref / "sources.json").write_text(json.dumps(source_data, ensure_ascii=False), encoding="utf-8")
        (ref / "purchase-cost.md").write_text((module.REF / "purchase-cost.md").read_text(encoding="utf-8"), encoding="utf-8")
        errors = module.validate(data, source_data)
        result = {"case": case, "validation_errors": errors}
        if errors:
            result["rejected"] = True
        else:
            module.write_views(data, target)
            captured = io.StringIO()
            with contextlib.redirect_stdout(captured):
                code = module.cmd_check(target)
            result.update(rejected=code != 0, check_exit=code, output=captured.getvalue())
        results.append(result)

print(json.dumps(results, ensure_ascii=False, indent=2))
sys.exit(0 if all(r["rejected"] for r in results) else 1)
