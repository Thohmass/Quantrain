// Quantrain engine — plain JavaScript, no rendering.
// Mirrors the Python package quantrain/: the level format, the Qiskit translation and the track physics.
// Used by the browser game (inlined by tools/build_prototype.py) and by tests/test_js_parity.py (via Node).

export const FORMAT = 'quantrain-level/1';
export const TWIST_STEPS = 8;                        // twists turn in steps of π/4; 8 steps = 2π = 0
export const SPAN = { twist: 1, points: 2, cross: 2, interlock: 2 };
const PI = Math.PI;

export class LevelError extends Error {}

// ───────────────────────── level format ─────────────────────────

function element(d, fixed, lid) {
  if (!(d.type in SPAN)) throw new LevelError(`${lid}: unknown element type '${d.type}'`);
  const steps = d.steps ?? 0, stay = d.stay ?? 50;
  if (d.type === 'twist' && !(Number.isInteger(steps) && steps >= 0 && steps < TWIST_STEPS)) throw new LevelError(`${lid}: twist steps must be 0..7`);
  if (d.type === 'points' && !(stay >= 0 && stay <= 100)) throw new LevelError(`${lid}: points 'stay' must be 0..100`);
  return { type: d.type, col: +d.col, rails: [...d.rails], steps, stay, fixed };
}
export const phiOf = el => (el.steps % TWIST_STEPS) * PI / 4;
export const thetaOf = el => 2 * Math.acos(Math.sqrt(el.stay / 100));

export function parseLevel(data) {
  if (data.format !== FORMAT) throw new LevelError(`expected format '${FORMAT}'`);
  const lid = data.id ?? '?';
  const L = {
    id: lid, name: data.name ?? lid, blurb: data.blurb ?? '',
    rails: [...data.rails], columns: +data.columns, dispatch: data.dispatch ?? 'sequential',
    trains: data.trains.map(t => ({ id: t.id, colour: t.colour ?? '#f2683a', depot: t.depot, rails: [...(t.rails ?? [])] })),
    slots: (data.slots ?? []).map(s => ({ col: +s.col, rails: [...s.rails] })),
    fixed: (data.fixed ?? []).map(e => element(e, true, lid)),
    stations: (data.stations ?? []).map(s => ({ id: s.id, name: s.name ?? s.id, rail: s.rail, col: +s.col, passengers: [...(s.passengers ?? [])], partner: s.partner ?? null })),
    supply: { ...(data.supply ?? {}) },
    solutions: { ...(data.solutions ?? {}) },
    cars: data.cars ?? null,
    source: data,                                  // the level file as given (sent to Python on Qollab)
  };
  L.railIndex = r => L.rails.indexOf(r);
  L.owner = r => L.trains.find(t => t.rails.includes(r)) ?? null;
  L.groups = () => (L.dispatch === 'together' ? [[...L.trains]] : L.trains.map(t => [t]));
  validate(L);
  return L;
}

function validate(L) {
  const lid = L.id, cells = new Map();
  if (L.rails.length < 1 || L.rails.length > 12) throw new LevelError(`${lid}: needs 1..12 rails`);
  if (!['sequential', 'together'].includes(L.dispatch)) throw new LevelError(`${lid}: dispatch '${L.dispatch}' not supported`);
  if (L.trains.length < 1 || L.trains.length > 4) throw new LevelError(`${lid}: needs 1..4 trains`);
  if (L.cars !== null && !(Number.isInteger(L.cars) && L.cars >= 1 && L.cars <= 64)) throw new LevelError(`${lid}: 'cars' must be a whole number 1..64`);
  for (const s of L.stations) {
    const p = s.partner && L.stations.find(o => o.id === s.partner);
    if (s.partner && (!p || p.partner !== s.id)) throw new LevelError(`${lid}: station '${s.id}' and its partner must name each other`);
  }
  if (L.dispatch === 'together') {
    const owned = L.trains.flatMap(t => t.rails);
    if (L.trains.some(t => !t.rails.length || !t.rails.includes(t.depot))) throw new LevelError(`${lid}: every train lists its rails, including its depot`);
    if (new Set(owned).size !== owned.length) throw new LevelError(`${lid}: two trains own the same rail`);
  } else if ('interlock' in L.supply || L.fixed.some(e => e.type === 'interlock')) {
    throw new LevelError(`${lid}: interlocks need trains that leave together`);
  }
  const claim = (col, rails, what, isElement = false) => {
    if (col < 1 || col > L.columns) throw new LevelError(`${lid}: ${what} outside columns 1..${L.columns}`);
    for (const r of rails) if (L.railIndex(r) < 0) throw new LevelError(`${lid}: ${what} uses unknown rail '${r}'`);
    if (!rails.length || new Set(rails).size !== rails.length) throw new LevelError(`${lid}: ${what} must list distinct rails`);
    if (isElement && rails.length === 2 && Math.abs(L.railIndex(rails[0]) - L.railIndex(rails[1])) !== 1) throw new LevelError(`${lid}: ${what} joins rails that are not neighbours`);
    for (const r of rails) {
      const k = `${col}/${r}`;
      if (cells.has(k)) throw new LevelError(`${lid}: ${what} overlaps ${cells.get(k)}`);
      cells.set(k, what);
    }
  };
  L.slots.forEach(s => claim(s.col, s.rails, `build cells ${s.col}/${s.rails.join('-')}`));
  L.fixed.forEach(e => {
    if (e.rails.length !== SPAN[e.type]) throw new LevelError(`${lid}: fixed ${e.type} needs ${SPAN[e.type]} rail(s)`);
    claim(e.col, e.rails, `fixed ${e.type}`, true); pairRule(L, e);
  });
  L.stations.forEach(s => claim(s.col, [s.rail], `station '${s.id}'`));
}

// Trains that leave together never share a rail: points/crossovers stay inside one train's rails,
// an interlock is the only element joining rails of two different trains.
function pairOk(L, type, rails) {
  if (L.dispatch !== 'together' || rails.length !== 2) return true;
  const [a, b] = rails.map(L.owner);
  return type === 'interlock' ? !!(a && b && a !== b) : !!(a && a === b);
}
function pairRule(L, el) {
  if (!pairOk(L, el.type, el.rails)) {
    throw new LevelError(`${L.id}: ${el.type} at ${el.col}/${el.rails.join('-')} breaks the rule that trains never share a rail`);
  }
}

// ───────────────────────── build cells and placements ─────────────────────────
// The level's "slots" list build cells: one per (column, rail). A twist takes one cell; points, a crossover or
// an interlock take two neighbouring cells of one column. Each cell holds one element. Rails are stored top
// to bottom.

export const isCell = (L, col, rail) => L.slots.some(s => s.col === col && s.rails.includes(rail));
export const ordered = (L, rails) => [...rails].sort((a, b) => L.railIndex(a) - L.railIndex(b));

/** Every place an element of this type could go on an empty board: [{ col, rails }], rails top to bottom. */
export function spots(L, type) {
  const out = [];
  for (let col = 1; col <= L.columns; col++) {
    for (let k = 0; k < L.rails.length; k++) {
      const rails = SPAN[type] === 1 ? [L.rails[k]] : k + 1 < L.rails.length ? [L.rails[k], L.rails[k + 1]] : null;
      if (!rails || !rails.every(r => isCell(L, col, r))) continue;
      if (pairOk(L, type, rails)) out.push({ col, rails });
    }
  }
  return out;
}
/** Can an element of this type stand on these rails of this column (build cells, neighbours, rail sharing rule)? */
export function fits(L, type, spot) {
  const rails = ordered(L, spot.rails);
  if (rails.length !== SPAN[type] || !rails.every(r => isCell(L, spot.col, r))) return false;
  if (rails.length === 2 && Math.abs(L.railIndex(rails[0]) - L.railIndex(rails[1])) !== 1) return false;
  return pairOk(L, type, rails);
}

/** Fixed elements + validated player placements, in column order (same order as the Python translator). */
export function layout(L, placements) {
  const used = {}, taken = new Set(), placed = [];
  for (const raw of placements) {
    const el = element(raw, false, L.id);
    const rails = ordered(L, el.rails);
    const where = `${el.type} at ${el.col}/${rails.join('-')}`;
    if (rails.some(r => L.railIndex(r) < 0)) throw new LevelError(`${L.id}: ${where} uses an unknown rail`);
    if (rails.length !== SPAN[el.type] || new Set(rails).size !== rails.length) throw new LevelError(`${L.id}: ${where} must cover ${SPAN[el.type]} rail(s)`);
    if (rails.length === 2 && Math.abs(L.railIndex(rails[0]) - L.railIndex(rails[1])) !== 1) throw new LevelError(`${L.id}: ${where} joins rails that are not neighbours`);
    for (const r of rails) {
      if (!isCell(L, el.col, r)) throw new LevelError(`${L.id}: ${where} is not on build cells`);
      if (taken.has(`${el.col}/${r}`)) throw new LevelError(`${L.id}: ${where} lands on a cell that is already used`);
    }
    if (!(el.type in L.supply)) throw new LevelError(`${L.id}: ${el.type} is not available here`);
    used[el.type] = (used[el.type] ?? 0) + 1;
    const cap = L.supply[el.type];
    if (cap !== null && used[el.type] > cap) throw new LevelError(`${L.id}: only ${cap} × ${el.type} available`);
    for (const r of rails) taken.add(`${el.col}/${r}`);
    const done = { ...el, rails };
    pairRule(L, done);
    placed.push(done);
  }
  return [...L.fixed, ...placed].map((e, i) => [e, i]).sort((a, b) => a[0].col - b[0].col || a[1] - b[1]).map(p => p[0]);
}

// ───────────────────────── Qiskit translation ─────────────────────────

const regName = (kind, id) => `${kind}_` + String(id).replace(/[^A-Za-z0-9_]/g, '_');

/** The circuit as a list of ops, gate for gate what quantrain/circuit.py builds. */
export function buildCircuit(L, els, trains, { measure = true } = {}) {
  trains = Array.isArray(trains) ? trains : [trains];
  const nR = L.rails.length, nS = L.stations.length;
  const q = r => L.railIndex(r);
  const qubits = [...L.rails.map(r => regName('rail', r)), ...L.stations.map(s => regName('S', s.id))];
  const ops = trains.map(t => ({ gate: 'x', qubits: [q(t.depot)], params: [], src: { kind: 'depot', train: t.id } }));
  ops.push({ gate: 'barrier', label: 'depot' });
  for (let col = 1; col <= L.columns; col++) {
    for (const el of els) {
      if (el.col !== col) continue;
      if (el.type === 'twist') {
        if (el.steps % TWIST_STEPS) ops.push({ gate: 'p', qubits: [q(el.rails[0])], params: [phiOf(el)], src: { kind: 'twist', el } });
      } else if (el.type === 'points') {
        ops.push({ gate: 'xx_plus_yy', qubits: [q(el.rails[0]), q(el.rails[1])], params: [thetaOf(el), PI / 2], src: { kind: 'points', el } });
      } else if (el.type === 'cross') {
        ops.push({ gate: 'swap', qubits: [q(el.rails[0]), q(el.rails[1])], params: [], src: { kind: 'cross', el } });
      } else if (el.type === 'interlock') {
        ops.push({ gate: 'cz', qubits: [q(el.rails[0]), q(el.rails[1])], params: [], src: { kind: 'interlock', el } });
      }
    }
    L.stations.forEach((st, i) => {
      if (st.col === col) ops.push({ gate: 'cx', qubits: [q(st.rail), nR + i], params: [], src: { kind: 'station', st } });
    });
    ops.push({ gate: 'barrier', label: `c${col}` });
  }
  if (measure) ops.push({ gate: 'measure', qubits: qubits.map((_, i) => i), params: [] });
  return { name: `${L.id}:${trains.length === 1 ? trains[0].id : 'together'}`, qubits, nRails: nR, nStations: nS, nTrains: trains.length, ops };
}

/** Python source that rebuilds exactly this circuit in Qiskit. */
export function toQiskitPython(L, circ) {
  const n = circ.qubits.length;
  const ang = x => {
    for (const [num, den] of [[0, 1], [1, 4], [1, 2], [3, 4], [1, 1], [5, 4], [3, 2], [7, 4], [2, 1]]) {
      if (Math.abs(x - PI * num / den) < 1e-12) {
        if (num === 0) return '0';
        const top = num === 1 ? 'pi' : `${num}*pi`;
        return den === 1 ? top : `${top}/${den}`;
      }
    }
    return x.toPrecision(17);
  };
  const lines = [
    'from math import pi',
    'from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister',
    'from qiskit.circuit.library import XXPlusYYGate',
    '',
    `# Quantrain · ${circ.name} — one qubit per rail, one per station`,
    `regs = [${circ.qubits.map(name => `QuantumRegister(1, "${name}")`).join(', ')}]`,
    `qc = QuantumCircuit(*regs, ClassicalRegister(${n}, "c"), name="${circ.name}")`,
  ];
  for (const op of circ.ops) {
    const [a, b] = op.qubits ?? [];
    if (op.gate === 'x') lines.push(`qc.x(${a})`);
    else if (op.gate === 'p') lines.push(`qc.p(${ang(op.params[0])}, ${a})`);
    else if (op.gate === 'xx_plus_yy') lines.push(`qc.append(XXPlusYYGate(${ang(op.params[0])}, ${ang(op.params[1])}), [${a}, ${b}])`);
    else if (op.gate === 'swap') lines.push(`qc.swap(${a}, ${b})`);
    else if (op.gate === 'cz') lines.push(`qc.cz(${a}, ${b})`);
    else if (op.gate === 'cx') lines.push(`qc.cx(${a}, ${b})`);
    else if (op.gate === 'barrier') lines.push(`qc.barrier(label="${op.label}")`);
    else if (op.gate === 'measure') lines.push(`qc.measure(range(${n}), range(${n}))`);
  }
  return lines.join('\n') + '\n';
}

// ───────────────────────── statevector simulation of the circuit ─────────────────────────

export function simulate(circ) {
  const n = circ.qubits.length, size = 1 << n;
  const re = new Float64Array(size), im = new Float64Array(size);
  re[0] = 1;
  const swapAmp = (i, j) => { [re[i], re[j]] = [re[j], re[i]]; [im[i], im[j]] = [im[j], im[i]]; };
  for (const op of circ.ops) {
    const [a, b] = op.qubits ?? [];
    const ma = 1 << a, mb = 1 << b;
    if (op.gate === 'x') { for (let i = 0; i < size; i++) if (!(i & ma)) swapAmp(i, i | ma); }
    else if (op.gate === 'p') {
      const c = Math.cos(op.params[0]), s = Math.sin(op.params[0]);
      for (let i = 0; i < size; i++) if (i & ma) { const r = re[i], m = im[i]; re[i] = r * c - m * s; im[i] = r * s + m * c; }
    } else if (op.gate === 'swap') { for (let i = 0; i < size; i++) if ((i & ma) && !(i & mb)) swapAmp(i, (i ^ ma) | mb); }
    else if (op.gate === 'cx') { for (let i = 0; i < size; i++) if ((i & ma) && !(i & mb)) swapAmp(i, i | mb); }
    else if (op.gate === 'cz') { for (let i = 0; i < size; i++) if ((i & ma) && (i & mb)) { re[i] = -re[i]; im[i] = -im[i]; } }
    else if (op.gate === 'xx_plus_yy') {
      // Qiskit XXPlusYYGate(θ, β) on [a, b]: |a=1,b=0⟩ ↔ |a=0,b=1⟩ block
      // [[c, -i s e^{-iβ}], [-i s e^{iβ}, c]]
      const [theta, beta] = op.params, c = Math.cos(theta / 2), s = Math.sin(theta / 2);
      const u = [-s * Math.sin(beta), -s * Math.cos(beta)];   // -i s e^{-iβ}
      const w = [s * Math.sin(beta), -s * Math.cos(beta)];    // -i s e^{iβ}
      for (let i = 0; i < size; i++) {
        if (!((i & ma) && !(i & mb))) continue;
        const j = (i ^ ma) | mb;
        const [ir, ii, jr, ji] = [re[i], im[i], re[j], im[j]];
        re[i] = c * ir + (u[0] * jr - u[1] * ji); im[i] = c * ii + (u[0] * ji + u[1] * jr);
        re[j] = (w[0] * ir - w[1] * ii) + c * jr; im[j] = (w[0] * ii + w[1] * ir) + c * ji;
      }
    }
  }
  const probs = {};
  for (let i = 0; i < size; i++) {
    const p = re[i] * re[i] + im[i] * im[i];
    if (p > 1e-12) probs[i.toString(2).padStart(n, '0')] = p;
  }
  return probs;
}

/** One measured bitstring (Qiskit order, qubit 0 rightmost) in game terms. */
export function decode(L, key, nTrains = 1) {
  const bits = key.replace(/ /g, '').split('').reverse();
  const nR = L.rails.length;
  const on = L.rails.filter((_, i) => bits[i] === '1');
  const stops = L.stations.filter((_, i) => bits[nR + i] === '1').sort((x, y) => x.col - y.col).map(s => s.id);
  const ok = on.length === nTrains;
  return { exit: ok ? on.join('+') : null, valid: ok, stops };
}
export const outcomeKey = d => `${d.stops.join(',')}|${d.exit ?? 'derail'}`;

export function circuitOutcomes(L, els, trains) {
  trains = Array.isArray(trains) ? trains : [trains];
  const out = {};
  for (const [key, p] of Object.entries(simulate(buildCircuit(L, els, trains, { measure: false })))) {
    const k = outcomeKey(decode(L, key, trains.length));
    out[k] = (out[k] ?? 0) + p;
  }
  return out;
}

// ───────────────────────── track physics (what the game animates) ─────────────────────────
// The state is a Map: configuration → complex amplitude [re, im]. A configuration lists the rail index of
// each train in the group ("0,3"); with one train it is just one amplitude per rail. applyJoint applies the
// part of an element between progress p0 and p1 (0..1), so the animation can show it happening gradually.

export const abs2 = c => c[0] * c[0] + c[1] * c[1];
export const cfgOf = key => key.split(',').map(Number);
const rot = (c, ang) => { const co = Math.cos(ang), si = Math.sin(ang); return [c[0] * co - c[1] * si, c[0] * si + c[1] * co]; };

export function initialState(L, trains) {
  return new Map([[trains.map(t => L.railIndex(t.depot)).join(','), [1, 0]]]);
}

export function applyJoint(S, L, el, p0, p1) {
  const q = r => L.railIndex(r);
  const out = new Map();
  const add = (cfg, c) => { const k = cfg.join(','), o = out.get(k); out.set(k, o ? [o[0] + c[0], o[1] + c[1]] : c); };
  if (el.type === 'twist') {
    const k = q(el.rails[0]), ang = phiOf(el) * (p1 - p0);
    for (const [key, c] of S) out.set(key, cfgOf(key).includes(k) ? rot(c, ang) : c);
    return out;
  }
  const i = q(el.rails[0]), j = q(el.rails[1]);
  if (el.type === 'interlock') {                         // CZ, phased in gradually: e^{iπp} when trains sit on both rails
    const ang = PI * (p1 - p0);
    for (const [key, c] of S) { const cfg = cfgOf(key); out.set(key, cfg.includes(i) && cfg.includes(j) ? rot(c, ang) : c); }
    return out;
  }
  if (el.type === 'cross') {                             // a swap happens all at once, halfway along
    if ((p0 < 0.5) === (p1 < 0.5)) return new Map(S);
    for (const [key, c] of S) add(cfgOf(key).map(r => (r === i ? j : r === j ? i : r)), c);
    return out;
  }
  // points: RY(θ) on the train sitting on rail i or j — [stay, switch] = [[cs, -sn], [sn, cs]]
  const half = thetaOf(el) * (p1 - p0) / 2, cs = Math.cos(half), sn = Math.sin(half);
  for (const [key, c] of S) {
    const cfg = cfgOf(key), ti = cfg.indexOf(i), tj = cfg.indexOf(j);
    if (ti >= 0) {
      add(cfg, [cs * c[0], cs * c[1]]);
      const m = [...cfg]; m[ti] = j; add(m, [sn * c[0], sn * c[1]]);
    } else if (tj >= 0) {
      const m = [...cfg]; m[tj] = i; add(m, [-sn * c[0], -sn * c[1]]);
      add(cfg, [cs * c[0], cs * c[1]]);
    } else add(cfg, c);
  }
  return out;
}

/** Which stations of this column see a train in configuration cfg (ids in station order). */
export const seenBy = (L, stops, cfg) => stops.filter(s => cfg.includes(L.railIndex(s.rail))).map(s => s.id);

/** Probabilities of (stations that saw a train, exit rails) — same algorithm as quantrain/reference.py. */
export function trackOutcomes(L, els, trains) {
  trains = Array.isArray(trains) ? trains : [trains];
  let branches = [[[], initialState(L, trains)]];
  for (let col = 1; col <= L.columns; col++) {
    for (const el of els) if (el.col === col) branches = branches.map(([seen, S]) => [seen, applyJoint(S, L, el, 0, 1)]);
    const stops = L.stations.filter(s => s.col === col);
    if (!stops.length) continue;
    const next = [];
    for (const [seen, S] of branches) {
      const groups = new Map();
      for (const [key, c] of S) {
        const hit = seenBy(L, stops, cfgOf(key)).join(',');
        if (!groups.has(hit)) groups.set(hit, new Map());
        groups.get(hit).set(key, c);
      }
      for (const [hit, sub] of groups) {
        let p = 0; for (const c of sub.values()) p += abs2(c);
        if (p > 1e-30) next.push([[...seen, ...(hit ? hit.split(',') : [])], sub]);
      }
    }
    branches = next;
  }
  const out = {};
  for (const [seen, S] of branches) for (const [key, c] of S) {
    const p = abs2(c);
    if (p <= 1e-12) continue;
    const k = `${seen.join(',')}|${cfgOf(key).sort((a, b) => a - b).map(r => L.rails[r]).join('+')}`;
    out[k] = (out[k] ?? 0) + p;
  }
  return out;
}

// ───────────────────────── the ideal run (scoring) ─────────────────────────
// A run sends `cars` cars per circuit; every car is one shot. In the ideal run the cars are spread over the
// outcomes exactly in proportion to their probabilities (largest remainder), so the score depends only on the
// build. Each car picks up one passenger at every station that sees it; couples board only if the partner
// station sees the same car. Same algorithm as quantrain/score.py (checked by tests/test_js_parity.py).

/** Cars per circuit: the level's 'cars', or enough to carry every passenger once. */
export function carsFor(L) {
  if (L.cars) return L.cars;
  const total = L.stations.reduce((n, s) => n + s.passengers.length, 0);
  return Math.max(1, Math.ceil(total / L.groups().length));
}
/** Spread `cars` shots over the outcomes in proportion (largest remainder), interleaved evenly. */
export function idealShots(probs, cars) {
  const keys = Object.keys(probs).filter(k => probs[k] > 1e-12).sort();
  const quota = keys.map(k => probs[k] * cars);
  const n = quota.map(q => Math.floor(q + 1e-9));
  let left = cars - n.reduce((a, b) => a + b, 0);
  const rem = i => Math.round((quota[i] - n[i]) * 1e9) / 1e9;
  const order = keys.map((_, i) => i).sort((a, b) => rem(b) - rem(a) || a - b);
  for (const i of order) { if (left <= 0) break; n[i] += 1; left -= 1; }
  const cur = keys.map(() => 0), out = [];
  for (let s = 0; s < cars; s++) {                 // smooth weighted round robin: A B A B rather than A A B B
    keys.forEach((_, i) => { cur[i] += n[i]; });
    let best = 0;
    for (let i = 1; i < keys.length; i++) if (cur[i] > cur[best]) best = i;
    out.push(keys[best]);
    cur[best] -= cars;
  }
  return out;
}
export function starsFor(picked, total) {
  if (!total) return 0;
  if (picked === total) return 3;
  return picked * 3 >= total * 2 ? 2 : picked * 3 >= total ? 1 : 0;
}
/** Play the ideal run: the outcome of every car, and how many passengers they pick up. */
export function idealRun(L, els) {
  const waiting = new Map(L.stations.map(s => [s.id, s.passengers.length]));
  const cars = carsFor(L);
  const groups = L.groups().map(group => {
    const probs = trackOutcomes(L, els, group);
    const shots = idealShots(probs, cars);
    for (const key of shots) {
      const seen = new Set(key.split('|')[0].split(',').filter(Boolean));
      for (const id of seen) {
        const st = L.stations.find(s => s.id === id);
        if (st.partner && !seen.has(st.partner)) continue;
        if (waiting.get(id) > 0) waiting.set(id, waiting.get(id) - 1);
      }
    }
    return { group, probs, shots };
  });
  const total = L.stations.reduce((n, s) => n + s.passengers.length, 0);
  const picked = total - [...waiting.values()].reduce((a, b) => a + b, 0);
  return { cars, groups, picked, total, cleared: total > 0 && picked === total, stars: starsFor(picked, total) };
}

// ───────────────────────── what each ghost shows ─────────────────────────
// For every train t and rail r: the probability of finding t there, and a phase for its roll and label.
// One train: the amplitude's own phase. Several trains: individual phases aren't defined for an entangled
// state, so we use a stable convention: a ghost shows the phase of the strongest joint configuration it is
// part of (for unentangled trains that is simply the train's own relative phase), measured against a
// reference configuration that is kept from frame to frame (prevRefKey) while it still carries weight.
// Ties are broken by configuration order, never by rounding noise, so nothing flips back and forth.
export function ghostView(S, nTrains, nRails, prevRefKey = null) {
  const arg = c => Math.atan2(c[1], c[0]);
  const items = [];
  for (const [k, c] of S) { const p = abs2(c); if (p > 1e-12) items.push({ k, cfg: cfgOf(k), c, p }); }
  const order = (a, b) => (Math.abs(b.p - a.p) > 1e-6 ? b.p - a.p : a.k < b.k ? -1 : a.k > b.k ? 1 : 0);
  items.sort(order);
  const marg = Array.from({ length: nTrains }, () => new Array(nRails).fill(0));
  const phase = Array.from({ length: nTrains }, () => new Array(nRails).fill(0));
  for (const it of items) it.cfg.forEach((r, t) => { marg[t][r] += it.p; });
  if (!items.length) return { marg, phase, refKey: null };
  if (nTrains === 1) {
    for (const it of items) phase[0][it.cfg[0]] = arg(it.c);
    return { marg, phase, refKey: items[0].k };
  }
  const top = items[0].p;
  const prev = prevRefKey && S.get(prevRefKey);
  const ref = prev && abs2(prev) > 0.02 * top ? { k: prevRefKey, cfg: cfgOf(prevRefKey), c: prev } : items[0];
  const refPh = arg(ref.c);
  for (let t = 0; t < nTrains; t++) {
    for (let r = 0; r < nRails; r++) {
      if (marg[t][r] <= 1e-12) continue;
      phase[t][r] = arg(items.find(it => it.cfg[t] === r).c) - refPh;   // strongest branch this ghost is part of
    }
  }
  return { marg, phase, refKey: ref.k };
}

// ───────────────────────── shared puzzles (a whole puzzle inside a link) ─────────────────────────
// A puzzle made in the Playground travels as a compact array, compressed (deflate-raw) and written in URL-safe
// base64 after "#p=q1." in a link, or pasted as a code. It turns into an ordinary level file (puzzleToLevelData),
// so everything a level is checked for applies to it, plus the playground limits below.
//
//   [1, name, description, rails, columns, together(0/1),
//    trains   [[colour slot 0..3, depot rail index]],
//    stations [[col, rail index, passengers 0..4, partner station index or -1]],
//    fixed    [[type code, col, top rail index, steps (twist) | stay (points)]],     type codes: TYPE_CODES
//    cells    [bitmask of the rails the player may build on, one per column],
//    supply   [twist, points, cross, interlock]  (-1 = unlimited, 0 = not offered, n = n),
//    cars     (0 = automatic)]
export const LIMITS = { maxRails: 8, maxColumns: 10, maxQubits: 20, maxTrains: 4, maxPassengers: 4, name: 40, description: 280 };
export const TRAIN_KINDS = [['orange', '#f2683a'], ['teal', '#12a39b'], ['violet', '#8a5cf6'], ['blue', '#2f7de1']];
export const SHAPE_NAMES = ['bubble', 'cube', 'octahedron'];
export const TYPE_CODES = ['twist', 'points', 'cross', 'interlock'];
const PUZZLE_VERSION = 1;
const letter = k => String.fromCharCode(65 + k);

/** The puzzle array → a level file (throws LevelError when anything is off). */
export function puzzleToLevelData(P) {
  const bad = why => { throw new LevelError(`puzzle: ${why}`); };
  if (!Array.isArray(P) || P.length !== 12 || P[0] !== PUZZLE_VERSION) bad('unknown puzzle format');
  const [, name, desc, nR, nC, together, trains, stations, fixed, cells, supply, cars] = P;
  const isInt = (v, lo, hi) => Number.isInteger(v) && v >= lo && v <= hi;
  if (typeof name !== 'string' || name.length > LIMITS.name) bad('name');
  if (typeof desc !== 'string' || desc.length > LIMITS.description) bad('description');
  if (!isInt(nR, 1, LIMITS.maxRails) || !isInt(nC, 1, LIMITS.maxColumns) || !isInt(together, 0, 1)) bad('size');
  if (!Array.isArray(trains) || !trains.length || trains.length > LIMITS.maxTrains) bad('trains');
  if (!Array.isArray(stations) || nR + stations.length > LIMITS.maxQubits) bad('stations');
  if (!Array.isArray(fixed) || fixed.length > nR * nC || !Array.isArray(cells) || cells.length !== nC) bad('map');
  if (!Array.isArray(supply) || supply.length !== 4 || !supply.every(v => isInt(v, -1, 99))) bad('supply');
  if (!isInt(cars, 0, 64)) bad('cars');
  const rails = Array.from({ length: nR }, (_, k) => letter(k));
  for (const t of trains) if (!Array.isArray(t) || !isInt(t[0], 0, 3) || !isInt(t[1], 0, nR - 1)) bad('train');
  if (new Set(trains.map(t => t[0])).size !== trains.length || new Set(trains.map(t => t[1])).size !== trains.length) bad('two trains alike');
  const sorted = [...trains].sort((a, b) => a[1] - b[1]);
  const levelTrains = sorted.map(([slot, r], k) => {
    const d = { id: TRAIN_KINDS[slot][0], colour: TRAIN_KINDS[slot][1], depot: rails[r] };
    if (together) d.rails = rails.slice(k === 0 ? 0 : r, k + 1 < sorted.length ? sorted[k + 1][1] : nR);
    return d;
  });
  const sid = st => `s${st[0]}${rails[st[1]]}`;
  for (const st of stations) if (!Array.isArray(st) || !isInt(st[0], 1, nC) || !isInt(st[1], 0, nR - 1) || !isInt(st[2], 0, LIMITS.maxPassengers) || !isInt(st[3], -1, stations.length - 1)) bad('station');
  const levelStations = stations.map((st, i) => ({
    id: sid(st), name: `Stop ${rails[st[1]]}${st[0]}`, rail: rails[st[1]], col: st[0],
    passengers: Array.from({ length: st[2] }, (_, k) => SHAPE_NAMES[(i + k) % 3]),
    ...(st[3] >= 0 ? { partner: sid(stations[st[3]]) } : {}),
  }));
  const levelFixed = fixed.map(f => {
    if (!Array.isArray(f) || !isInt(f[0], 0, 3) || !isInt(f[1], 1, nC) || !isInt(f[2], 0, nR - 1)) bad('block');
    const type = TYPE_CODES[f[0]], span = SPAN[type];
    if (f[2] + span > nR) bad('block off the map');
    const el = { type, col: f[1], rails: rails.slice(f[2], f[2] + span) };
    if (type === 'twist') { if (!isInt(f[3], 0, 7)) bad('twist'); el.steps = f[3]; }
    if (type === 'points') { if (!isInt(f[3], 0, 100)) bad('points'); el.stay = f[3]; }
    return el;
  });
  const slots = [];
  cells.forEach((mask, c) => {
    if (!isInt(mask, 0, (1 << nR) - 1)) bad('cells');
    const free = rails.filter((_, k) => mask & (1 << k));
    if (free.length) slots.push({ col: c + 1, rails: free });
  });
  const levelSupply = {};
  TYPE_CODES.forEach((t, i) => { if (supply[i] !== 0) levelSupply[t] = supply[i] < 0 ? null : supply[i]; });
  if (!together || trains.length < 2) delete levelSupply.interlock;
  const data = {
    format: FORMAT, id: 'puzzle', name: name || 'Untitled puzzle', blurb: desc, rails, columns: nC,
    dispatch: together ? 'together' : 'sequential', trains: levelTrains, slots, fixed: levelFixed,
    stations: levelStations, supply: levelSupply, solutions: {}, ...(cars ? { cars } : {}),
  };
  parseLevel(data);                                // throws on overlaps, broken couples, shared rails, …
  return data;
}

const b64url = bytes => {
  let s = '';
  for (let i = 0; i < bytes.length; i += 0x8000) s += String.fromCharCode(...bytes.subarray(i, i + 0x8000));
  return btoa(s).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
};
const unb64url = text => {
  const s = atob(text.replace(/-/g, '+').replace(/_/g, '/') + '==='.slice((text.length + 3) % 4));
  return Uint8Array.from(s, ch => ch.charCodeAt(0));
};
async function pipe(bytes, stream) {
  return new Uint8Array(await new Response(new Blob([bytes]).stream().pipeThrough(stream)).arrayBuffer());
}
/** Puzzle array → "q1.…" (compressed) or "q1j.…" (plain, for browsers without CompressionStream). */
export async function encodePuzzle(P) {
  puzzleToLevelData(P);                            // never share a broken puzzle
  const bytes = new TextEncoder().encode(JSON.stringify(P));
  if (typeof CompressionStream === 'function') return 'q1.' + b64url(await pipe(bytes, new CompressionStream('deflate-raw')));
  return 'q1j.' + b64url(bytes);
}
/** A code, or any text containing "#p=<code>" (a whole link) → { puzzle, level data }. Throws LevelError if damaged. */
export async function decodePuzzle(text) {
  const m = String(text).trim().match(/(?:#p=)?(q1j?)\.([A-Za-z0-9_-]{4,8000})\s*$/);
  if (!m) throw new LevelError('puzzle: this is not a puzzle code');
  let bytes;
  try {
    bytes = unb64url(m[2]);
    if (m[1] === 'q1') bytes = await pipe(bytes, new DecompressionStream('deflate-raw'));
  } catch { throw new LevelError('puzzle: the code is damaged'); }
  if (bytes.length > 20000) throw new LevelError('puzzle: too big');
  let P;
  try { P = JSON.parse(new TextDecoder().decode(bytes)); } catch { throw new LevelError('puzzle: the code is damaged'); }
  return { puzzle: P, data: puzzleToLevelData(P) };
}
