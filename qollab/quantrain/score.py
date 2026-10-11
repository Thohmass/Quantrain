"""The ideal run: how a level is scored, the same way the browser game plays it.

A run sends a train of `cars` cars per circuit; every car is one shot. In the ideal run the cars are spread
over the outcomes exactly in proportion to their probabilities (largest-remainder rounding), so the score
depends only on the build, never on luck. Each car picks up one passenger at every station that sees it;
couples board only if the partner station sees the same car (the same shot).

The real shots (simulator or IonQ) are shown next to this for comparison; they don't change the score.
"""
from __future__ import annotations

import math

from .circuit import exact_outcomes
from .level import Element, Level


def outcome_str(key: tuple) -> str:
    stops, exit_rail = key
    return f"{','.join(stops)}|{exit_rail or 'derail'}"


def cars_for(level: Level) -> int:
    """Cars per circuit: the level's 'cars', or enough to carry every passenger once."""
    if level.cars:
        return level.cars
    total = sum(len(s.passengers) for s in level.stations)
    return max(1, math.ceil(total / len(level.groups())))


def ideal_shots(probs: dict[str, float], cars: int) -> list[str]:
    """Spread `cars` shots over the outcomes in proportion (largest remainder), interleaved evenly."""
    keys = sorted(k for k, p in probs.items() if p > 1e-12)
    quota = [probs[k] * cars for k in keys]
    n = [math.floor(q + 1e-9) for q in quota]
    left = cars - sum(n)
    order = sorted(range(len(keys)), key=lambda i: (-round(quota[i] - n[i], 9), i))
    for i in order[:max(0, left)]:
        n[i] += 1
    cur, out = [0] * len(keys), []
    for _ in range(cars):                          # smooth weighted round robin: A B A B rather than A A B B
        for i in range(len(keys)):
            cur[i] += n[i]
        best = max(range(len(keys)), key=lambda i: (cur[i], -i))
        out.append(keys[best])
        cur[best] -= cars
    return out


def ideal_run(level: Level, elements: list[Element]) -> dict:
    """Play the ideal run: which outcome each car gets, and how many passengers it picks up."""
    waiting = {s.id: len(s.passengers) for s in level.stations}
    partner = {s.id: s.partner for s in level.stations}
    cars = cars_for(level)
    groups = []
    for group in level.groups():
        probs = {outcome_str(k): p for k, p in exact_outcomes(level, elements, group).items()}
        shots = ideal_shots(probs, cars)
        for key in shots:
            seen = {s for s in key.split("|")[0].split(",") if s}
            for sid in seen:
                if partner[sid] and partner[sid] not in seen:
                    continue
                if waiting[sid] > 0:
                    waiting[sid] -= 1
        groups.append({"trains": [t.id for t in group], "probs": probs, "shots": shots})
    total = sum(len(s.passengers) for s in level.stations)
    picked = total - sum(waiting.values())
    return {"cars": cars, "groups": groups, "picked": picked, "total": total,
            "cleared": total > 0 and picked == total, "stars": stars(picked, total)}


def stars(picked: int, total: int) -> int:
    if total == 0:
        return 0
    if picked == total:
        return 3
    return 2 if picked * 3 >= total * 2 else 1 if picked * 3 >= total else 0
