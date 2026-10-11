# Quantrain level format (`quantrain-level/1`)

A level is a **grid**: columns are time steps, rails are qubits. The level file is the single
source of truth. The 3D scene, the browser simulation and the Qiskit circuit are all built from
**level + placements** (the player's build), so they cannot disagree.

```
      depot  1  2  3  4  exit          · = build cell (two neighbouring cells of a column take a two-rail element)
   A orange  X  ·  X  S  ─▶            X = points  digit = twist steps (×π/4)  S = station
   B         X  4  X  S  ─▶            (print any level with: python -m quantrain levels/<file>.json)
```

## Fields

| Field | Meaning |
|---|---|
| `format` | always `"quantrain-level/1"` |
| `id`, `name`, `blurb` | identity and the one-line explanation shown in the game |
| `rails` | rail names, **top to bottom**. Rail *k* is qubit *k*. 1–12 rails. |
| `columns` | circuit depth: columns `1..columns`. Depot is before column 1, exit after the last. |
| `dispatch` | `"sequential"`: trains take turns, one circuit each. `"together"`: all trains leave at once, one circuit. |
| `trains` | 1–4 × `{ id, colour, depot, rails? }`. Colours must differ. `depot` is a rail. With `"together"`, every train lists the `rails` it owns (no rail owned twice). |
| `slots` | build cells: `{ col, rails: [r, …] }` makes a cell at every listed rail of that column. How the cells are grouped into entries doesn't matter. |
| `fixed` | immutable level elements, same shape as a placement |
| `stations` | `{ id, name, rail, col, passengers: [shape…], partner? }`. Any column, any rail, several per rail allowed. `partner` makes couples: passengers here only board if the partner station sees a train in the same run (both must name each other). |
| `cars` | optional: cars per run and circuit, each car one shot (default: enough to carry every passenger once). Every level must be clearable with **one** press of Run (see "Scoring"). |
| `supply` | `{ type: count }`. `null` = unlimited; a type that is missing is not available in this level. |
| `solutions` | named example builds (for tests and demos). Every one must be legal. |

Each cell `(col, rail)` holds at most one thing: a build cell, a fixed element or a station.

## Elements (placements and fixed)

| `type` | rails | params | Game meaning | Qiskit |
|---|---|---|---|---|
| `twist` | 1 | `steps` 0–7 (×π/4; each tap +1, 8 wraps to 0) | rolls the train by φ | `P(steps·π/4)` |
| `points` | 2 | `stay` 0–100, default 50 | beam splitter; % chance to stay on its own rail | `XXPlusYYGate(θ, π/2)`, `cos²(θ/2) = stay/100` |
| `cross` | 2 | — | the two rails swap places | `SWAP` |
| `interlock` | 2 | — | "together" levels only: joins rails of two different trains; phase π only when a train is on each | `CZ` |

With `"together"`, points and crossovers must stay inside one train's rails, so two trains never share a rail
(our one-qubit-per-rail encoding can't hold two trains on one rail). The interlock is the only element that
joins different trains. It isn't linear optics; real photonic chips do it with extra photons and detectors,
which succeeds only some of the time.

A placement is `{ "type", "col", "rails", ...params }`. A twist takes one empty build cell; points, a cross or an
interlock take two empty build cells on **neighbouring** rails of the same column. So two neighbouring cells hold
either two twists or one two-rail element. Rails are stored top to bottom. Placements stay within supply; fixed
elements don't use up supply.

## Stations and the exit

* A station adds one qubit. When the train passes, the station copies "train on my rail?" into that
  qubit (a CX). It is a real detector: it records the train **and** destroys interference across that
  column, so a station halfway along a line changes the physics downstream (tested).
* The exit measures every rail qubit. Exactly one `1` = where the train ended; anything else = a
  derailment (only noise can cause it).
* Qubits per circuit = rails + stations (10 rails + 8 stations = 18).

## Reading results

Classical bit *i* = qubit *i*: rails first (in `rails` order), then stations (in `stations` order).
`quantrain.decode(level, bitstring, n_trains)` returns `{ exit, valid, stops }`: `exit` is the rail (or rails,
joined with `+` in rail order, e.g. `A+D`) the trains ended on, and `stops` lists the stations that saw a train,
in column order.

## Scoring: the ideal run

One press of Run sends, for every circuit, a train of `cars` cars; each car is one shot. In the **ideal run** the
cars are spread over the outcomes exactly in proportion to their probabilities (largest-remainder rounding,
interleaved A B A B), so the result depends only on the build. Each car picks up one passenger at every station
that sees it; couples board only if the partner station sees the same car. Stars: 3 = every passenger picked up
(level cleared), 2 = at least two thirds, 1 = at least one third. `quantrain.ideal_run` and the browser's
`idealRun` implement the same rule (checked by `tests/test_js_parity.py`); `tests/test_engine.py` checks that
every level's best example build clears it in one run.

Real shots (the "Run 1000 shots" button under the hood: the browser's sampler, or on Qollab the backend picked in
*Select QPU*, including IonQ) are shown for comparison only; they never change the score.

## Example

See `levels/04-dark-port.json`: two fixed 50:50 points with two twist slots between them. With no twist,
every train goes to B. A π twist on either rail sends every train to A.

## Make your own level

**Without code:** in the game's Playground, build a map, press **✎ Make a puzzle**, clear it with ★★★ and share the
code (see "Share codes" below).

**As a level file** (it becomes part of the campaign):

1. Copy a level that is close to your idea, e.g. `levels/04-dark-port.json` → `levels/16-my-level.json`, and change
   `id` (the file name without `.json`), `name` and `blurb`.
2. Edit `rails`, `columns`, `fixed`, `slots`, `stations` and `supply`. Keep each cell to one thing.
3. Add at least one build under `solutions`, e.g. `"solve": [{ "type": "twist", "col": 2, "rails": ["B"], "steps": 4 }]`.
4. Check it: `python -m quantrain levels/16-my-level.json --solution solve` prints the grid, the circuit and the
   probabilities. Mistakes in the file are reported with the level id and the problem.
5. Add the stars each solution should get to `expect` in `tests/test_engine.py`
   (`test_ideal_run_clears_levels_in_one_run`), then run `python tests/test_engine.py` and
   `python tests/test_js_parity.py`.
6. `python tools/build_prototype.py` puts the level into the game, ordered by file name.

## Share codes (community puzzles)

A shared puzzle is a level in compact form: a JSON array, compressed with deflate and written in URL-safe base64
behind the prefix `q1.` (or `q1j.` when the browser can't compress). A link carries it after `#p=`, a part of the
URL that browsers never send to a server.

```
[1, name, description, tracks, columns, together (0|1),
 trains   [[colour slot 0–3, depot track index], …],
 stations [[col, track index, passengers 0–4, partner index or -1], …],
 fixed    [[type code, col, top track index, steps (twist) | stay (points)], …],   type codes: twist 0, points 1, cross 2, interlock 3
 pads     [bitmask of the player's build cells, one number per column],
 supply   [twist, points, cross, interlock],                                         -1 = unlimited, 0 = none
 cars]                                                                               0 = automatic
```

Limits: 8 tracks, 10 columns, 20 qubits, 4 trains, 4 passengers per station, a name of 40 characters and a
description of 280. `decodePuzzle` in `prototype/src/engine.mjs` turns a code back into an ordinary level file and
runs the same validator as for the campaign levels, so a damaged or hand-edited code is rejected, never half-loaded.
