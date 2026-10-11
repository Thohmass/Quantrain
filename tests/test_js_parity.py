"""The browser engine (prototype/src/engine.mjs) must build exactly the circuit the Python translator builds.

Run from the project root:  python tests/test_js_parity.py      (needs Node.js 18+)

For every level solution, for random builds on 10-rail / 4-train levels and for random community puzzles
(sent through the share code and back, tools/export_puzzles.mjs):
  • the Qiskit code the browser shows ("Under the hood") is executed here and compared, instruction by
    instruction, with quantrain.build_circuit;
  • the browser's statevector simulation of that circuit and its track physics are compared with
    Qiskit's exact probabilities.
"""
from __future__ import annotations

import json
import math
import random
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from quantrain import build_circuit, exact_outcomes, ideal_run, load_level      # noqa: E402
from test_engine import big_level, random_items, random_together_items, together_level   # noqa: E402


def js_key(key: tuple) -> str:
    stops, exit_rail = key
    return f"{','.join(stops)}|{exit_rail or 'derail'}"


def cases() -> list[dict]:
    out = []
    for path in sorted((ROOT / "levels").glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        for name, items in data.get("solutions", {}).items():
            out.append({"name": f"{path.stem}/{name}", "level": data, "placements": items})
    rng = random.Random(5)
    for seed in range(8):
        data = big_level(seed)
        level = load_level(data)
        for k in range(4):
            out.append({"name": f"fuzz-{seed}/{k}", "level": data, "placements": random_items(level, rng)})
    for seed in range(8):
        data = together_level(seed)
        clean = {k: v for k, v in data.items() if not k.startswith("_")}
        for k in range(4):
            out.append({"name": f"together-{seed}/{k}", "level": clean, "placements": random_together_items(data, rng)})
    return out


def same_instruction(a, b) -> bool:
    if a.operation.name != b.operation.name:
        return False
    pa, pb = list(a.operation.params), list(b.operation.params)
    if len(pa) != len(pb) or any(not math.isclose(float(x), float(y), abs_tol=1e-12) for x, y in zip(pa, pb)):
        return False
    if a.operation.name == "barrier" and getattr(a.operation, "label", None) != getattr(b.operation, "label", None):
        return False
    return True


def test_js_matches_python():
    node = shutil.which("node")
    if not node:
        print("skip: Node.js not found")
        return
    all_cases = cases()
    res = subprocess.run([node, str(ROOT / "tools/export_puzzles.mjs"), "40"], capture_output=True, text=True, cwd=ROOT)
    assert res.returncode == 0, res.stderr                           # community puzzles: share code → level file → same circuits
    puzzles = [{k: c[k] for k in ("name", "level", "placements")} for c in json.loads(res.stdout)]
    all_cases += puzzles
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(all_cases, f)
    res = subprocess.run([node, str(ROOT / "tools/export_circuits.mjs"), f.name], capture_output=True, text=True, cwd=ROOT)
    assert res.returncode == 0, res.stderr
    results = json.loads(res.stdout)

    checked = 0
    for case, per_train in zip(all_cases, results):
        level = load_level(case["level"])
        elements = level.layout(case["placements"])
        ideal = ideal_run(level, elements)
        for gi, (group, js) in enumerate(zip(level.groups(), per_train)):
            where = f"{case['name']} / trains {[t.id for t in group]}"
            ns: dict = {}
            exec(js["python"], ns)                                   # the code shown under the hood
            from_js = ns["qc"]
            from_py = build_circuit(level, elements, group)
            assert len(from_js.data) == len(from_py.data), f"{where}: {len(from_js.data)} vs {len(from_py.data)} instructions"
            for i, (a, b) in enumerate(zip(from_js.data, from_py.data)):
                qa = [from_js.find_bit(q).index for q in a.qubits]
                qb = [from_py.find_bit(q).index for q in b.qubits]
                assert same_instruction(a, b) and qa == qb, f"{where}: instruction {i}: {a.operation.name}{qa} vs {b.operation.name}{qb}"
            exact = {js_key(k): p for k, p in exact_outcomes(level, elements, group).items()}
            for name in ("circuit", "track"):
                got = js[name]
                for k in set(exact) | set(got):
                    assert abs(exact.get(k, 0) - got.get(k, 0)) < 1e-9, f"{where}: {name} {k}: {got.get(k, 0)} vs {exact.get(k, 0)}"
            want = {"shots": ideal["groups"][gi]["shots"], "picked": ideal["picked"], "total": ideal["total"], "cars": ideal["cars"]}
            assert js["ideal"] == want, f"{where}: ideal run {js['ideal']} vs {want}"
            checked += 1
    print(f"     {checked} circuits identical, probabilities and ideal runs equal ({len(puzzles)} shared puzzles among them)")


if __name__ == "__main__":
    test_js_matches_python()
    print("ok  test_js_matches_python")
