"""Inspect a level: python -m quantrain levels/04-dark-port.json [--solution NAME] [--shots N]

Prints the level grid, the Qiskit circuit for each train, the exact outcome probabilities and a
sampled run, so a level and its translation can be checked by eye.
"""
from __future__ import annotations

import argparse

from . import build_circuit, exact_outcomes, fmt_phase, load_level, sample
from .level import Element


def describe(el: Element) -> str:
    extra = {"twist": f" {fmt_phase(el.steps)}", "points": f" {el.stay}:{100 - el.stay}", "cross": "", "interlock": ""}[el.type]
    return f"{'fixed ' if el.fixed else ''}{el.type}{extra}"


def grid(level, elements) -> str:
    cell = {}
    for col, r in level.cells():
        cell[(col, r)] = "·"
    for e in elements:
        for r in e.rails:
            cell[(e.col, r)] = {"twist": str(e.steps), "points": "X", "cross": "x", "interlock": "Z"}[e.type]
    for st in level.stations:
        cell[(st.col, st.rail)] = "S"
    lines = ["      depot " + " ".join(f"{c:>2}" for c in range(1, level.columns + 1)) + "  exit"]
    for r in level.rails:
        dep = ",".join(t.id for t in level.trains if t.depot == r)
        row = " ".join(f"{cell.get((c, r), '─'):>2}" for c in range(1, level.columns + 1))
        lines.append(f"  {r:>2} {dep:>6} {row}  ─▶")
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("level")
    ap.add_argument("--solution", default=None)
    ap.add_argument("--shots", type=int, default=1000)
    args = ap.parse_args()

    level = load_level(args.level)
    name = args.solution or next(iter(level.solutions), None)
    elements = level.solution(name) if name else level.layout([])
    print(f"{level.id} · {level.name} · solution: {name or '(empty build)'}")
    print(f"rails {len(level.rails)}, columns {level.columns}, stations {len(level.stations)}, "
          f"qubits {len(level.rails) + len(level.stations)}")
    print("legend: · build cell (two neighbouring cells take points / cross / interlock)  digit = twist steps (×π/4)  X points  x cross  Z interlock  S station\n")
    print(grid(level, elements))
    print("\nplaced:", ", ".join(f"{describe(e)} @{e.col}/{'-'.join(e.rails)}" for e in elements) or "nothing")

    runs = sample(level, elements, shots=args.shots, seed=7)
    for group, run in zip(level.groups(), runs):
        print(f"\n── {'trains together: ' if len(group) > 1 else 'train '}{', '.join(f'{t.id} (depot {t.depot})' for t in group)} ──")
        print(build_circuit(level, elements, group, measure=False).draw("text", fold=120))
        exact = exact_outcomes(level, elements, group)
        print(f"{'stations seen':<22}{'exit':<6}{'exact':>8}{'sampled':>10}")
        for key in sorted(set(exact) | set(run["counts"]), key=lambda k: -exact.get(k, 0)):
            stops, exit_rail = key
            print(f"{', '.join(stops) or '—':<22}{exit_rail or 'derail':<6}"
                  f"{exact.get(key, 0):>8.3f}{run['counts'].get(key, 0) / args.shots:>10.3f}")


if __name__ == "__main__":
    main()
