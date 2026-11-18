"""Review diagnostic: runs only on temporary copies; never builds into the repo.

Baseline should pass. Every mutated case should fail in a corrected checker.
The duplicate case regenerates a view to isolate duplicate-key validation.
Run against the reviewed v0.4.0 implementation (scripts/facts.py).
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
spec = importlib.util.spec_from_file_location("review_facts", root / "scripts/facts.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
original = json.loads(module.OUT.read_text(encoding="utf-8"))
matrix = module.MATRIX.read_text(encoding="utf-8")
cases = ["baseline", "price_changed_to_1", "invalid_source_id", "L1_without_source",
         "missing_checked_date", "invalid_status", "missing_matrix", "duplicate_field_after_render"]
results = []

with tempfile.TemporaryDirectory(prefix="leap-v040-review-") as directory:
    module.OUT = Path(directory) / "facts.json"
    module.MATRIX = Path(directory) / "matrix.md"
    for case in cases:
        data = copy.deepcopy(original)
        if case == "price_changed_to_1":
            data["records"][0]["value"] = 1
        elif case == "invalid_source_id":
            data["records"][1]["source_ids"] = ["does-not-exist"]
        elif case == "L1_without_source":
            data["records"][0]["source_ids"] = []
        elif case == "missing_checked_date":
            data["records"][1].pop("checked")
        elif case == "invalid_status":
            data["records"][1]["status"] = "invented"
        elif case == "duplicate_field_after_render":
            data["records"].append(copy.deepcopy(data["records"][0]))
        module.OUT.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        module.MATRIX.write_text(matrix, encoding="utf-8")
        if case == "missing_matrix":
            module.MATRIX.unlink()
        if case == "duplicate_field_after_render":
            module.MATRIX.write_text(module.render(dry=True), encoding="utf-8")
        captured = io.StringIO()
        with contextlib.redirect_stdout(captured):
            code = module.check()
        results.append({"case": case, "exit_code": code,
                        "expected": "PASS" if case == "baseline" else "FAIL",
                        "output": captured.getvalue()})

print(json.dumps(results, ensure_ascii=False, indent=2))
sys.exit(0 if all((item["exit_code"] == 0) == (item["case"] == "baseline")
                 for item in results) else 1)
