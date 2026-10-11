"""Translate a Quantrain level + placements into Qiskit circuits.

Encoding (one-hot path encoding):
  • rail k            → qubit k (rail order in the level file, top to bottom)
  • train on rail k   → qubit k = |1⟩, all other rail qubits |0⟩
  • station s         → one extra qubit; the station copies "train on my rail?" into it with a CX.
                        That is a which-path detector: it records the train and destroys interference
                        across that column, exactly like a real detector the train passes through.
  • exit              → measure every rail qubit (where the train ended up; ≠ one '1' means derailed)

Elements:
  twist  (steps k)  → P(k·π/4) on the rail's qubit              — the train's roll / phase
  points (stay %)   → XXPlusYYGate(θ, π/2) on [rail₁, rail₂]    — real beam splitter, P(stay)=cos²(θ/2)
  cross             → SWAP                                       — the two rails trade places
  interlock         → CZ on two rails of different trains        — phase π only if both trains are there

Dispatch "sequential": trains take turns, so each train gets its own circuit. Dispatch "together": all
trains share one circuit (one X per depot). A run sends the list of circuits as ONE job (IonQ accepts one
job per run). Classical bits: bit i = qubit i (rails, then stations).
"""
from __future__ import annotations

import math
from collections import defaultdict

import re

from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister
from qiskit.circuit.library import XXPlusYYGate
from qiskit.quantum_info import Statevector

from .level import Element, Level, Train

BETA = math.pi / 2          # XXPlusYYGate(θ, π/2) == RY(θ) on the single-train pair (verified, see tests)


def build_circuit(level: Level, elements: list[Element], trains: Train | list[Train], *, measure: bool = True) -> QuantumCircuit:
    trains = [trains] if isinstance(trains, Train) else list(trains)
    n_rails, n_stops = len(level.rails), len(level.stations)
    n = n_rails + n_stops
    # one named qubit per rail and per station, so the circuit diagram reads like the map
    regs = [QuantumRegister(1, _reg_name("rail", r)) for r in level.rails]
    regs += [QuantumRegister(1, _reg_name("S", s.id)) for s in level.stations]
    if measure:
        regs.append(ClassicalRegister(n, "c"))
    name = trains[0].id if len(trains) == 1 else "together"
    qc = QuantumCircuit(*regs, name=f"{level.id}:{name}")
    qc.metadata = {
        "level": level.id,
        "trains": [t.id for t in trains],
        "rails": list(level.rails),
        "stations": [s.id for s in level.stations],
    }
    q = level.rail_index
    stop_qubit = {s.id: n_rails + i for i, s in enumerate(level.stations)}

    for t in trains:
        qc.x(q(t.depot))                                        # each train leaves its depot
    qc.barrier(label="depot")

    by_col: dict[int, list] = defaultdict(list)
    for el in elements:
        by_col[el.col].append(el)
    for st in level.stations:
        by_col[st.col].append(st)

    for col in range(1, level.columns + 1):
        for item in by_col.get(col, []):
            if isinstance(item, Element):
                apply_element(qc, level, item)
            else:                                               # station
                qc.cx(q(item.rail), stop_qubit[item.id])
        qc.barrier(label=f"c{col}")

    if measure:
        qc.measure(range(n), range(n))
    return qc


def _reg_name(kind: str, ident: str) -> str:
    return f"{kind}_" + re.sub(r"[^A-Za-z0-9_]", "_", ident)


def apply_element(qc: QuantumCircuit, level: Level, el: Element) -> None:
    q = level.rail_index
    if el.type == "twist":
        if el.steps % 8:
            qc.p(el.phi, q(el.rails[0]))
    elif el.type == "points":
        qc.append(XXPlusYYGate(el.theta, BETA), [q(el.rails[0]), q(el.rails[1])])
    elif el.type == "cross":
        qc.swap(q(el.rails[0]), q(el.rails[1]))
    elif el.type == "interlock":
        qc.cz(q(el.rails[0]), q(el.rails[1]))
    else:  # pragma: no cover - level.py rejects unknown types
        raise ValueError(f"unknown element {el.type}")


def build_run(level: Level, elements: list[Element], *, measure: bool = True) -> list[QuantumCircuit]:
    """All circuits for one run, in dispatch order (one per train, or one for all). Send them as one job."""
    return [build_circuit(level, elements, g, measure=measure) for g in level.groups()]


# ───────────────────────── reading results ─────────────────────────

def decode(level: Level, key: str, n_trains: int = 1) -> dict:
    """Turn one measured bitstring (Qiskit order, bit 0 rightmost) into game terms.
    exit = the rail(s) the train(s) ended on, joined with '+' in rail order (e.g. 'A+D')."""
    bits = key.replace(" ", "")[::-1]
    n_rails = len(level.rails)
    on = [level.rails[i] for i in range(n_rails) if bits[i] == "1"]
    stops = [s.id for i, s in enumerate(level.stations) if bits[n_rails + i] == "1"]
    stops.sort(key=lambda sid: next(s.col for s in level.stations if s.id == sid))
    ok = len(on) == n_trains
    return {"exit": "+".join(on) if ok else None, "valid": ok, "stops": stops}


def outcome_key(d: dict) -> tuple:
    return (tuple(d["stops"]), d["exit"])


def exact_outcomes(level: Level, elements: list[Element], trains: Train | list[Train]) -> dict[tuple, float]:
    """Exact probabilities of (stations that saw a train, exit rails) from Qiskit's statevector."""
    trains = [trains] if isinstance(trains, Train) else list(trains)
    sv = Statevector(build_circuit(level, elements, trains, measure=False))
    out: dict[tuple, float] = defaultdict(float)
    for key, p in sv.probabilities_dict().items():
        if p > 1e-12:
            out[outcome_key(decode(level, key, len(trains)))] += p
    return dict(out)


def sample(level: Level, elements: list[Element], shots: int = 1000, seed: int | None = None) -> list[dict]:
    """Run every train's circuit on Qiskit's local sampler (stand-in for Qollab's backend)."""
    from qiskit.primitives import StatevectorSampler
    circuits = build_run(level, elements)
    result = StatevectorSampler(seed=seed).run(circuits, shots=shots).result()
    runs = []
    for group, pub in zip(level.groups(), result):
        counts = pub.data.c.get_counts()
        decoded: dict[tuple, int] = defaultdict(int)
        for key, c in counts.items():
            decoded[outcome_key(decode(level, key, len(group)))] += c
        runs.append({"trains": [t.id for t in group], "counts": dict(decoded)})
    return runs
