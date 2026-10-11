# How Quantrain works

This is the reference for what the game does: how the metro map becomes a Qiskit circuit, how a run is
played and scored, and how we check the physics. It describes the code as built. The original design notes
are kept separately in [`design/`](design/).

## 1. The idea in one paragraph

The train is a single photon. Each track is one possible path for it, so a map with *n* tracks is an
*n*-qubit register in **path encoding**: exactly one track qubit is `1`, the one the train is on. Quantum
points (beam splitters) put the train on two tracks at once, twists (phase shifters) change the phase
between those paths, and when the paths meet again they interfere. Stations are detectors. The puzzle is
to arrange the blocks so that interference sends the train where the passengers are waiting. Every map is
compiled into a real Qiskit circuit, which you can inspect and run on a simulator or IonQ hardware.

## 2. The map as a circuit

| On the map | In the circuit | Notes |
|---|---|---|
| Track A, B, C… (top to bottom) | qubit 0, 1, 2… | One named register per track (`rail_A`, …) so the diagram reads like the map. |
| Depot | `X` on the depot track's qubit | The train starts on its depot track. |
| Column 1…n (left to right) | time | Everything in a column acts at the same moment; a barrier separates columns. |
| **Twist**, *k* steps | `P(k·π/4)` on the track | The train's roll on screen is its phase. Twists add up and wrap round after 8 steps (2π). |
| **Quantum points** | `XXPlusYYGate(θ, π/2)` on two neighbouring tracks | A beam splitter. On a single train it acts as `RY(θ)` on the pair. The default is 50:50; in general the train stays on its track with probability cos²(θ/2). |
| **Crossover** | `SWAP` on two neighbouring tracks | The two tracks trade places. |
| **Interlock** | `CZ` on two neighbouring tracks of *different* trains | A phase of π only when both trains are on those tracks. This is how two trains become entangled. |
| **Station** | an extra qubit, and `CX` (track → station) | A which-path detector: it records "a train passed here" and, just like a real detector, destroys interference downstream. |
| Exit | measure every qubit | Which stations saw the train, and which track it left on. |

A couple of details:

* **Sequential trains** (the default) take turns, so each train gets its own circuit. **Trains that leave
  together** share one circuit; each train owns the tracks from its depot down to the next train's depot,
  and only an interlock connects the tracks of two trains. The level validator enforces this rule.
* A run sends all of its circuits as **one job**, because IonQ accepts one job per Qollab run.
* An outcome reads as "stations that saw a train | exit track(s)". If noise on real hardware leaves the
  tracks in an impossible state (no train, or two trains on one train's tracks), the outcome is "derailed".

### Example: the dark port (level 4)

Two 50:50 points in a row form a Mach–Zehnder interferometer. Untouched, the two paths of the train cancel
on track A and every train leaves on B. A twist of π on one path flips the interference and every train
leaves on A. Twists of π/4 or 3π/4 give the mixed splits in between.

```
          points     twist     points
rail_A: ─X─┤XX+YY├────────────┤XX+YY├─ M      without the twist: every train leaves on B
rail_B: ───┤XX+YY├────P(π)────┤XX+YY├─ M      with the twist (π): every train leaves on A
```

## 3. What you see on screen

* **Ghosts.** While the train is on several tracks at once, every one of those tracks carries a translucent
  copy of it, a ghost. The label above the train shows its phase φ.
* **Roll = phase.** Each ghost rolls around the track by its phase, so a π twist turns it upside down. Two
  ghosts meeting at points interfere according to the *difference* of their rolls. The game makes no
  claim about the absolute phase.
* **Entanglement.** When two trains are entangled, their ghosts no longer roll on their own (each one alone
  has no definite phase). A hanging chain joins the ghosts that belong together, and coloured dots on the
  label show which branch of the other train each ghost goes with.
* **Measurement.** When a car reaches a station, the ghosts it passes collapse: the car is either there or
  it isn't, and the other ghosts vanish.

## 4. A run and the stars

One press of **Run** sends one train of **cars**, and every car is one shot of the circuit.

* **How many cars:** the level's `cars`, or by default enough to carry every passenger once:
  ceil(passengers ÷ circuits).
* **The ideal run:** the cars are spread over the outcomes exactly in proportion to their probabilities
  (largest-remainder rounding), interleaved so that the animation alternates outcomes (A B A B, not A A B B).
  The score therefore depends only on what you built, not on luck.
* **Boarding:** each car picks up one waiting passenger at every station that saw it. A **couple**
  (two linked stations) boards only when the same car is seen at both stations, which is how the
  entanglement levels test correlations rather than single probabilities.
* **Stars:** ★★★ when every passenger is picked up, ★★ for at least two thirds, ★ for at least one third.

**Under the hood** shows the circuit, its Qiskit code, the exact probabilities from two independent
calculations (the circuit simulation and the train physics), the ideal run, and **Run 1000 shots**.
On Qollab, the shots go as one job to the backend chosen in Qollab's *Select QPU* dialog (any free
simulator, or IonQ). Before sending, the bridge (`quantrain/qollab.py`) removes the barriers and transpiles the
circuits into gates every backend accepts (`x h ry rz p cx cz swap`). Real shots wander around the exact
probabilities (about ±3 % for 1000 shots). Outside Qollab, the page samples the exact distribution locally.

## 5. Architecture

```
levels/*.json  ──►  quantrain/  (Python)          ──►  Qiskit circuits ──► Qollab backend / IonQ
 (level files)      level.py   load + validate                ▲
                    circuit.py  map → circuit                 │ the same circuits, gate for gate
                    score.py    ideal run + stars             │ (tests/test_js_parity.py)
                    reference.py physics without Qiskit       │
                    qollab.py   one-job bridge for Qollab     │
               └─►  prototype/src/engine.mjs (JavaScript) ────┘
                    the same translator, a statevector simulator and the train physics, in the browser
                    prototype/src/app.html: the game (three.js), built into one page by tools/build_prototype.py
```

* **In a plain browser** (GitHub Pages), the JavaScript engine builds and simulates the circuits exactly,
  and Under the hood prints the same Qiskit code the Python package builds.
* **On Qollab** (`tools/build_qollab.py` → `dist/quantrain-qollab.zip`), the same page runs as a
  JS / Qiskit project. `main.js` imports the Python package through Qollab's bridge, and real shots run there.

## 6. How we know the physics is right

Run `python tests/test_engine.py` and `python tests/test_js_parity.py` (the second needs Node.js).

* **Two independent models.** `reference.py` simulates the trains with no Qiskit at all (amplitudes on
  tracks, detector branches). For every level solution and for random builds on maps up to 10 tracks
  and 4 trains, its probabilities match Qiskit's statevector to 1e-8.
* **Gate identities.** `XXPlusYYGate(θ, π/2)` equals `RY(θ)` on a single-train pair. The
  transpiled circuits sent to backends give the same probabilities as the originals.
* **Browser = Python.** 262 circuits (every level solution, random fuzz builds, and 40 random community
  puzzles sent through the share code and back) are rebuilt by the JavaScript engine. Its Qiskit code is
  executed and compared instruction by instruction with the Python translator, and the probabilities and
  ideal runs agree.
* **Every level can be cleared in one run.** For each level, the intended solution gets ★★★ and the
  tempting wrong builds get the stars the design expects.
* **Validation.** Broken levels (overlapping blocks, points on tracks that aren't neighbours, two trains
  sharing a track, couples that don't name each other, …) are rejected with a clear message.

## 7. Community puzzles: the share code

A puzzle is the Playground map packed into a compact array, compressed and written into the link after `#p=`
(about 100–300 characters, e.g. `q1.JYq9CsMw…`). That part of a URL never reaches a server, so nothing is uploaded or
stored anywhere. Opening a code rebuilds an ordinary level file and runs it through the same validator as the
campaign levels. A puzzle can be shared only after its maker clears it with ★★★, so every shared puzzle is
solvable. The exact format is in [`LEVEL_FORMAT.md`](LEVEL_FORMAT.md#share-codes-community-puzzles).

## 8. Simplifications we chose (and why)

1. **Trains are hard-core particles.** A qubit holds 0 or 1, so two trains can never be on one track.
   Real photons meeting at a beam splitter bunch (the Hong–Ou–Mandel effect); ours can't meet. The rule
   that trains leaving together never share a track keeps the game honest about this.
2. **The interlock is not linear optics.** A deterministic `CZ` between two photons needs a non-linear
   element. In real photonic quantum computing it works only with some probability (KLM-style schemes, with
   extra photons and detectors). We keep it deterministic so that the entanglement puzzles stay puzzles.
3. **Stations measure only which track.** Other measurements are made the way the lab does it, by
   placing points and twists before the detector.
4. **Global phase is not shown as a puzzle mechanic.** Only phase differences change outcomes, and the
   game only ever asks for those.
