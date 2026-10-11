"""Bridge between the browser game and the quantum backend Qollab hands to a project.

On Qollab (JS / Qiskit project), main.js calls

    run_shots(backend, level_json, placements_json, shots)

with the backend the player picked in the "Select QPU" dialog. It builds every circuit of the run with the
same translator the tests check (quantrain.build_run), rewrites the beam splitter into gates every backend
accepts, sends all circuits as ONE job (IonQ backends allow one job per run), and returns the counts decoded
into game outcomes ("stations that saw a train|exit rails", or "|derail" when noise put the trains on an
impossible set of rails), one dict per circuit, as JSON.
"""
from __future__ import annotations

import json
from collections import defaultdict

from qiskit import transpile
from qiskit.transpiler.passes import RemoveBarriers

from .circuit import build_run, decode, outcome_key
from .level import load_level
from .score import outcome_str

# gates the IonQ provider and the local simulators all accept (XXPlusYYGate is not one of them)
BASIS = ["x", "h", "ry", "rz", "p", "cx", "cz", "swap", "measure"]


def prepare(level, elements) -> list:
    """The run's circuits, barriers removed and rewritten into BASIS. Same probabilities (tested)."""
    circuits = [RemoveBarriers()(qc) for qc in build_run(level, elements)]
    return transpile(circuits, basis_gates=BASIS, optimization_level=1, seed_transpiler=7)


def backend_name(backend) -> str:
    name = getattr(backend, "name", None)
    name = name() if callable(name) else name
    return str(name or type(backend).__name__)


def run_shots(backend, level_json: str, placements_json: str, shots: int = 1000) -> str:
    level = load_level(json.loads(level_json))
    elements = level.layout(json.loads(placements_json))
    circuits = prepare(level, elements)
    job = backend.run(circuits, shots=int(shots))          # one job for every circuit of the run
    result = job.result()
    groups = []
    for i, group in enumerate(level.groups()):
        counts = result.get_counts(i) if len(circuits) > 1 else result.get_counts()
        decoded: dict[str, int] = defaultdict(int)
        width = circuits[i].num_clbits
        for key, n in counts.items():
            key = str(key)
            if key.startswith("0x"):                    # some providers report hex keys
                key = format(int(key, 16), f"0{width}b")
            decoded[outcome_str(outcome_key(decode(level, key, len(group))))] += int(n)
        groups.append(dict(decoded))
    return json.dumps({"backend": backend_name(backend), "shots": int(shots), "groups": groups})
