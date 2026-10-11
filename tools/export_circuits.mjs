// Used by tests/test_js_parity.py: run the browser engine on a list of cases and print what it builds.
//   node tools/export_circuits.mjs cases.json
import { readFileSync } from 'node:fs';
import { parseLevel, layout, buildCircuit, toQiskitPython, circuitOutcomes, trackOutcomes, idealRun } from '../prototype/src/engine.mjs';

const cases = JSON.parse(readFileSync(process.argv[2], 'utf8'));
const out = cases.map(c => {
  const L = parseLevel(c.level);
  const els = layout(L, c.placements);
  const ideal = idealRun(L, els);
  return L.groups().map((group, gi) => {
    const circ = buildCircuit(L, els, group);
    return {
      case: c.name, trains: group.map(t => t.id),
      python: toQiskitPython(L, circ),
      ops: circ.ops.map(o => ({ gate: o.gate, qubits: o.qubits ?? [], params: o.params ?? [], label: o.label ?? null })),
      circuit: circuitOutcomes(L, els, group),
      track: trackOutcomes(L, els, group),
      ideal: { shots: ideal.groups[gi].shots, picked: ideal.picked, total: ideal.total, cars: ideal.cars },
    };
  });
});
process.stdout.write(JSON.stringify(out));
