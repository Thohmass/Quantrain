// Used by tests/test_js_parity.py: random community puzzles, sent through the share code and back.
//   node tools/export_puzzles.mjs [count]
// Prints [{ name, code, level, placements }]: the level file the code opens to and a legal random build on it.
import { LIMITS, SPAN, TYPE_CODES, encodePuzzle, decodePuzzle, puzzleToLevelData, parseLevel, layout, spots } from '../prototype/src/engine.mjs';

let seed = 7;
const rnd = () => ((seed = Math.imul(seed ^ (seed >>> 15), 0x2c1b3c6d) + 0x6d2b79f5 | 0) >>> 0) / 2 ** 32;
const pick = n => Math.floor(rnd() * n);

function randomPuzzle(i) {
  const nR = 2 + pick(4), nC = 2 + pick(5), together = rnd() < 0.4 ? 1 : 0;
  const rails = [...Array(nR).keys()].sort(() => rnd() - 0.5).slice(0, 1 + pick(Math.min(nR, LIMITS.maxTrains)));
  const slots = [0, 1, 2, 3].sort(() => rnd() - 0.5);
  const trains = rails.map((r, k) => [slots[k], r]);
  const taken = new Set(), stations = [];
  for (let s = 0; s < 1 + pick(4); s++) {
    const col = 1 + pick(nC), r = pick(nR), key = `${col}/${r}`;
    if (taken.has(key)) continue;
    taken.add(key);
    stations.push([col, r, pick(LIMITS.maxPassengers + 1), -1]);
  }
  if (stations.length >= 2 && rnd() < 0.5) { stations[0][3] = 1; stations[1][3] = 0; }
  const fixed = [];
  for (let f = 0; f < pick(nR * nC); f++) {
    const code = pick(together && trains.length > 1 ? 4 : 3), type = TYPE_CODES[code], col = 1 + pick(nC), top = pick(nR - SPAN[type] + 1);
    const cells = Array.from({ length: SPAN[type] }, (_, k) => `${col}/${top + k}`);
    if (cells.some(c => taken.has(c))) continue;
    const el = [code, col, top, ...(type === 'twist' ? [pick(8)] : type === 'points' ? [pick(101)] : [])];
    const P = [1, '', '', nR, nC, together, trains, stations, [...fixed, el], Array(nC).fill(0), [-1, -1, -1, -1], 0];
    try { puzzleToLevelData(P); } catch { continue; }              // breaks the shared-rail rule: skip it
    cells.forEach(c => taken.add(c)); fixed.push(el);
  }
  const cells = Array.from({ length: nC }, (_, c) => {
    let m = 0;
    for (let r = 0; r < nR; r++) if (!taken.has(`${c + 1}/${r}`) && rnd() < 0.7) m |= 1 << r;
    return m;
  });
  const supply = [0, 1, 2, 3].map(() => [-1, 0, 1, 2, 3][pick(5)]);
  return [1, `Puzzle ${i}`, rnd() < 0.5 ? '' : `Random puzzle number ${i}, “quoted” & <odd> text.`, nR, nC, together, trains, stations, fixed, cells, supply, rnd() < 0.3 ? 1 + pick(8) : 0];
}

function randomBuild(L) {
  const out = [], used = new Set();
  for (let tries = 0; tries < 30; tries++) {
    const types = TYPE_CODES.filter(t => t in L.supply);
    if (!types.length) break;
    const type = types[pick(types.length)], options = spots(L, type).filter(sp => sp.rails.every(r => !used.has(`${sp.col}/${r}`)));
    if (!options.length) continue;
    const sp = options[pick(options.length)], p = { type, col: sp.col, rails: sp.rails };
    if (type === 'twist') p.steps = pick(8);
    if (type === 'points') p.stay = pick(101);
    try { layout(L, [...out, p]); } catch { continue; }           // over the supply
    out.push(p); sp.rails.forEach(r => used.add(`${sp.col}/${r}`));
  }
  return out;
}

const count = +(process.argv[2] ?? 40), out = [];
for (let i = 0; out.length < count && i < count * 20; i++) {
  const P = randomPuzzle(i);
  let data;
  try { data = puzzleToLevelData(P); } catch { continue; }
  const code = await encodePuzzle(P);
  const back = await decodePuzzle(`https://example.org/quantrain/#p=${code}`);
  if (JSON.stringify(back.puzzle) !== JSON.stringify(P) || JSON.stringify(back.data) !== JSON.stringify(data)) throw new Error(`round trip changed puzzle ${i}`);
  out.push({ name: `puzzle-${i}`, code, level: data, placements: randomBuild(parseLevel(data)) });
}
if (out.length < count) throw new Error(`only ${out.length} puzzles`);
process.stdout.write(JSON.stringify(out));
