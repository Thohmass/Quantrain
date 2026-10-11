"""Checks for the level format and the Qiskit translator.

Run from the project root:  python tests/test_engine.py      (or: python -m pytest tests)

The core check: for every level, every shipped solution and every train, the Qiskit statevector
and the independent reference simulator (quantrain/reference.py) give the same outcome probabilities.
A 10-rail, 4-train fuzz level does the same for hundreds of random builds.
"""
from __future__ import annotations

import math
import random
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from qiskit.circuit.library import RYGate, XXPlusYYGate          # noqa: E402
from qiskit.quantum_info import Operator                         # noqa: E402

from quantrain import ideal_run, ideal_shots, LevelError, decode, exact_outcomes, load_level, sample   # noqa: E402
from quantrain.reference import outcomes as reference_outcomes                  # noqa: E402

LEVELS = sorted((ROOT / "levels").glob("*.json"))


def same(a: dict, b: dict, tol: float = 1e-9) -> bool:
    return all(abs(a.get(k, 0) - b.get(k, 0)) < tol for k in set(a) | set(b))


def test_points_gate_is_a_real_beam_splitter():
    for theta in [0.3, math.pi / 2, 2.0]:
        full = Operator(XXPlusYYGate(theta, math.pi / 2)).data
        # single-train subspace: |01⟩ (train on qubit 0) and |10⟩ (train on qubit 1)
        sub = full[np.ix_([1, 2], [1, 2])]
        assert np.allclose(sub, Operator(RYGate(theta)).data), theta
        assert np.isclose(abs(full[0, 0]), 1) and np.isclose(abs(full[3, 3]), 1)   # no train / two trains untouched


def test_levels_load_and_match_reference():
    assert LEVELS, "no level files found"
    for path in LEVELS:
        level = load_level(path)
        for name in level.solutions:
            elements = level.solution(name)
            for group in level.groups():
                q, r = exact_outcomes(level, elements, group), reference_outcomes(level, elements, group)
                assert same(q, r), f"{path.name}/{name}/{group[0].id}: qiskit {q} vs reference {r}"
                assert math.isclose(sum(q.values()), 1, abs_tol=1e-9)


def test_dark_port_physics():
    level = load_level(ROOT / "levels" / "04-dark-port.json")
    train = level.trains[0]
    empty = exact_outcomes(level, level.solution("untouched"), train)
    half = exact_outcomes(level, level.solution("half-turn"), train)
    quarter = exact_outcomes(level, level.solution("quarter-turn"), train)
    assert math.isclose(empty[(("stop-b",), "B")], 1, abs_tol=1e-9)        # dark port: everything to B
    assert math.isclose(half[(("stop-a",), "A")], 1, abs_tol=1e-9)         # a π twist sends everything to A
    assert math.isclose(quarter[(("stop-a",), "A")], 0.5, abs_tol=1e-9)    # π/2 twist: back to 50/50


def test_switch_both_ways():
    """Phase difference picks the exit of a Mach-Zehnder loop: π in the first loop, a cancelling π in the second."""
    level = load_level(ROOT / "levels" / "11-switch-both-ways.json")
    expect = {"empty": (("second",), "B"), "first-only": (("first",), "A"), "both-ways": (("first", "second"), "B")}
    for name, key in expect.items():
        q = exact_outcomes(level, level.solution(name), level.trains)
        assert math.isclose(q.get(key, 0), 1, abs_tol=1e-9), (name, q)


def test_quantum_points_is_fifty_fifty_and_twist_does_not_matter():
    level = load_level(ROOT / "levels" / "03-quantum-points.json")
    train = level.trains[0]
    for name in ["split", "split-and-twist"]:
        out = exact_outcomes(level, level.solution(name), train)
        assert math.isclose(out[(("stop-a",), "A")], 0.5, abs_tol=1e-9)
        assert math.isclose(out[(("stop-b",), "B")], 0.5, abs_tol=1e-9)


def test_station_mid_line_destroys_interference():
    # dark port with a station on rail B between the two points: the detector reveals the path
    level = load_level({
        "format": "quantrain-level/1", "id": "t-mid-station", "rails": ["A", "B"], "columns": 4,
        "trains": [{"id": "t", "depot": "A"}],
        "slots": [{"col": 2, "rails": ["B"]}],
        "fixed": [{"type": "points", "col": 1, "rails": ["A", "B"]}, {"type": "points", "col": 3, "rails": ["A", "B"]}],
        "stations": [{"id": "spy", "rail": "A", "col": 2}, {"id": "end-a", "rail": "A", "col": 4}, {"id": "end-b", "rail": "B", "col": 4}],
        "supply": {"twist": 1},
    })
    for steps in range(8):
        els = level.layout([{"type": "twist", "col": 2, "rails": ["B"], "steps": steps}])
        out = exact_outcomes(level, els, level.trains[0])
        assert same(out, reference_outcomes(level, els, level.trains[0]))
        p_end_a = sum(p for (stops, _), p in out.items() if "end-a" in stops)
        assert math.isclose(p_end_a, 0.5, abs_tol=1e-9), (steps, out)     # no twist can fix it any more
        p_two_stops = sum(p for (stops, _), p in out.items() if len(stops) == 2)
        assert math.isclose(p_two_stops, 0.5, abs_tol=1e-9)               # seen by 'spy' and again at the end


def big_level(seed: int) -> dict:
    """10 rails, 4 trains, 8 columns, slots everywhere, two stations on one rail."""
    rng = random.Random(seed)
    rails = [f"R{i}" for i in range(10)]
    stations = [
        {"id": "mid-4", "rail": "R4", "col": 4},
        {"id": "end-4", "rail": "R4", "col": 8},
        {"id": "end-1", "rail": "R1", "col": 8},
        {"id": "end-7", "rail": "R7", "col": 8},
    ]
    taken = {(s["col"], s["rail"]) for s in stations}
    slots = []
    for col in range(1, 8):
        i = col % 2                                        # stagger pair slots like a brick wall
        while i < 10:
            if i + 1 < 10 and rng.random() < 0.7 and (col, rails[i]) not in taken and (col, rails[i + 1]) not in taken:
                slots.append({"col": col, "rails": [rails[i], rails[i + 1]]})
                i += 2
            else:
                if (col, rails[i]) not in taken:
                    slots.append({"col": col, "rails": [rails[i]]})
                i += 1
    return {
        "format": "quantrain-level/1", "id": f"fuzz-{seed}", "rails": rails, "columns": 8,
        "trains": [{"id": f"t{k}", "colour": c, "depot": rails[d]}
                   for k, (c, d) in enumerate([("#f2683a", 0), ("#3f57f0", 3), ("#2f9e6b", 6), ("#c64fbf", 9)])],
        "slots": slots, "stations": stations,
        "supply": {"twist": None, "points": None, "cross": None},
    }


def random_build(level, rng):
    return level.layout(random_items(level, rng))


def cell_items(rails, slots, rng, owner=None, skip=0.25):
    """Random legal build on a grid of build cells: walking each column top to bottom, a free cell takes a
    twist, or a two-rail element together with the free cell below it (two twists, or one pair element)."""
    cells = {(s["col"] if isinstance(s, dict) else s.col, r) for s in slots for r in (s["rails"] if isinstance(s, dict) else s.rails)}
    items, used = [], set()
    for col in sorted({c for c, _ in cells}):
        for i, r in enumerate(rails):
            if (col, r) not in cells or (col, r) in used or rng.random() < skip:
                continue
            below = rails[i + 1] if i + 1 < len(rails) else None
            if below and (col, below) in cells and (col, below) not in used and rng.random() < 0.6:
                if owner and owner[r] != owner[below]:
                    kind = "interlock"
                else:
                    kind = rng.choice(["points", "points", "cross"])
                item = {"type": kind, "col": col, "rails": [r, below]}
                if kind == "points":
                    item["stay"] = rng.choice([50, 50, 25, 80, 0, 100])
                items.append(item)
                used |= {(col, r), (col, below)}
            else:
                items.append({"type": "twist", "col": col, "rails": [r], "steps": rng.randrange(8)})
                used.add((col, r))
    return items


def random_items(level, rng):
    return cell_items(level.rails, level.slots, rng)


def test_fuzz_ten_rails_four_trains():
    rng = random.Random(1)
    for seed in range(12):
        level = load_level(big_level(seed))
        for _ in range(6):
            els = random_build(level, rng)
            for group in level.groups():
                q, r = exact_outcomes(level, els, group), reference_outcomes(level, els, group)
                assert same(q, r, 1e-8), f"seed {seed}, trains {[t.id for t in group]}"


def test_entangled_couples():
    level = load_level(ROOT / "levels" / "14-entangled-couples.json")
    group = level.groups()[0]
    assert len(group) == 2                                              # both trains share one circuit
    indep = exact_outcomes(level, level.solution("independent"), group)
    ent = exact_outcomes(level, level.solution("entangled"), group)
    # without the interlock the teal train always reaches D; orange is 50/50 → couples meet half the time
    assert math.isclose(indep[(("a", "d"), "A+D")], 0.5, abs_tol=1e-9)
    assert math.isclose(indep[(("b", "d"), "B+D")], 0.5, abs_tol=1e-9)
    # with it: a Bell pair. Each train alone is still 50/50, but they always end on matching stations
    assert math.isclose(ent[(("a", "d"), "A+D")], 0.5, abs_tol=1e-9)
    assert math.isclose(ent[(("b", "c"), "B+C")], 0.5, abs_tol=1e-9)
    assert len(ent) == 2


def together_level(seed: int) -> dict:
    """2–3 trains leaving together, each on its own block of rails, joined only by interlocks."""
    rng = random.Random(100 + seed)
    blocks = [rng.choice([2, 3]) for _ in range(rng.choice([2, 3]))]
    rails, trains = [], []
    colours = ["#f2683a", "#12a39b", "#7a5cf0"]
    for t, size in enumerate(blocks):
        own = [f"T{t}R{k}" for k in range(size)]
        trains.append({"id": f"t{t}", "colour": colours[t], "depot": own[rng.randrange(size)], "rails": own})
        rails += own
    owner = {r: t["id"] for t in trains for r in t["rails"]}
    cols = 7
    stations = [{"id": f"s{k}", "rail": r, "col": cols} for k, r in enumerate(rails)]
    stations.append({"id": "mid", "rail": rails[1], "col": 4})
    taken = {(s["col"], s["rail"]) for s in stations}
    slots = []
    for col in range(1, cols):
        i = rng.randrange(2)
        while i < len(rails):
            a = rails[i]
            if (col, a) in taken:
                i += 1
                continue
            if i + 1 < len(rails) and (col, rails[i + 1]) not in taken and rng.random() < 0.7:
                slots.append({"col": col, "rails": [a, rails[i + 1]]})
                i += 2
            else:
                slots.append({"col": col, "rails": [a]})
                i += 1
    return {"format": "quantrain-level/1", "id": f"together-{seed}", "rails": rails, "columns": cols,
            "dispatch": "together", "trains": trains, "slots": slots, "stations": stations,
            "supply": {"twist": None, "points": None, "cross": None, "interlock": None}, "_owner": owner}


def random_together_items(data: dict, rng) -> list[dict]:
    return cell_items(data["rails"], data["slots"], rng, owner=data["_owner"], skip=0.2)


def test_fuzz_trains_together():
    rng = random.Random(9)
    for seed in range(12):
        data = together_level(seed)
        level = load_level({k: v for k, v in data.items() if not k.startswith("_")})
        for _ in range(5):
            els = level.layout(random_together_items(data, rng))
            group = level.groups()[0]
            q, r = exact_outcomes(level, els, group), reference_outcomes(level, els, group)
            assert same(q, r, 1e-8), f"together seed {seed}"
            assert math.isclose(sum(q.values()), 1, abs_tol=1e-9)


def test_validation_catches_mistakes():
    base = {"format": "quantrain-level/1", "id": "bad", "rails": ["A", "B", "C"], "columns": 3,
            "trains": [{"id": "t", "depot": "A"}], "supply": {"twist": 1, "points": None}}
    bad_levels = {
        "fixed points on non-neighbours": {**base, "fixed": [{"type": "points", "col": 1, "rails": ["A", "C"]}]},
        "overlap": {**base, "slots": [{"col": 1, "rails": ["A"]}, {"col": 1, "rails": ["A", "B"]}]},
        "station on a slot": {**base, "slots": [{"col": 2, "rails": ["B"]}], "stations": [{"id": "s", "rail": "B", "col": 2}]},
        "column out of range": {**base, "slots": [{"col": 4, "rails": ["A"]}]},
        "unknown rail": {**base, "trains": [{"id": "t", "depot": "Z"}]},
        "five trains": {**base, "trains": [{"id": f"t{i}", "colour": f"#00000{i}", "depot": "A"} for i in range(5)]},
        "interlock without together": {**base, "supply": {"interlock": 1}},
        "together without rails": {**base, "dispatch": "together"},
        "shared rail": {**base, "dispatch": "together", "trains": [{"id": "t", "colour": "#111111", "depot": "A", "rails": ["A", "B"]},
                                                                   {"id": "u", "colour": "#222222", "depot": "B", "rails": ["B", "C"]}]},
        "points across trains": {**base, "dispatch": "together", "fixed": [{"type": "points", "col": 1, "rails": ["B", "C"]}],
                                 "trains": [{"id": "t", "colour": "#111111", "depot": "A", "rails": ["A", "B"]},
                                            {"id": "u", "colour": "#222222", "depot": "C", "rails": ["C"]}]},
        "one-sided partner": {**base, "stations": [{"id": "s", "rail": "A", "col": 1, "partner": "x"}]},
    }
    for why, data in bad_levels.items():
        try:
            load_level(data)
        except LevelError:
            continue
        raise AssertionError(f"accepted a level with: {why}")

    level = load_level({**base, "slots": [{"col": 1, "rails": ["A"]}, {"col": 2, "rails": ["A"]}, {"col": 2, "rails": ["B", "C"]}]})
    bad_builds = {
        "not on a slot": [{"type": "twist", "col": 3, "rails": ["A"]}],
        "pair half off the grid": [{"type": "points", "col": 1, "rails": ["A", "B"]}],
        "pair on non-neighbours": [{"type": "points", "col": 2, "rails": ["A", "C"]}],
        "pair over a used cell": [{"type": "twist", "col": 2, "rails": ["B"]}, {"type": "points", "col": 2, "rails": ["B", "C"]}],
        "two on one slot": [{"type": "twist", "col": 1, "rails": ["A"]}, {"type": "twist", "col": 1, "rails": ["A"]}],
        "wrong size": [{"type": "points", "col": 1, "rails": ["A"]}],
        "supply exceeded": [{"type": "twist", "col": 1, "rails": ["A"]}, {"type": "twist", "col": 2, "rails": ["A"]}],
        "not available": [{"type": "cross", "col": 2, "rails": ["B", "C"]}],
        "steps out of range": [{"type": "twist", "col": 1, "rails": ["A"], "steps": 8}],
    }
    for why, items in bad_builds.items():
        try:
            level.layout(items)
        except LevelError:
            continue
        raise AssertionError(f"accepted a build with: {why}")


def test_build_cells_take_twists_or_pairs():
    """Two neighbouring build cells hold either two twists or one two-rail element, whichever way the
    level file groups them."""
    data = {"format": "quantrain-level/1", "id": "cells", "rails": ["A", "B", "C"], "columns": 2,
            "trains": [{"id": "t", "depot": "A"}], "supply": {"twist": None, "points": None},
            "slots": [{"col": 1, "rails": ["A", "B"]}, {"col": 2, "rails": ["B"]}, {"col": 2, "rails": ["C"]}]}
    level = load_level(data)
    two_twists = level.layout([{"type": "twist", "col": 1, "rails": ["A"], "steps": 2},
                               {"type": "twist", "col": 1, "rails": ["B"], "steps": 4}])
    assert [e.rails for e in two_twists] == [("A",), ("B",)]
    across = level.layout([{"type": "points", "col": 2, "rails": ["C", "B"]}])      # spans two separate entries
    assert across[0].rails == ("B", "C")                                             # stored top to bottom
    for group in level.groups():
        assert same(exact_outcomes(level, across, group), reference_outcomes(level, across, group))


def test_ideal_run_clears_levels_in_one_run():
    """Every level has a build that clears it with one press of Run (the ideal run), and the obvious
    wrong builds don't."""
    expect = {
        "01-first-departure": {"untouched": 3},
        "02-twist-tunnel": {"untouched": 3, "half-turn": 3},
        "03-quantum-points": {"untouched": 1, "split": 3, "split-and-twist": 3},
        "04-dark-port": {"untouched": 0, "half-turn": 3, "quarter-turn": 1},
        "05-quarter-turn": {"untouched": 1, "even-out": 3, "full-turn": 3, "half-turn": 0},
        "06-switchyard": {"untouched": 1, "route": 3},
        "07-crossed-wires": {"untouched": 0, "middle": 0, "swap-in": 3, "swap-out": 3},
        "08-fair-shares": {"untouched": 0, "tempting": 2, "fair": 3},
        "09-grand-junction": {"untouched": 0, "one": 0, "pattern": 3, "pattern-outer": 3},
        "10-nosy-inspector": {"untouched": 1, "twist": 1, "detour": 3},
        "11-switch-both-ways": {"empty": 1, "both-ways": 3, "first-only": 1},
        "12-remote-twist": {"untouched": 1, "interlock": 3},
        "13-remote-switch": {"untouched": 0, "interlock-only": 1, "split-only": 1, "entangle": 3},
        "14-entangled-couples": {"entangled": 3, "independent": 1},
        "15-swap-partners": {"untouched": 1, "interlock-only": 0, "swap": 3, "swap-c": 3},
    }
    for path in sorted((ROOT / "levels").glob("*.json")):
        level = load_level(path)
        for name, want in expect[level.id].items():
            got = ideal_run(level, level.solution(name))
            assert got["stars"] == want, (level.id, name, got["picked"], got["total"])
    assert ideal_shots({"a": 0.25, "b": 0.75}, 4) == ["b", "a", "b", "b"]
    assert sorted(ideal_shots({"a": 0.5, "b": 0.5}, 4)) == ["a", "a", "b", "b"]
    shots = ideal_shots({"x": 0.8535533905932737, "y": 0.14644660940672624}, 7)      # cos²(π/8): rounds to 6 + 1
    assert shots.count("x") == 6 and shots.count("y") == 1


def test_qollab_bridge_keeps_the_physics():
    """The circuits sent to Qollab (barriers removed, beam splitter rewritten into basic gates) have exactly the
    same outcome probabilities, and one job on a simulator returns outcomes the game knows."""
    import json
    from qiskit.providers.basic_provider import BasicSimulator
    from qiskit.quantum_info import Statevector
    from quantrain.qollab import BASIS, prepare, run_shots
    from quantrain.score import outcome_str
    from quantrain.circuit import outcome_key

    rng = random.Random(3)
    builds = []
    for path in sorted((ROOT / "levels").glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        builds += [(data, items) for items in data["solutions"].values()]
    for seed in range(3):
        data = together_level(seed)
        clean = {k: v for k, v in data.items() if not k.startswith("_")}
        builds.append((clean, random_together_items(data, rng)))
    for data, items in builds:
        level = load_level(data)
        elements = level.layout(items)
        for qc, group in zip(prepare(level, elements), level.groups()):
            assert set(qc.count_ops()) <= set(BASIS), qc.count_ops()
            bare = qc.remove_final_measurements(inplace=False)
            got = {}
            for key, p in Statevector(bare).probabilities_dict().items():
                if p > 1e-12:
                    k = outcome_str(outcome_key(decode(level, key, len(group))))
                    got[k] = got.get(k, 0) + p
            want = {outcome_str(k): p for k, p in exact_outcomes(level, elements, group).items()}
            assert all(abs(got.get(k, 0) - want.get(k, 0)) < 1e-9 for k in set(got) | set(want)), (level.id, got, want)
        out = json.loads(run_shots(BasicSimulator(), json.dumps(data), json.dumps(items), 64))
        for counts, group in zip(out["groups"], level.groups()):
            want = {outcome_str(k) for k, p in exact_outcomes(level, elements, group).items() if p > 1e-9}
            assert sum(counts.values()) == 64 and set(counts) <= want, (level.id, counts)


def test_decode_bitstrings():
    level = load_level(ROOT / "levels" / "03-quantum-points.json")
    # bit order: qubit 0 = rail A is the rightmost character; then rail B; then stop-a, stop-b
    assert decode(level, "0101") == {"exit": "A", "valid": True, "stops": ["stop-a"]}
    assert decode(level, "1010") == {"exit": "B", "valid": True, "stops": ["stop-b"]}
    assert decode(level, "0011")["valid"] is False                      # two rails lit: noise / derail


def test_sampling_agrees_with_exact():
    level = load_level(ROOT / "levels" / "03-quantum-points.json")
    els = level.solution("split")
    run = sample(level, els, shots=4000, seed=3)[0]["counts"]
    frac_a = run.get((("stop-a",), "A"), 0) / 4000
    assert abs(frac_a - 0.5) < 0.04, frac_a


if __name__ == "__main__":
    tests = [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_") and callable(f)]
    for name, fn in tests:
        fn()
        print(f"ok  {name}")
    print(f"\nall {len(tests)} checks passed")
