# Quantrain

*A quantum puzzle game on a metro map, where the train is a single photon. This effort is supported by Qollab & IonQ.*

Lay out **quantum points** (beam splitters), **twists** (phase shifters), **crossovers** and **interlocks** so that
interference delivers every passenger with one press of **Run**. Under every map is a real Qiskit circuit: one
qubit per track, one per station. Then make your own puzzle and share it with a code.

**Source code and full docs:** https://github.com/Thohmass/Quantrain · **Play in any browser:** https://thohmass.github.io/Quantrain/prototype/ · **Video:** {{VIDEO_URL}}

## What problem it explores

Interference is the heart of quantum computing, and it is usually taught with bras, kets and matrices
before anyone gets a feel for it. Quantrain turns it into something you can play with. A beam splitter puts
the train on two tracks at once, a twist changes the phase between them, and when the paths meet again they add
up or cancel. A station on the way is a detector, and you watch it destroy the interference. Two trains
joined by an interlock become entangled, and couples of passengers only board when the trains' positions are
correlated. Each idea is one level, and every level is a real circuit you can open, read as Qiskit code and run
on a quantum backend. You build the intuition first, then see the circuit that matches it.

## How to run it

1. Press **Run** in Qollab. Any backend works; the built-in simulator starts at once. The game appears above
   the console.
2. Use a recent Chrome or Edge (desktop or Android). Qollab's Python bridge needs a browser feature that
   Safari doesn't have yet; the **Play** link above runs the game in any browser, including iPhone.

## How to play

1. Pick **Levels** (15 levels, from one track to entangled trains) or **Playground** (everything free).
2. Drag blocks from the dock onto the pads on the line, or press a block to put it on the first free pad.
   Tap a twist to turn it by π/4. Drag a block off the line to remove it.
3. Press **Run**. One press sends one train of cars, and each car is one shot of the circuit. The level is
   cleared when that one run picks up every passenger: ★★★ for all of them, ★★ for two thirds, ★ for one third.
4. Open **Under the hood** to see the Qiskit circuit and its code, the exact probabilities, and
   **Run 1000 shots**: real shots sent as one job to the backend you picked in Qollab's *Select QPU* dialog
   (IonQ allows one job per Qollab run).
5. **Make your own puzzle** in the Playground (✎ Make a puzzle). Choose which pads the player may build on
   and which blocks they get, clear it yourself with ★★★, and share its code. Someone else opens it with
   **Open a shared puzzle** in the menu. The whole puzzle is in the code: nothing is uploaded.

## The quantum model

| On the map | In the circuit |
|---|---|
| Track | one qubit (path encoding: exactly one track qubit is 1, the one the train is on) |
| Depot | `X` on the start track |
| Twist | `P(k·π/4)`: the train's roll on screen is its phase |
| Quantum points | `XXPlusYYGate(θ, π/2)`: a real beam splitter, 50:50 by default |
| Crossover | `SWAP` |
| Interlock | `CZ` between the tracks of two trains that leave together: this is what entangles them |
| Station | `CX` into its own qubit: a which-path detector that really destroys interference downstream |

**Scoring.** The score uses the *ideal run*: the cars are spread over the outcomes exactly by their
probabilities, so it depends only on what you built, not on luck. Real shots are shown next to it to
compare.

## The levels

| # | Level | What it teaches |
|---|---|---|
| 1 | First departure | the train is a photon, the station a detector, a car is a shot |
| 2 | Twist tunnel | phase: the roll you can't see at a station |
| 3 | Quantum points | superposition, then measurement at random |
| 4 | Dark port | interference (a Mach–Zehnder interferometer) |
| 5 | Quarter turn | only phase *differences* matter |
| 6 | Switchyard | crossovers carry ghosts across the map |
| 7 | Crossed wires | when swapping changes nothing, and when it does |
| 8 | Fair shares | chaining splits: shares of ½, ¼ and ¼ |
| 9 | Grand junction | four-way interference, a pattern of twists |
| 10 | Nosy inspector | which-path information destroys interference |
| 11 | Switch both ways | phase 0 or π picks the exit |
| 12 | Remote twist | a controlled phase: one train twists another |
| 13 | Remote switch | entanglement from an interlock |
| 14 | Entangled couples | perfect correlations that two independent trains can't produce |
| 15 | Swap partners | changing which outcomes are correlated |

## How it's built, and how to extend it

* **One level file, three engines that agree.** Each level is a small JSON file. The same translator exists in
  Python (`quantrain/`, used here on Qollab) and in JavaScript (the browser game). Tests check that they
  build the same Qiskit circuit gate for gate (262 circuits), and that Qiskit's results match an independent
  simulator written without Qiskit.
* **Make a level:** with the Playground's puzzle maker in the game, or by writing a level file. The format is
  described in `docs/LEVEL_FORMAT.md` in the repository, with a step-by-step guide.
* **Accessibility:** blocks can be placed from the keyboard (Tab to a block, Enter), and Under the hood gives a text
  version of every map (Qiskit code and a probability table). Details are in the repository README.
* **Files in this project:** `index.html`, `main.css` and `main.js` are the game. `main.js` imports the Python
  bridge `quantrain/qollab.py`, which builds the circuits with the `quantrain` package, transpiles them for
  the chosen backend and sends them as one job.

## Honest simplifications

* Two trains can never share a track (a qubit holds 0 or 1). Real photons can meet at a beam splitter and
  bunch together.
* The interlock is a perfect `CZ`. In real photonic quantum computing, this gate works only with some
  probability.
* Stations measure only which track the train is on. Other measurements are made the way the lab does it,
  with points and twists before the detector.

## Credits and disclosure

* Built from scratch during the hackathon build weekend (10–11 Oct 2026) by Bc. Tomáš Roch. No code existed
  before, and no Qollab template was used.
* Development used an AI coding assistant (Claude, by Anthropic) for code, tests and documentation, under
  the author's direction.
* Open-source software used: Qiskit (Apache-2.0); three.js with OrbitControls (MIT, provided by Qollab);
  qrcode-generator 1.4.4 by Kazuhiko Arase (MIT, included in `main.js` with its licence header); the fonts
  Figtree and JetBrains Mono (SIL Open Font License 1.1) via Google Fonts.

This effort is supported by Qollab & IonQ. MIT licensed.
