# Quantrain — plan and decisions

> **Working log, kept for the record.** Decisions, work order and wishlist as they were made during the build weekend (10–11 Oct 2026). The game as built is described in [`../HOW_IT_WORKS.md`](../HOW_IT_WORKS.md).

*Last updated 11 Oct 2026, 21:00 CEST. Hackathon deadline: **Sun 19:00 ET = Mon 01:00 CEST**.*

## Decisions so far

* **Single source of truth.** Level file + placements → 3D scene, browser simulation and Qiskit circuit.
  Drag and drop only edits the placements. Format: `docs/LEVEL_FORMAT.md`.
* **Grid.** Columns = time steps (fixed circuit depth per level), rails = qubits, up to 10–12 rails.
  Each level has a fixed map of build cells. A two-rail element takes two **neighbouring** cells of a column.
  Long-range routing uses crossovers.
* **Elements (palette).**
  * Twist: tap to cycle +π/4, wrapping at 2π.
  * Points (50:50 beam splitter; other ratios possible per level).
  * Cross (swap).
  * Immutable: depot, stations, exit, level-specific fixed elements.
* **Supply.** Unlimited by default. A level can limit a type. A depleted block dims. Discarding a placed
  element returns it to the supply. Dropping onto an occupied slot replaces the element.
* **Stations.** Which-path detectors (CX into one extra qubit). Any column, several per rail allowed.
  A mid-line station destroys interference downstream, which is real physics and a useful puzzle tool.
* **Trains.** Up to 4, different colours, **sequential dispatch**: trains take turns and never share the
  network at the same time. Each train is its own circuit, and a run sends them all as one job.
  * Why: one qubit per rail can't hold two photons on one rail, so two trains meeting at points would
    behave wrongly (real photons bunch; the Hong–Ou–Mandel effect).
  * Simultaneous trains need either a validator that keeps them apart or a bigger encoding. That's a
    later feature, together with interlocks (entangling gates).
* **Phase display.** Roll of the train + label in π units. Dial = ring with an arc and a fill that
  deplete as the needle turns with the train.
* **Qiskit conventions (tested).**
  * Points = `XXPlusYYGate(θ, π/2)`, which equals `RY(θ)` on the single-train pair.
  * Twist = `P(φ)`.
  * Cross = `SWAP`.

## Answers from 11 Oct (Tomáš)

* **Pickups:** one passenger per station that sees the train (one per measurement).
* **Several trains:** every run dispatches all trains, one after another.
* **Score:** efficiency = passengers / runs, compared with the level's optimal build (stars later).
* **Closed / forbidden stations:** an option for some levels later; not implemented yet.
* **Other split ratios:** no extra blocks. Points + twist + points (a Mach–Zehnder interferometer) gives
  any ratio, as on real photonic chips. The palette has 50:50 points only; `stay` stays in the format for
  fixed elements.

## Work order

1. [x] Level format + Qiskit translator + reference simulator + tests (`quantrain/`, `levels/`, `tests/`)
2. [x] Tomáš verified step 1
3. [x] **"Under the hood" overlay** (`prototype/`):
   * the browser runs on the same level files;
   * `prototype/src/engine.mjs` mirrors the translator gate for gate;
   * the overlay shows the circuit (columns c1… match the map), a live check (circuit statevector vs
     train physics) and the Qiskit code;
   * `tests/test_js_parity.py` runs the shown code in Qiskit and compares it instruction by instruction.
4. [x] Visual pass after review:
   * depot square on the rail;
   * ghosts merge back along the crossover when they interfere;
   * rails 3.6 apart;
   * platforms at rail level on pillars, right next to the rail, with the house and tree on them;
   * crosshair phase dial with a tick for every π/4;
   * circuit panel always at the bottom.
5. [x] Crosshair as one rotating lens (needle + a dot for every π/4); faster trains (speed 3.4, dwell 1.1 s).
6. [x] **Entanglement — level 4 "Entangled couples"**:
   * `dispatch: "together"`: trains leave at once, each owning its rails, in one circuit.
   * `interlock` element = CZ between neighbouring rails of two trains (shown as a gantry).
   * Station `partner`: couples only board if both stations see a train in the same run.
   * Joint-state physics in Python and JS (configuration → amplitude); tethers link the ghosts of each joint
     configuration, with the relative phase on the tether.
   * Without the interlock the couples meet in half the runs; with it in every run (Bell pair A+D / B+C).
7. [x] Visual pass:
   * component labels only on hover / press-and-hold;
   * interlock drawn as a chain with a big dot on each rail;
   * chain icon on entangled trains' labels and chain lines between the labels of configurations that only
     exist together (relative phase on the line);
   * small triangles on each platform edge pointing at its rail;
   * couples in a shared colour (pink first).
   * Fix: entangled trains' phases no longer jump between the paired trains.
     * The old display measured every phase against "the strongest configuration", and during the interlock
       four configurations tie, so rounding noise kept picking a different one (8 jumps of π per run).
     * Now each ghost shows the phase of the strongest branch it belongs to, against a reference kept from
       frame to frame, with ties broken by a fixed order (`ghostView` in engine.mjs).
     * The single remaining change (teal's C ghost joining the π branch when its last points start) is
       shown as a quick roll.
     * Phases stay continuous through measurements.
   * [x] Tomáš verified
8. [x] **Drag and drop** (decided 11 Oct):
   * Palette above Run with only this level's blocks; count badge (∞ when unlimited), dims at 0.
   * Any block fits any pad of its size (twist: one rail; points / cross / interlock: two), as long as trains
     that leave together never share a rail. Choosing *which* block goes where is part of the puzzle.
   * Empty build spots are pads under the rail. While dragging, the pads the block fits light up and the
     target glows with a see-through preview of the block; snap within about half a column.
   * Drag a placed block to another pad; drag it off the line to remove it; drop onto a placed block to
     replace it (the old one goes back to the supply). Drags on empty map still pan, pinch zooms.
   * New twists start at π/4; tap a twist to add π/4 (wraps to 0; a 0 twist stays as a "do nothing" piece).
     Long press only shows the label.
   * On a phone the dragged block floats above the finger.
   * Board locked while trains run; Run turns into Stop, which ends the run and resets the line.
   * Clear button; each level's build is saved in the browser. Pressing a palette block (or Enter) puts it on
     the first free pad. With "Under the hood" open, the palette moves into its header and the circuit
     updates on every edit.
   * Fixed blocks show a lock in their label. The Build menu is gone; `?level=4&solution=entangled` loads an
     example build (tests, demo video).
   * [x] Tomáš verified
   * **Build cells instead of fixed slots** (11 Oct): the level lists single build cells; any two neighbouring
     empty cells of one column take a two-rail block, otherwise each takes a twist. Dropping a block clears
     whatever was in its way. Same rule in Python and JS, covered by the tests and the fuzzing.
   * [x] Tomáš verified
   * **Teaching the points rule, branch colours, menu, playground** (11 Oct):
     * New level 4 "Switch both ways": the phase difference at quantum points picks the exit (π in the first
       loop, a cancelling π in the second). Entangled couples is now level 5, with a blurb that explains the
       interlock as "a twist that only happens when a train is on each of its rails".
     * At quantum points a label shows the arriving ghosts' phase difference and where they merge; when the
       trains are entangled it shows one line per branch ("if orange on A: Δφ 0 → D").
     * Chain lines removed. Entangled ghosts wear coloured rings, one colour per joint branch, and their
       labels show a dot per branch with that branch's phase. Entangled ghosts stop rolling (no phase of
       their own); they roll again once a station measures them.
     * Menu (Levels / Playground) and a level grid with big numbers, names, three stars (filled by scoring,
       step 10) and "cleared · best N runs".
     * Playground: every block plus stations and trains, unlimited; + buttons add columns (end of line) and
       tracks (top and bottom); "trains take turns / leave together" toggle (together: each train owns the
       tracks from its depot down to the next train's; the interlock appears). Limits: 8 tracks, 10 columns,
       20 qubits (tracks + stations), 4 trains. "reset" returns to a small line. Saved in the browser.
     * Checked with 60 random playgrounds (up to the limits): every block kept, circuit == train physics,
       runs finish without errors.
   * [x] Tomáš verified
   * **One-run levels, cars, pause** (11 Oct):
     * Run plays the **ideal run**: a train of `cars` cars per circuit (level field, default = enough for every
       passenger), each car one shot, spread over the outcomes exactly by their probabilities (largest remainder,
       interleaved). Every level is cleared by one press of Run; stars = share of passengers picked up
       (3 = all). Same rule in Python (`quantrain/score.py`) and JS (`idealRun`), parity-tested; a test checks
       that each level's best example build clears it and the wrong ones don't.
     * The cars follow each other and never stop; each car is measured as it passes a station, so the train
       splits car by car; passengers hop onto the passing car. Labels on the first car of every branch.
     * Buttons: idle [Under the hood][Run] → running [Stop][Pause] → paused [Stop][Resume] → done [Under the
       hood][Run again]. The board is locked while trains run.
     * Under the hood: the outcome table adds "Ideal run (cars)" and "Shots"; a "Run 1000 shots" button draws
       real shots (local statevector sampler for now; the Qollab port swaps in one simulator job).
     * Playground: − next to every + (last column, top / bottom track, with whatever stood there; never the last
       column, track or train).
   * **Tomáš verifies** ← we are here
9. [~] Qollab port (`python tools/build_qollab.py` → `qollab/` + `dist/quantrain-qollab.zip`, upload as a new project):
   * JS / Qiskit project: `index.html` (markup), `main.css`, `main.js` (game + engine + levels, same script as the
     prototype), `quantrain/` Python package, `README.md` (project card), MIT `LICENSE`.
   * three.js comes from Qollab (0.186); localStorage is blocked there (builds and stars last for the session).
   * "Run 1000 shots" calls `quantrain.qollab.run_shots(backend, …)`: Python builds the run's circuits with
     `build_run`, removes barriers, rewrites them into basic gates (XXPlusYY → ry/rz/cx…), sends them as ONE job
     to the backend picked in Select QPU, and returns decoded outcome counts (noise shows as "derailed").
     On IonQ the button then explains the one-job-per-run rule.
   * Tested: the rewritten circuits keep the exact probabilities (test_engine), one job on Qiskit's
     BasicSimulator returns valid outcomes, and the built page runs in a sandboxed frame with three 0.186 and a
     stub bridge. Not yet tested: Qollab itself (Tomáš uploads), Pyodide, IonQ simulator.
10. [x] Scoring: the ideal run (one Run clears a level), stars by passengers picked up.
11. [ ] Project page (problem, why quantum, how to run, results, limitations, pre-existing code), MIT
   license, line "This effort is supported by Qollab & IonQ".
12. [ ] 2–3 min demo video, public link, no sign-in.

## Campaign levels (docs/LEVELS.md)

* [x] L1–L10 built as `levels/01-first-departure` … `10-nosy-inspector` (the "engine already done" group).
  Then five levels of our own (not in LEVELS.md), all on existing mechanics: 11 Switch both ways (phase picks the
  exit, both ways), 12 Remote twist (the interlock as a twist another train controls), 13 Remote switch (making
  entanglement: split teal + interlock → couples A–C / B–D), 14 Entangled couples, 15 Swap partners (a twist on
  one entangled train swaps who meets whom). Each level is scored by the one-run ideal run (cars = passengers), not by η:
  every example build in LEVELS.md gives the stars it should (tests: `test_ideal_run_clears_levels_in_one_run`).
* Not done from LEVELS.md for these levels: L2's "arrive upside down" objective (Q1 open), the "can't be reached"
  warning, the classical-metro bar, inspector art / dashed decohered ghosts, hints.
* Next groups: construction site + days (L11, L12) → pair source (L16, L17) → lamps (L18) → signals, tilt, siding.

## How the prototype is built

`python tools/build_prototype.py` inlines `prototype/src/engine.mjs` and `levels/*.json` into
`prototype/src/app.html`, writing `prototype/index.html` (opens straight from disk).
Edit the sources, not the built file. The old single-file prototype stays in `prototype/01-test-line/`
for reference.

## Open questions

* Middle rails: with the 3.6 rail gap a platform fits beside a middle rail without touching the
  neighbour's rolling train, so no island platforms are needed for now.
* Star thresholds relative to the optimum.
* Performance (proposed, not done yet):
  * render only when something changes;
  * merge each level's static meshes into a few draw calls;
  * adaptive pixel ratio;
  * update labels only when the view or the trains move.

## Wishlist after the hackathon

* [x] **Share your own puzzle (done 11 Oct; codec in engine.mjs, random puzzles in the parity test):** Create mode in the Playground (placed blocks
  become fixed, mark player cells, set the supply with ±, passengers, name + description), play-test with ★★★
  required before sharing, then the whole level (same level format) compressed into the URL fragment
  (`#p=q1.<deflate+base64url>`, ~150–700 chars) with a QR code and a copyable puzzle code. Links point to a public
  GitHub Pages copy (Qollab's sandbox can't read URLs; on Qollab: an "Open a puzzle code" box). Opened puzzles are
  immutable except the player cells; "Remix" copies one into the Playground. Community chapter via GitHub issues/PRs.

* Live circuit view during a run: highlight the column the leading car is in (the circuit panel is static now).
* [x] Level-complete card (done 11 Oct): stars pop in one by one, what every car did, Under the hood / Keep building /
  Levels / Next level.

## Ideas for the full game (discussed 11 Oct, not decided)

* Test levels 1–4 are throwaway; the real game gets 10–20 designed levels.
* **Element set:**
  * Single train: points + twists + crossovers are already universal (any linear-optics network).
  * Candidates:
    * tunable points (an MZI as one block);
    * construction site (loss) → bomb-tester level;
    * long delay / siding (time-bin, see below);
    * phase interlock CP(kπ/4);
    * signal (feed-forward: a station's result throws a later element), needed for teleportation.
* **Delay:**
  * A short delay is just a twist.
  * A long one makes paths distinguishable (no interference), unless the other path is delayed equally.
    That's the "balance your interferometer" puzzle and time-bin qubits (Franson).
* **Pair source** (on-chip Bell state):
  * The pump train splits at points into two sources; each source turns it into a signal + idler pair of trains.
  * Gives entanglement with linear optics only (more honest than the interlock).
  * Later: twists before the stations → correlations change → a CHSH "beat the classical metro" level.
* **Train cars** = more degrees of freedom of one photon:
  * polarization (car tilt);
  * time-bin (front/back car);
  * colour.

  A polarizing splitter is a deterministic CNOT between path and polarization of one photon (real linear
  optics), so cars give entanglement on a single track.

## Level sequence for the real game (proposal, 10–20 levels)

1. **Paths and phases (one train):**
   * twist line → quantum points → dark port (Mach–Zehnder);
   * routing with crossovers;
   * three- and four-way splits;
   * a mid-line station that destroys interference;
   * bomb tester with a construction site;
   * **the mist level** (below).
2. **Cars = more properties of one photon:**
   * polarization cars and the polarizing splitter (entangling path and polarization on one track);
   * delays and time-bin ("balance your interferometer").
3. **Two trains from the pair source:**
   * couples that must arrive together;
   * twists before the stations change the correlations.
4. **Finale:**
   * a CHSH level where the score beats the best possible classical metro;
   * teleportation with signals (feed-forward).
   * The interlock stays as an advanced "not quite photonic" element, or goes.

## Level idea: the mist (Tomáš, 11 Oct)

Several parallel tracks are covered by mist or clouds, so the player can't see what is on them. Some
tracks hide construction work, which absorbs the train: the probability on that track drops to zero.

The player has to:
1. spread the train in superposition over all tracks, so no single blocked track can stop it;
2. bring all paths back together before the final station, where they reunite.

The player builds both the split and the reunion. Physics: a multi-path interferometer with unknown losses
(construction = absorber); the recombination must be tuned so the surviving amplitude interferes into the
station. Needs the construction-site (loss) element.
