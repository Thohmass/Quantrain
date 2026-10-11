# Quantrain — quantum model & visual language

> **Design notes, kept for the record.** This is the first-day proposal for the quantum model. Several ideas here changed while building (the interlock is a `CZ`, stars come from the ideal run, there is no realism mode). The game as built is described in [`../HOW_IT_WORKS.md`](../HOW_IT_WORKS.md).

*Draft v0.1 · 10 Oct 2026 · living document*

Quantrain is a Mini-Metro-style puzzle game in which the train — the **quantrain** — is a single photon.
Underneath every metro map is a real Qiskit circuit. This file defines **what every quantum concept
means on the map, how it looks, and which Qiskit instructions implement it.** All gate conventions
marked ✅ were checked numerically with Qiskit 2.5.2 (scripts in the appendix).

---

## 1. Core idea: path encoding

| Metro | Physics | Qiskit |
|---|---|---|
| A rail (track segment between two columns) | an optical **mode** (a waveguide / light path) | one qubit |
| The quantrain on rail *k* | one photon in mode *k* | qubit *k* = `1`, all others `0` |
| A quantrain spread over several rails | the photon in a superposition of paths | a superposition of one-hot bitstrings |
| Map columns, left → right | time steps | circuit layers (moments) |
| Stations at the end of the rails | photodetectors | `measure` |
| One dispatch of a train | one photon sent through | **one shot** |

**Encoding: one-hot ("one qubit per rail").** Rail *k* ↔ qubit *k*; "train on rail *k*" ↔ bitstring with a
single `1` at position *k*. This is what photonic chips actually do (each waveguide is a mode), and it
makes the circuit view a literal redrawing of the map: **each qubit wire *is* a rail.** A junction
between two rails is a 2-qubit gate between neighbouring wires.

Trade-offs and rejected alternatives:
- *Binary encoding* (N rails in log₂N qubits) uses fewer qubits, but junctions turn into
  multi-controlled rotations and the circuit no longer looks like the map. Rejected.
- One-hot gives **built-in error detection**: a measured bitstring with zero or several `1`s is
  physically impossible for one train. On noisy simulators or hardware these outcomes show up as
  **derailments**, which is honest and fun.
- Budget: N rails + a few ancillas ≈ 4–14 qubits per level. Check the qubit limit of Qollab's IonQ simulator before designing big levels.

**Terminology.** A train on N rails is a *qudit* (dimension N). Two rails reserved for one train form a
**dual-rail qubit**: rail **a** = logical |0⟩, rail **b** = logical |1⟩. This is how real photonic
quantum computers (e.g. PsiQuantum, Quandela) encode qubits, so "quantrain = photonic qubit" is accurate
in dual-rail levels.

---

## 2. What the quantrain carries, and how we draw it

| Quantity | Physics | Visual (proposal) |
|---|---|---|
| Which rail(s) | path / mode | where the train (or its ghosts) is drawn |
| Superposition | amplitude on several rails | the train splits into **ghosts**, one per rail |
| \|amplitude\|² | probability of arriving there | **ghost opacity** (floor ≈ 15 % so small ones stay visible) + % on hover |
| Phase (arg of amplitude) | photon phase / Feynman's stopwatch hand | **roll angle** of the train around its rail (see 2.1) |
| Train identity | which photon / which logical qubit | **train colour** |
| Photon colour (wavelength) | distinguishability | same as identity: differently coloured trains never interfere with each other |
| Entanglement | non-product joint state | **linked ghosts** + branch board (section 7) |
| Decoherence / which-path known | mixed state | ghosts lose their roll marker → dashed outline, no glow (section 8) |
| Loss | photon absorbed | ghost fades into dust at a construction site |
| Measurement | detector click | ghosts collapse: one turns solid, the others pop |

### 2.1 Phase = roll (your idea, kept)

Picture a rail as a single 3D line with the train riding *around* it. The **roll angle φ** around the
rail is the phase. In a top-down 2D view a pure roll is ambiguous: φ and π−φ look the same. So the
proposal is to draw the roll as an **end-on badge** on the round train body: a small circle (the rail
seen head-on) with a dot showing where the train sits on it.

- φ = 0 → dot on top ("upright")
- φ = π → dot at the bottom ("upside down")
- φ = +π/2 → dot on the right ("leaning right"); φ = −π/2 → dot on the left

The badge is a phasor, i.e. Feynman's stopwatch from *QED*. Hue stays reserved for train identity.
An optional "analyst view" could add domain colouring (hue = phase) for screenshots and documentation.

**Global vs relative phase.** Rolling *every* ghost by the same angle changes nothing physical. Only
the **difference** in roll between ghosts matters, and only when they meet at a junction. Rendering
rule: show rolls relative to a reference ghost (the most probable one is drawn upright), or show
absolute rolls but never let gameplay depend on them.

### 2.2 The six cardinal states (dual-rail train)

| State | Map picture | Distinguishable at stations alone? |
|---|---|---|
| \|0⟩ | solid train on rail a | yes |
| \|1⟩ | solid train on rail b | yes |
| \|+⟩ | two 50 % ghosts, **same roll** | no (50/50) |
| \|−⟩ | two 50 % ghosts, rail-b ghost **upside down** | no (50/50) |
| \|+i⟩ | rail-b ghost rolled **¼ turn right** | no (50/50) |
| \|−i⟩ | rail-b ghost rolled **¼ turn left** | no (50/50) |

General Bloch state: the split ratio is θ (opacity) and the relative roll is φ.

**Key puzzle insight ✅:** stations only measure *which rail* the train is on. |+⟩ and |−⟩ give identical
station statistics. A **junction placed before the stations** turns roll differences into rail differences:
after a 50:50 junction, |+⟩ → 100 % one station and |−⟩ → 100 % the other. ±i stay at 50/50 after
that junction. Separating them needs a **¼ twist** first. Real photonic experiments read phase in exactly
this way, and it is the backbone of most levels.

---

## 3. Track element catalogue (single train, N rails)

| Game element | What happens to the quantrain | Optical element | Qiskit (one-hot) | Typical player control |
|---|---|---|---|---|
| **Depot** | train enters on rail k | single-photon source | `qc.x(k)` | fixed |
| **Track** | nothing (rolls stay equal on equal-length tracks) | free propagation | identity | — |
| **Twist tunnel** (φ) | train rolls by φ on that rail (a rifled/spiral tunnel) | phase shifter | `qc.p(φ, k)` | dial, π/4 steps |
| **Quantum points** (θ) | train splits between two rails; ghosts arriving together **interfere** | beam splitter | `XXPlusYYGate(θ, π/2)` on rails (i, j) | usually **fixed**; adjustable in sandbox |
| **Crossover** | two rails swap places | waveguide crossing / mirror pair | `qc.swap(i, j)` | placeable |
| **Construction site** | any ghost on this rail is lost | absorber / blocked path | `qc.swap(k, loss_q)`; loss qubit measured at end | fixed hazard |
| **Ticket inspector** | records which rail the train used; **kills interference** downstream | which-path detector (non-destructive) | `qc.cx(k, record_q)` | placeable / hazard |
| **Long siding** | that ghost arrives ≥ 1 tick late, misses its partner → no interference | long delay line (time-bin) | `qc.cx(k, timing_q)` + drawn delay | placeable |
| **Station** | train stops here; 1 passenger boards | photodetector | `measure` | fixed, with demand |
| **Closed station** | train must not arrive here | detector that costs points | `measure` + scoring | fixed |

### Notes and conventions

- **"X = switching rails".** In railway language a *switch / points* is the device that *splits* the
  route, and in Quantrain that is the beam splitter ("quantum points" send the train both ways at once).
  Swapping which rail the train is on is the **crossover**, and in a dual-rail pair the crossover **is** the X gate ✅.
- **Junction convention ✅.** `XXPlusYYGate(θ, β)` acting on two rails leaves "no train" and "two trains"
  untouched and rotates the single-train pair:
  - `β = π/2` → exactly **RY(θ)**: a *real* splitter, P(stay) = cos²(θ/2), P(switch) = sin²(θ/2). **Game default**, so that every phase the player sees comes from a visible twist tunnel.
  - `β = 0` → exactly **RX(θ)**: the physical symmetric beam splitter, with a hidden *i* on the switched path. Use it only in an "optics realism" view.
  - θ = π/2 gives 50:50. Rail ordering in the qubit pair flips signs, so always pass `[upper_rail, lower_rail]`.
- **Delay — two kinds.** A *short* delay (shorter than the train) only shifts phase, so it is just a twist
  tunnel; for a monochromatic photon, φ = ω·Δt. A *long* delay (at least one tick) makes the ghosts arrive at
  different times. They can no longer interfere, because the arrival time reveals the path. This is equivalent
  to an inspector, so we implement it the same way (an ancilla records "late") and animate the late ghost.
- **Construction site = deferred measurement ✅.** IonQ takes one circuit per run, and we avoid mid-circuit
  measurement. Absorption is a SWAP of the rail into a fresh ancilla that is measured at the end. Verified
  Elitzur–Vaidman ("bomb tester") behaviour: a tuned interferometer sends 100 % of trains to station A.
  Blocking one arm gives 50 % lost, 25 % A and **25 % at the previously dark station B**. In those runs the
  blockage is detected without the train touching it.
- **Inspector ✅.** A CX that copies "train on rail k" into an ancilla: the tuned interferometer drops from
  100/0 to 50/50. Teaching moment: *looking* at the train is what destroys interference, not touching it.
- **Optional mode, path length = phase.** The train's badge spins as it travels (Feynman stopwatch), so
  unequal track lengths create phase. This is physically beautiful but makes free-hand line drawing very
  fiddly. It's off for the MVP, where phase comes only from twist tunnels and all rails between two columns
  count as equal length.

---

## 4. Gate dictionary — logical qubits (dual-rail trains)

Logical |0⟩ = rail a (upper), |1⟩ = rail b (lower). All single-train rows ✅ verified, up to global phase.

| Gate | Metro build |
|---|---|
| X | crossover of a ↔ b |
| Z | twist π on rail b |
| S / S† | twist +π/2 / −π/2 on rail b |
| T / T† | twist +π/4 / −π/4 on rail b |
| P(φ), RZ(φ) | twist φ on rail b (RZ differs only by a global phase) |
| RY(θ) | real quantum points, θ |
| RX(θ) | symmetric quantum points, θ |
| √X | symmetric 50:50 points |
| H | twist π on rail b → real 50:50 points |
| Y | crossover → twist π on rail a |
| SWAP (two trains) | cross both rail pairs. Pure rerouting, so **linear optics can do it** |
| CNOT (A controls B) | **Interlock**: if train A is on its rail b, B's crossover is thrown → `qc.cswap(A_b, B_a, B_b)` |
| CZ | **Interlock-twist**: B gets a π roll if both trains are on rail b → `qc.cz(A_b, B_b)` |
| Toffoli | double interlock (`mcx` / `cswap` with two controls) |

**The interlock is a railway signal**: one train's position sets the points for another. ✅ Verified: H on
train A, then an interlock, gives the Bell state (both trains on rail a) + (both on rail b), each with 50 %.

**Honesty note (put this on the project page).** Photons don't interact, so linear optics cannot build a
deterministic interlock. Real photonic QC does it *probabilistically*, using extra photons and detectors (KLM
scheme; the post-selected CZ succeeds 1 in 9 times) or with fusion measurements. Trapped ions (IonQ!) and
superconducting qubits have native entangling gates. Two options:
- *Arcade mode:* the interlock just works, and we label it as a "non-linear element".
- *Realism mode:* the interlock succeeds 1/9 of the time, otherwise the run derails. This is emulated with an
  ancilla `RY` coin, so the success cost is real in the statistics.

---

## 5. Measurement, shots and the animation pipeline

1. **Compile** the level and player settings into one `QuantumCircuit` (one-hot rails + ancillas, measure all).
2. **Exact forecast (instant).** `Statevector` after each column gives every ghost's amplitude at every column.
   This drives the live preview while the player edits (the "timetable" and ghost animation) and the star rating.
   For a single train it is just N complex numbers per column.
3. **Submit = one job.** `backend.run(circuit, shots=1024)`, a single call, which satisfies IonQ's one-job-per-run limit.
4. **Shots → dispatches.** Each shot is one train dispatch. If the backend returns per-shot memory, replay the
   shots in order. Otherwise expand the counts into a multiset and shuffle it with a fixed seed. Either way,
   animation statistics match the measured distribution exactly; no rounding is needed.
5. **Replay.** Dispatch trains one by one until every station's demand is met. Ghosts split and interfere along
   the route and collapse at the station layer. An invalid bitstring (≠ one `1` on the rail qubits) plays a
   derailment. A `1` on the loss qubit plays a lost-at-construction animation.
6. **Results screen.** Predicted (statevector) vs measured (shots) histogram per station, plus a classical-metro
   bar. This is the "science" panel the judges will want.

Simulation backends: Qollab hands us `backend`. Local simulators allow many jobs per run; IonQ allows one,
so "Verify all solved levels" batches every circuit into a single `backend.run([...])`.

---

## 6. Game loop, scoring & stars

- Station *k* has demand *d*ₖ passengers; D = Σ*d*ₖ. Each dispatch picks up **1** passenger where the train is measured.
- Wasted run: the train arrives at a station that is already served, is lost, or derails.
- Arriving at a **closed station** wastes the run and adds a penalty (for example, 3 strikes = level failed). To be tuned.
- **Efficiency η = D / E[runs to serve everyone]**, where η = 1 is perfect.
  - E[runs] is computed from the exact distribution *p* by Monte-Carlo (≈10⁴ simulated playthroughs, instant).
    **Stars come from *p*, not from the single animated replay**, so luck doesn't decide them. The replay's own
    count is shown as "this run".
  - Even *p*ₖ = *d*ₖ/D has η < 1 because of randomness. The only route to η = 1 is **deterministic delivery**,
    which a perfectly tuned interferometer can achieve and a random classical switch can't. Good levels exploit this.
- **Classical baseline.** The same map with every junction replaced by a random coin-flip switch of the same
  ratio, and twist tunnels ignored (no interference). Its η is shown next to the player's.
- **Stars (placeholders):** ★ beat the classical metro · ★★ ≥ 90 % of the level's optimum · ★★★ ≥ 98 % of optimum.
  The optimum per level is found offline by the level designer, by grid search over the adjustable elements.
- **Why most junctions are fixed.** If players could set every split ratio freely, a classical random switchyard
  could reach any distribution, and judges would rightly call it a Markov chain. With fixed junctions and adjustable
  **twists / crossovers**, every solution *must* use interference. That is the Quantum Playground bar.

---

## 7. Several trains & entanglement

- Each train has its own colour and its own dual-rail pair (or rail group).
- **Product state:** each train's ghosts behave independently.
- **Entangled state:** show the joint state as **branches**. Each term of the superposition is one configuration
  of *all* trains, drawn as ghosts joined by a thin **tether** in a shared link style. Opacity = branch probability;
  badges show relative phase.
  - Two independent 50/50 trains → 4 tethered configurations (a grid).
  - Bell state → only 2 configurations: (a,a) and (b,b).
- **The spooky moment:** when train A reaches its station, every branch inconsistent with A's outcome vanishes at
  once, including B's ghosts on the other side of the map.
- **Branch board:** a departure-board panel listing each configuration with a probability bar and phase badge.
  An optional entanglement meter shows entropy of one train's state (0 = independent, 1 bit = maximally entangled).
- **Fun fact for the circuit view.** In one-hot encoding, a single train spread over 3 rails is a *W state* of
  the 3 qubits. The circuit view shows qubit entanglement even with one train (the "single-photon mode
  entanglement" debate). Worth one sentence in the docs, not a game mechanic.

---

## 8. Decoherence, noise and loss

- **Quantum superposition vs classical uncertainty must look different.**
  - Coherent ghosts: glowing outline, visible roll badge.
  - After an inspector or long siding, ghosts that are now just *classical alternatives*: dashed outline, badge
    replaced by "?". They still split by probability but no longer interfere at junctions.
- **Noise models** (Qollab offers ideal and noise-model simulators): derailments appear naturally as non-one-hot
  outcomes. The results screen can show "% of runs derailed", a nice hook for the documentation.
- **Loss:** construction sites (deliberate) and, in realism mode, failed interlocks.

---

## 9. Known physics simplifications (be upfront about these)

1. **Two trains on one rail is impossible** in our encoding, because a qubit holds 0 or 1. Our trains behave like
   *hard-core* particles. Real photons meeting at a 50:50 beam splitter bunch (Hong–Ou–Mandel effect); ours would
   pass through unchanged. MVP rule: trains in multi-train levels never share a junction. They interact only through
   interlocks, and the level validator enforces this.
2. **The interlock is not linear optics** (section 4).
3. **Global phase is unobservable.** Gameplay never depends on it.
4. Stations measure only the rail (path) basis. Other bases are measured by building junctions and twists before
   the stations, exactly as in the lab.

---

## 10. Data model & compiler sketch

```jsonc
// levels.json (one entry)
{
  "id": "L03-dark-port",
  "rails": 4,                          // rail k ↔ qubit k
  "ancillas": { "loss": 1, "record": 0 },
  "depot": 0,
  "columns": [
    [{ "type": "points", "rails": [0, 1], "theta": 1.5708, "locked": true }],          // π/2 = 50:50
    [{ "id": "tw1", "type": "twist", "rail": 1, "phi": 0, "locked": false, "step": 0.7854 }], // π/4 steps
    [{ "type": "points", "rails": [0, 1], "theta": 1.5708, "locked": true }]
  ],
  // ✅ with φ = 0 every train lands on rail 1 (the closed station); the player must find φ = π
  "stations": [
    { "rail": 0, "demand": 5 },
    { "rail": 1, "demand": 0, "closed": true }
  ],
  "stars": { "classical": 0.42, "optimum": 1.0 }
}
```

```python
from math import pi
from qiskit import QuantumCircuit
from qiskit.circuit.library import XXPlusYYGate

def compile_level(level, settings):
    n = level["rails"]
    loss = list(range(n, n + level["ancillas"].get("loss", 0)))
    rec = list(range(loss[-1] + 1 if loss else n,
                     (loss[-1] + 1 if loss else n) + level["ancillas"].get("record", 0)))
    qc = QuantumCircuit(n + len(loss) + len(rec))
    qc.x(level["depot"])
    for column in level["columns"]:
        for el in column:
            p = {**el, **settings.get(el.get("id", ""), {})}  # player overrides
            t = p["type"]
            if t == "points":   qc.append(XXPlusYYGate(p["theta"], pi / 2), p["rails"])
            elif t == "twist":  qc.p(p["phi"], p["rail"])
            elif t == "cross":  qc.swap(*p["rails"])
            elif t == "site":   qc.swap(p["rail"], loss[p["slot"]])
            elif t == "inspector": qc.cx(p["rail"], rec[p["slot"]])
            elif t == "interlock": qc.cswap(p["control"], *p["target"])
        qc.barrier()  # keeps columns visible in the circuit view
    qc.measure_all()
    return qc
```

On Qollab this lives in a Python package (`quantrain/engine.py`), called from `main.js` with `.callPromising`.
Levels are loaded from one `levels.json` whose path is written literally in Python (Qollab only ships files named
as plain strings).

---

## 11. Suggested hackathon scope

- **MVP (must ship):** single train; depot, track, twist tunnel, fixed + adjustable points, crossover, construction
  site, inspector, stations, closed station; 5–6 handcrafted levels + sandbox; map ↔ circuit toggle; replay
  animation; predicted vs measured vs classical results.
- **Stretch:** dual-rail trains with interlock, entanglement tethers and branch board; long siding; realism-mode interlock.
- **Level ideas:** 1. *First split* (one junction). 2. *Dark port* (Mach–Zehnder: deliver 100 % to one station).
  3. *The ±i problem* (needs a ¼ twist). 4. *Broken bridge* (bomb tester: detect the construction site).
  5. *Nosy inspector* (an inspector ruins your interference; route around it). 6. *Three-way share*
  (qutrit / Fourier-style split to match demands 1:1:1 deterministically-ish). 7. *Twin lines* (stretch: Bell pair via interlock).

---

## 12. Open questions

1. Phase badge vs a roll shading on the train body vs hue — decide during art direction.
2. Free-hand Mini-Metro lines vs a column grid. Proposal: curvy visuals but **topologically column-locked**
   (time flows left → right), so map ↔ circuit stays 1:1.
3. Per level, what may the player change: twists only, twists + crossovers, or also split ratios (sandbox)?
4. Closed-station penalty and failure rules.
5. Star thresholds, and whether to also show "runs used in this replay".
6. Circuit view: Qiskit's own drawer (`circuit.draw("mpl")`, SVG in Qollab) or a custom renderer that mirrors the map's styling.
7. Does Qollab's IonQ backend return per-shot memory, and what is its qubit cap? Check on the first deploy.

---

## Appendix — verification log (Qiskit 2.5.2, statevector)

- `XXPlusYYGate(θ, π/2)` on the single-train subspace = `RY(θ)`; `XXPlusYYGate(θ, 0)` = `RX(θ)`; θ = π/2 → 50:50; `β=0, θ=π/2` = √X.
- H = `p(π)` on rail b → `XXPlusYYGate(π/2, π/2)`. X = `swap`. Y = `swap` → `p(π)` on rail a.
- Mach–Zehnder (symmetric splitters) vs twist φ: φ = 0 → 0/100, π/2 → 50/50, π → 100/0.
- |+⟩/|−⟩ → after a real 50:50 junction 100/0 and 0/100; |±i⟩ → 50/50 (need S† first).
- Bomb tester with a loss ancilla: 25 % / 25 % / 50 % lost. Inspector via CX: 100/0 → 50/50.
- H on train A + `cswap(A_b, B_a, B_b)` → Bell state 50 % (a,a) / 50 % (b,b).
