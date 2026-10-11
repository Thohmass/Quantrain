"""Independent reference simulator — no Qiskit, just the game physics.

Used to check the Qiskit translator, and it is the exact algorithm the browser game uses for its
preview. The state is a dict: configuration → complex amplitude, where a configuration says which
rail each train is on (a tuple of rail indices, one per train in the group). With one train this is
just one amplitude per rail. At a station column the stations see (or don't see) the trains and the
state branches.
"""
from __future__ import annotations

import cmath
import math
from collections import defaultdict

from .level import Element, Level, Train

Config = tuple[int, ...]


def apply(state: dict[Config, complex], level: Level, el: Element) -> dict[Config, complex]:
    q = level.rail_index
    if el.type == "twist":
        k, ph = q(el.rails[0]), cmath.exp(1j * el.phi)
        return {c: a * ph if k in c else a for c, a in state.items()}
    i, j = q(el.rails[0]), q(el.rails[1])
    if el.type == "interlock":                      # CZ: −1 when one train is on i and another on j
        return {c: -a if (i in c and j in c) else a for c, a in state.items()}
    if el.type == "cross":
        swap = lambda r: j if r == i else i if r == j else r
        return {tuple(swap(r) for r in c): a for c, a in state.items()}
    # points: RY(θ) on the train that is on rail i or j — [stay, switch] = [[cs, -sn], [sn, cs]]
    cs, sn = math.cos(el.theta / 2), math.sin(el.theta / 2)
    out: dict[Config, complex] = defaultdict(complex)
    for c, a in state.items():
        if i in c:
            t = c.index(i)
            out[c] += cs * a
            out[c[:t] + (j,) + c[t + 1:]] += sn * a
        elif j in c:
            t = c.index(j)
            out[c[:t] + (i,) + c[t + 1:]] += -sn * a
            out[c] += cs * a
        else:
            out[c] += a
    return dict(out)


def outcomes(level: Level, elements: list[Element], trains: Train | list[Train]) -> dict[tuple, float]:
    """Probabilities of (stations that saw a train, exit rails joined with '+')."""
    trains = [trains] if isinstance(trains, Train) else list(trains)
    q = level.rail_index
    branches = [((), {tuple(q(t.depot) for t in trains): 1 + 0j})]
    for col in range(1, level.columns + 1):
        for el in elements:
            if el.col == col:
                branches = [(seen, apply(state, level, el)) for seen, state in branches]
        stops = [s for s in level.stations if s.col == col]
        if not stops:
            continue
        nxt = []
        for seen, state in branches:
            groups: dict[tuple, dict] = defaultdict(dict)
            for c, a in state.items():                       # which stations in this column see a train
                groups[tuple(s.id for s in stops if q(s.rail) in c)][c] = a
            for hit, sub in groups.items():
                if sum(abs(a) ** 2 for a in sub.values()) > 1e-30:
                    nxt.append(((*seen, *hit), sub))
        branches = nxt
    out: dict[tuple, float] = defaultdict(float)
    for seen, state in branches:
        for c, a in state.items():
            p = abs(a) ** 2
            if p > 1e-12:
                out[(seen, "+".join(level.rails[k] for k in sorted(c)))] += p
    return dict(out)
