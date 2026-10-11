"""Quantrain level description: load, validate, and place player elements.

A level is a grid. Columns are time steps (1..columns), rails are qubits (top to bottom).
The depot sits before column 1, the exit after the last column. Every cell (column, rail)
holds at most one thing: a build cell, a fixed element, or a station. The player builds on
build cells: a twist takes one cell, a two-rail element takes two neighbouring cells of one column.

The level file is the single source of truth. The 3D scene, the in-browser simulation and
the Qiskit circuit are all derived from a level plus the player's placements.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

FORMAT = "quantrain-level/1"
MAX_RAILS = 12
MAX_TRAINS = 4
TWIST_STEPS = 8                       # a twist turns in steps of π/4; 8 steps = 2π = 0

# element type -> how many neighbouring rails it spans
ELEMENT_SPAN = {"twist": 1, "points": 2, "cross": 2, "interlock": 2}
# sequential: trains take turns, one circuit each.  together: all trains leave at once on their own
# rails (one circuit); only an interlock connects rails of different trains. See docs/HOW_IT_WORKS.md.
DISPATCH_MODES = {"sequential", "together"}


class LevelError(ValueError):
    """The level file or a placement breaks a rule. The message says which one."""


@dataclass(frozen=True)
class Element:
    type: str
    col: int
    rails: tuple[str, ...]
    steps: int = 0                    # twist: phase φ = steps · π/4
    stay: int = 50                    # points: % chance to stay on the same rail (50 = 50:50)
    fixed: bool = False

    @property
    def phi(self) -> float:
        return (self.steps % TWIST_STEPS) * math.pi / 4

    @property
    def theta(self) -> float:
        """Beam-splitter angle: P(stay) = cos²(θ/2)."""
        return 2 * math.acos(math.sqrt(self.stay / 100))


@dataclass(frozen=True)
class Slot:
    """An entry of the level's 'slots' list: build cells in one column (one per listed rail)."""
    col: int
    rails: tuple[str, ...]


@dataclass(frozen=True)
class Station:
    id: str
    name: str
    rail: str
    col: int
    passengers: tuple[str, ...]
    partner: str | None = None        # couples: passengers here board only if the partner station also sees a train


@dataclass(frozen=True)
class Train:
    id: str
    colour: str
    depot: str
    rails: tuple[str, ...] = ()       # dispatch "together": the rails this train owns


@dataclass
class Level:
    id: str
    name: str
    blurb: str
    rails: list[str]
    columns: int
    dispatch: str
    trains: list[Train]
    slots: list[Slot]
    fixed: list[Element]
    stations: list[Station]
    supply: dict[str, int | None]     # type -> count; None = unlimited; missing type = not available
    solutions: dict[str, list[dict]]
    cars: int | None = None           # cars (shots) per run and circuit; None = enough for every passenger

    def rail_index(self, rail: str) -> int:
        return self.rails.index(rail)

    def owner(self, rail: str) -> Train | None:
        """In 'together' levels: the train that owns this rail."""
        return next((t for t in self.trains if rail in t.rails), None)

    def groups(self) -> list[list[Train]]:
        """Trains that share one circuit: each train alone (sequential) or all together."""
        return [list(self.trains)] if self.dispatch == "together" else [[t] for t in self.trains]

    def adjacent(self, a: str, b: str) -> bool:
        return abs(self.rail_index(a) - self.rail_index(b)) == 1

    def cells(self) -> set[tuple[int, str]]:
        """Build cells (column, rail)."""
        return {(s.col, r) for s in self.slots for r in s.rails}

    def ordered(self, rails) -> tuple[str, ...]:
        """Rails top to bottom (placements are stored this way)."""
        return tuple(sorted(rails, key=self.rail_index))

    def layout(self, placements: list[dict] | list[Element]) -> list[Element]:
        """Fixed elements plus validated player placements, in column order."""
        placed = place(self, placements)
        return sorted([*self.fixed, *placed], key=lambda e: e.col)

    def solution(self, name: str) -> list[Element]:
        if name not in self.solutions:
            raise LevelError(f"{self.id}: no solution called '{name}' (have: {', '.join(self.solutions) or 'none'})")
        return self.layout(self.solutions[name])


# ───────────────────────── loading ─────────────────────────

def load_level(source: str | Path | dict) -> Level:
    """Load a level from a path, a JSON string or an already-parsed dict, and validate it."""
    if isinstance(source, dict):
        data = source
    else:
        is_text = isinstance(source, str) and source.lstrip().startswith("{")
        text = source if is_text else Path(source).read_text(encoding="utf-8")
        data = json.loads(text)

    if data.get("format") != FORMAT:
        raise LevelError(f"expected format '{FORMAT}', got '{data.get('format')}'")
    lid = data.get("id", "?")

    def need(key):
        if key not in data:
            raise LevelError(f"{lid}: missing '{key}'")
        return data[key]

    level = Level(
        id=lid,
        name=data.get("name", lid),
        blurb=data.get("blurb", ""),
        rails=list(need("rails")),
        columns=int(need("columns")),
        dispatch=data.get("dispatch", "sequential"),
        trains=[Train(t["id"], t.get("colour", "#f2683a"), t["depot"], tuple(t.get("rails", []))) for t in need("trains")],
        slots=[Slot(int(s["col"]), tuple(s["rails"])) for s in data.get("slots", [])],
        fixed=[_element(e, fixed=True, lid=lid) for e in data.get("fixed", [])],
        stations=[Station(s["id"], s.get("name", s["id"]), s["rail"], int(s["col"]), tuple(s.get("passengers", [])),
                          s.get("partner")) for s in data.get("stations", [])],
        supply=dict(data.get("supply", {})),
        solutions=dict(data.get("solutions", {})),
        cars=data.get("cars"),
    )
    validate(level)
    for name, items in level.solutions.items():   # a level ships only solutions that are legal
        try:
            place(level, items)
        except LevelError as err:
            raise LevelError(f"{lid}: solution '{name}' is not legal: {err}") from None
    return level


def _element(d: dict, *, fixed: bool, lid: str) -> Element:
    t = d.get("type")
    if t not in ELEMENT_SPAN:
        raise LevelError(f"{lid}: unknown element type '{t}' (known: {', '.join(ELEMENT_SPAN)})")
    steps = int(d.get("steps", 0))
    stay = int(d.get("stay", 50))
    if t == "twist" and not 0 <= steps < TWIST_STEPS:
        raise LevelError(f"{lid}: twist steps must be 0..{TWIST_STEPS - 1}, got {steps}")
    if t == "points" and not 0 <= stay <= 100:
        raise LevelError(f"{lid}: points 'stay' must be 0..100, got {stay}")
    return Element(t, int(d["col"]), tuple(d["rails"]), steps=steps, stay=stay, fixed=fixed)


# ───────────────────────── validation ─────────────────────────

def validate(level: Level) -> None:
    lid = level.id
    if not 1 <= len(level.rails) <= MAX_RAILS:
        raise LevelError(f"{lid}: needs 1..{MAX_RAILS} rails, has {len(level.rails)}")
    if len(set(level.rails)) != len(level.rails):
        raise LevelError(f"{lid}: rail names must be unique")
    if level.columns < 1:
        raise LevelError(f"{lid}: needs at least 1 column")
    if level.dispatch not in DISPATCH_MODES:
        raise LevelError(f"{lid}: dispatch '{level.dispatch}' is not supported yet (have: {', '.join(DISPATCH_MODES)})")
    if not 1 <= len(level.trains) <= MAX_TRAINS:
        raise LevelError(f"{lid}: needs 1..{MAX_TRAINS} trains, has {len(level.trains)}")
    if len({t.id for t in level.trains}) != len(level.trains) or len({t.colour.lower() for t in level.trains}) != len(level.trains):
        raise LevelError(f"{lid}: train ids and colours must be unique")
    for t in level.trains:
        _rail_ok(level, t.depot, f"train '{t.id}' depot")
    for typ, n in level.supply.items():
        if typ not in ELEMENT_SPAN:
            raise LevelError(f"{lid}: supply lists unknown element '{typ}'")
        if n is not None and (not isinstance(n, int) or n < 0):
            raise LevelError(f"{lid}: supply of '{typ}' must be a whole number ≥ 0 or null (unlimited)")
    if level.cars is not None and (not isinstance(level.cars, int) or not 1 <= level.cars <= 64):
        raise LevelError(f"{lid}: 'cars' must be a whole number 1..64")
    if len({s.id for s in level.stations}) != len(level.stations):
        raise LevelError(f"{lid}: station ids must be unique")
    ids = {s.id: s for s in level.stations}
    for s in level.stations:
        if s.partner is not None and (s.partner not in ids or ids[s.partner].partner != s.id):
            raise LevelError(f"{lid}: station '{s.id}' and its partner '{s.partner}' must name each other")
    if level.dispatch == "together":
        owned: list[str] = []
        for t in level.trains:
            if not t.rails or t.depot not in t.rails:
                raise LevelError(f"{lid}: in a 'together' level every train lists its rails, including its depot")
            for r in t.rails:
                _rail_ok(level, r, f"train '{t.id}'")
            owned += t.rails
        if len(set(owned)) != len(owned):
            raise LevelError(f"{lid}: two trains own the same rail")
    elif "interlock" in level.supply or any(e.type == "interlock" for e in level.fixed):
        raise LevelError(f"{lid}: interlocks need trains that leave together (dispatch 'together')")

    cells: dict[tuple[int, str], str] = {}

    def claim(col: int, rails: tuple[str, ...], what: str, is_element: bool = False):
        if not 1 <= col <= level.columns:
            raise LevelError(f"{lid}: {what} is in column {col}, outside 1..{level.columns}")
        for r in rails:
            _rail_ok(level, r, what)
        if is_element and len(rails) == 2 and not level.adjacent(*rails):
            raise LevelError(f"{lid}: {what} joins rails {rails[0]} and {rails[1]}, which are not neighbours")
        if not rails or len(set(rails)) != len(rails):
            raise LevelError(f"{lid}: {what} must list distinct rails")
        for r in rails:
            if (col, r) in cells:
                raise LevelError(f"{lid}: {what} overlaps {cells[(col, r)]} at column {col}, rail {r}")
            cells[(col, r)] = what

    for s in level.slots:
        claim(s.col, s.rails, f"build cells {s.col}/{'-'.join(s.rails)}")
    for e in level.fixed:
        if len(e.rails) != ELEMENT_SPAN[e.type]:
            raise LevelError(f"{lid}: fixed {e.type} needs {ELEMENT_SPAN[e.type]} rail(s)")
        claim(e.col, e.rails, f"fixed {e.type} {e.col}/{'-'.join(e.rails)}", is_element=True)
        _pair_rule(level, e)
    for st in level.stations:
        claim(st.col, (st.rail,), f"station '{st.id}'")


def _pair_rule(level: Level, el: Element) -> None:
    """Trains that leave together must never share a rail: points and crossovers stay inside one train's
    rails; an interlock is the only element that joins rails of two different trains."""
    if level.dispatch != "together" or len(el.rails) != 2:
        return
    a, b = (level.owner(r) for r in el.rails)
    where = f"{el.type} at column {el.col}, rails {'-'.join(el.rails)}"
    if el.type == "interlock":
        if a is None or b is None or a == b:
            raise LevelError(f"{level.id}: {where} must join rails of two different trains")
    elif a is None or a != b:
        raise LevelError(f"{level.id}: {where} would let trains share a rail; it must stay within one train's rails")


def _rail_ok(level: Level, rail: str, what: str) -> None:
    if rail not in level.rails:
        raise LevelError(f"{level.id}: {what} uses unknown rail '{rail}'")


# ───────────────────────── placements (the player's build) ─────────────────────────

def place(level: Level, items: list[dict] | list[Element]) -> list[Element]:
    """Check a player's placements against the level's build cells and supply. Returns Elements.

    A twist takes one build cell; points, a crossover or an interlock take two neighbouring build cells of
    the same column. Each cell holds one element. Rails are stored top to bottom."""
    lid = level.id
    cells = level.cells()
    used: dict[str, int] = {}
    taken: set[tuple[int, str]] = set()
    out: list[Element] = []
    for raw in items:
        el = raw if isinstance(raw, Element) else _element(raw, fixed=False, lid=lid)
        rails = level.ordered(el.rails)
        where = f"{el.type} at column {el.col}, rails {'-'.join(rails)}"
        for r in rails:
            _rail_ok(level, r, where)
        if len(rails) != ELEMENT_SPAN[el.type] or len(set(rails)) != len(rails):
            raise LevelError(f"{lid}: {where} must cover {ELEMENT_SPAN[el.type]} rail(s)")
        if len(rails) == 2 and not level.adjacent(*rails):
            raise LevelError(f"{lid}: {where} joins rails that are not neighbours")
        for r in rails:
            if (el.col, r) not in cells:
                raise LevelError(f"{lid}: {where} is not on build cells (column {el.col}, rail {r})")
            if (el.col, r) in taken:
                raise LevelError(f"{lid}: {where} lands on a cell that is already used (column {el.col}, rail {r})")
        if el.type not in level.supply:
            raise LevelError(f"{lid}: {el.type} is not available in this level")
        used[el.type] = used.get(el.type, 0) + 1
        cap = level.supply[el.type]
        if cap is not None and used[el.type] > cap:
            raise LevelError(f"{lid}: only {cap} × {el.type} available")
        taken.update((el.col, r) for r in rails)
        placed = Element(el.type, el.col, rails, steps=el.steps, stay=el.stay, fixed=False)
        _pair_rule(level, placed)
        out.append(placed)
    return out


def fmt_phase(steps: int) -> str:
    return ["0", "π/4", "π/2", "3π/4", "π", "5π/4", "3π/2", "7π/4"][steps % TWIST_STEPS]
