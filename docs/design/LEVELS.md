# Quantrain: level design (campaign proposal)

> **Design notes, kept for the record.** This is the campaign proposal (20 levels). The game ships 15 levels in [`../../levels/`](../../levels/); some follow this plan, others were changed or added while building. The game as built is described in [`../HOW_IT_WORKS.md`](../HOW_IT_WORKS.md).

*Draft v0.1 · 11 Oct 2026 · for discussion, nothing implemented yet*

This proposes 20 levels in five chapters. They teach a new player, one level at a time, what every element
does, how the elements interact, and why each puzzle needs real quantum behaviour. The order follows
"Level sequence for the real game" in `docs/PLAN.md`. A few bridge levels are added where a jump felt too big.

**Every result here was checked numerically.** Each "untouched", "wrong try" and "solution" outcome
was computed with Qiskit statevectors, using the conventions in `quantrain/circuit.py`:
points = `XXPlusYYGate(θ, π/2)` on `[upper, lower]`, twist = `P(k·π/4)`, cross = `SWAP`, station = `CX` into
its own qubit. New elements use the gate recipes in [section 4](#4-new-mechanics-needed). The η numbers are exact expected runs, not
samples.

---

## 0. Design rules

1. **One new idea per level, then reuse it.** Each element is *introduced* in a safe level, *used* in a puzzle, and
   later *combined* with something else.
2. **The untouched map is always a problem.** Pressing Run before building visibly fails (a station is unreachable,
   the wrong one fills up, or the split is 50/50 when 100 % is possible). The player always starts with a question.
3. **From level 4 on, full stars need interference or entanglement.** Each level card shows the *classical metro*
   (every points is a coin flip, twists do nothing) next to the player's score. Levels 3, 6, 8, 16 and 19 are honest
   exceptions: they teach a mechanic, and the level text says out loud that "a coin could do this too, for now".
4. **Only relative phase matters.** The only exception is the level-2 tutorial objective (open question Q1).
5. **Every new physics claim gets a one-line "under the hood" card** that names the real experiment or gate.

### Map legend

Maps use the grid of `docs/LEVEL_FORMAT.md`: columns are time, rails are qubits, and the depot sits left of c1.

| Token | Meaning | Token | Meaning |
|---|---|---|---|
| `[·]` | 1-rail build slot | `[¦]` | 2-rail build slot (shown on both rails it joins) |
| `PTS` | fixed 50:50 quantum points (both rails) | `CRS` | fixed crossover (both rails) |
| `T+2` | fixed twist, +2 steps (= +π/2) | `S:n` | station with *n* passengers (`S:0` = empty platform) |
| `INS` | inspector (a station with no passengers) | `BRG` | bridge (may be a construction site, depending on the day) |
| `~~~` | mist (hides construction sites) | `PBS` | sorting switch (polarizing splitter) |
| `PNT` | paint shop (fixed tilter, lays cars flat) | `SID2` | long siding, +2 ticks |
| `SRC` | pair source | `───` | plain track · `▶` exit |

Steps: a twist step = π/4 (8 steps = full turn). A tilter step = 45° of car tilt (2 steps = flat).

---

## 1. Overview

| # | Name | Chapter | New idea | Untouched → | Best build → | Classical metro |
|---|---|---|---|---|---|---|
| 1 | First departure | I First tracks | Run, train = photon, station = detector | 100 % (η 1) | (nothing to build) | same |
| 2 | Twist tunnel | I | Twist, roll = phase, a lone roll is invisible | roll 0 | roll ½ turn | — |
| 3 | Quantum points | I | Superposition, measurement is random | B unreachable | 50/50 (η 0.73) | same (honest) |
| 4 | Dark port | I | Interference (Mach–Zehnder) | 100 % to empty B | 100 % A (η 1) | η 0.50 |
| 5 | Quarter turn | I | Relative phase, wrap-around, the ±i problem | 50/50 | 100 % B (η 1) | η 0.50 |
| 6 | Switchyard | II The network | Crossover, neighbour-only rule | D unreachable | 50/50 A/D (η 0.73) | same (honest) |
| 7 | Crossed wires | II | Where a crossover matters inside an interferometer | 100 % B | 100 % A (η 1) | η 0.50 |
| 8 | Fair shares | II | Multi-way splits, matching demand ratios | B, C unreachable | 25/50/25 (η 0.57) | same (honest) |
| 9 | Grand junction | II | Four-path interference, twist patterns | 100 % D | 100 % A (η 1) | η 0.25 |
| 10 | Nosy inspector | III Looking & losing | Measurement destroys interference | 50 % B (η 0.5) | 100 % B (η 1) | η 0.50 |
| 11 | Broken bridge | III | Loss, *days*, interaction-free measurement | false alarms | alarm only when broken | impossible without losing the train |
| 12 | The mist | III | Superposition as robustness to unknown loss | — | 56 % every day (28 runs) | 85 runs |
| 13 | Tilting cars | IV Inside the train | Tilt (polarization), sorting switch | 100 % A | 100 % B | — |
| 14 | Paint shop | IV | Distinguishability, quantum eraser | 50/50 | 100 % A (η 1) | η 0.50 |
| 15 | Long siding | IV | Arrival time, balancing the interferometer | 50/50 | 100 % B (η 1) | η 0.50 |
| 16 | Twin source | V Twin trains | Pair source, correlated trains | outer couple stranded | every run a couple (η 0.73) | same (honest) |
| 17 | Mirror couples | V | The pair shares one phase, no signalling | 0 couples | every run a couple (η 0.73) | η 0.36 |
| 18 | Beat the classical metro | V | Bell / CHSH | 75 % wins | **85.4 %** wins | max 75 % (proven) |
| 19 | Signal box | V | Feed-forward signals, causality | 50 % home | 100 % home | same (honest) |
| 20 | Teleport | V | Teleportation | 50 % home | 100 % home on both days | 50 % |

The current test levels map onto this as follows: `01-twist-line` → L2, `02-quantum-points` → L3,
`03-dark-port` → L4. `04-entangled-couples` uses the interlock. This campaign doesn't need the interlock
(see Q2), so that level would become a bonus or sandbox level.

### Skill map: where each element is introduced (I), used (U) and combined (C)

| Element / idea | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 | 14 | 15 | 16 | 17 | 18 | 19 | 20 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Station / run / η | I | U | U | U | U | U | U | U | U | U | U | U | U | U | U | U | U | U | U | U |
| Twist | | I | U | U | C | | | | C | U | U | C | | C | U | | C | C | | |
| Quantum points | | | I | U | U | U | C | C | C | U | U | C | | U | U | U | U | U | | C |
| Crossover | | | | | | I | C | U | U | C | | C | | | | | | | | |
| Mid-line station / inspector | | | | | | | | | | I | | | | | | | | | U | C |
| Construction site, days | | | | | | | | | | | I | C | | | | | | | | U |
| Tilt, sorting switch | | | | | | | | | | | | | I | C | | | | | | C |
| Siding (delay) | | | | | | | | | | | | | | | I | | | | | |
| Pair source, couples | | | | | | | | | | | | | | | | I | U | C | U | C |
| Lamps (free choice) | | | | | | | | | | | | | | | | | | I | | |
| Signals (feed-forward) | | | | | | | | | | | | | | | | | | | I | C |

---

## 2. Chapter I: First tracks (one train, two rails)

### L1: First departure
*Teaches:* the Run button, one train = one photon, one run = one shot, a station is a detector, and how η is counted.

```
        depot     c1     c2
  A   ●orange    ───    S:3 ▶
```
* **Player can:** nothing but press Run. No slots, no palette.
* **Goal:** carry 3 passengers.
* **What happens:** 3 runs, 3 passengers, η = 3/3 = 1. The results panel shows "predicted 100 % / measured 100 %".
* **First-time callouts:** Run button → passenger counter → run counter → results panel → the "under the hood"
  circuit button (one rail qubit + one station qubit: `X`, `CX`, `measure`). Then "Next level".
* **Under the hood:** a single-photon source, a waveguide and a detector. Every dispatch is one shot of the circuit.
* **Engine:** exists. The only change is that a level with no slots and no supply must be valid.

### L2: Twist tunnel
*Teaches:* the twist and its dial (tap = +π/4, wraps at 2π), roll = phase, and that a lone train's roll can't be seen.

```
        depot     c1     c2     c3     c4
  A   ●orange    [·]    [·]    [·]    S:3 ▶
```
* **Player can:** place twists (unlimited) and tap to turn them.
* **Goal:** carry 3 passengers **and** arrive *upside down* (roll = ½ turn). This is a tutorial objective
  read from the roll badge.
* **Untouched:** the passengers board; the objective isn't met.
* **Solution:** any set of twists summing to 4 steps (e.g. 2 + 2, or 1 + 3, or 3 + 3 + 6 = 12 ≡ 4). This teaches that twists add up and wrap around.
* **The lesson (end card):** "The station took every passenger *whatever* you did. A train on one track
  shows no roll to any detector. Roll only matters when two ghosts of the same train meet. Next level."
* **Under the hood:** `P(φ)` on a qubit that is certainly 1 is a global phase.
* **Engine:** exists, plus the roll objective check (see Q1).

### L3: Quantum points
*Teaches:* the palette and drag-and-drop, superposition (ghosts, opacity = probability), and that each run's
outcome is random.

```
        depot     c1     c2     c3
  A   ●orange    [¦]    [·]    S:2 ▶
  B              [¦]    [·]    S:2 ▶
```
* **Player can:** place 1 points, any number of twists.
* **Goal:** 2 passengers at A, 2 at B.
* **Untouched:** every train goes to A, so B can never be served. The UI warns before the run: "Stop B can't be reached".
* **Solution:** points at c1 gives 50/50. Expected runs 5.5, **η 0.73** (the best possible here).
* **Wrong tries that teach:** a twist after the points changes the roll of one ghost but not the 50/50 (verified).
  This is the setup for L4.
* **Honest note on the card:** "A coin-flip switch would do exactly as well. Next level it can't."
* **Under the hood:** `XXPlusYYGate(π/2, π/2)` = `RY(π/2)` on the dual-rail pair.
* **Engine:** exists.

### L4: Dark port
*Teaches:* interference. The Mach–Zehnder interferometer, the first deterministic quantum delivery, and
the first time the player beats the classical metro.

```
        depot     c1     c2     c3     c4
  A   ●orange    PTS    [·]    PTS    S:4 ▶
  B              PTS    [·]    PTS    S:0 ▶
```
* **Player can:** place 1 twist (on A or B).
* **Goal:** 4 passengers at A.
* **Untouched:** **100 % to B**, the empty platform. Two coin flips would give 50/50; instead the ghosts meet and
  cancel on A.
* **Solution:** a ½-turn twist on *either* rail gives **100 % A**, η 1. A ¼ turn gives 50/50.
* **Classical metro:** η 0.50 (8 runs). The results screen shows both bars.
* **Hints:** (1) "Watch the two ghosts' rolls where they meet." (2) "Ghosts that meet upside down to each other cancel."
* **Under the hood:** H–Z–H = X. The roll difference became a rail difference.
* **Engine:** exists (`levels/03-dark-port.json`).

### L5: Quarter turn
*Teaches:* that phase is relative, that you can't untwist (only twist on around), that twisting the *other* rail
works too, and the ±i states.

```
        depot     c1     c2     c3     c4     c5
  A   ●orange    PTS    ───    [·]    PTS    S:0 ▶
  B              PTS    T+2    [·]    PTS    S:4 ▶
```
* **Player can:** place 1 twist. The fixed `T+2` is an old tunnel that can't be removed.
* **Goal:** 4 passengers at **B**.
* **Untouched:** 50/50 (the |+i⟩ state; one points can't separate it).
* **Wrong tries:** +2 on B (total ½ turn) gives 100 % A, the wrong side. +4 on B (¾ turn) is still 50/50.
* **Solutions:** **+2 on A** (rolls are now equal), or **+6 on B** (¼ + ¾ = a full turn = nothing). Both give 100 % B, η 1.
* **Classical metro:** η 0.50.
* **Hints:** (1) "Only the *difference* between the ghosts' rolls matters." (2) "Can't undo a twist? Go all the way round."
* **Under the hood:** S† = S³; |±i⟩ need a quarter twist before the points to be told apart.
* **Engine:** exists. Fixed twists are already allowed.

---

## 3. Chapter II: The network (more rails)

### L6: Switchyard
*Teaches:* the crossover and the rule that elements only join neighbouring rails. A breather level.

```
        depot     c1     c2     c3     c4     c5
  A   ●orange    [¦]    ───    ───    [¦]    S:2 ▶
  B              [¦]    [¦]    ───    [¦]    S:0 ▶
  C              ───    [¦]    [¦]    ───    S:0 ▶
  D              ───    ───    [¦]    ───    S:2 ▶
```
Slots: c1 A–B, c2 B–C, c3 C–D, c4 A–B.
* **Player can:** place 1 points and 2 crossovers.
* **Goal:** 2 passengers at A, 2 at D.
* **Untouched:** everything goes to A; D is unreachable.
* **Solution:** points c1 (A–B), cross c2 (B–C), cross c3 (C–D) gives 50 % A / 50 % D, η 0.73.
* **Honest note:** pure routing, a coin could do it. The point is that crossovers carry ghosts across the map.
* **Under the hood:** on a dual-rail pair a crossover *is* the X gate.
* **Engine:** exists.

### L7: Crossed wires
*Teaches:* that swapping two identical ghosts changes nothing, while a crossover before or after an
interferometer relabels its inputs or exits.

```
        depot     c1     c2     c3     c4     c5     c6
  A   ●orange    [¦]    PTS    [¦]    PTS    [¦]    S:4 ▶
  B              [¦]    PTS    [¦]    PTS    [¦]    S:0 ▶
```
* **Player can:** place 1 crossover, and no twists.
* **Goal:** 4 passengers at A.
* **Untouched:** 100 % B (the dark port again).
* **The trap:** a crossover in the middle (c3), which seems like "swap the arms", gives **still 100 % B**.
* **Solutions:** the crossover at c1 (train starts on B) or at c5 (exits swapped) gives 100 % A, η 1.
* **Classical metro:** η 0.50.
* **Hints:** (1) "Look at the two ghosts at c3. Can you tell them apart?" (2) "Change what goes *in* or what comes *out*."
* **Under the hood:** SWAP leaves the symmetric state (|01⟩+|10⟩) unchanged.
* **Engine:** exists.

### L8: Fair shares
*Teaches:* three-way splits, matching the split to the demand, and crossovers as relabelling.

```
        depot     c1     c2     c3     c4
  A   ●orange    [¦]    ───    [¦]    S:1 ▶
  B              [¦]    [¦]    [¦]    S:2 ▶
  C              ───    [¦]    ───    S:1 ▶
```
Slots: c1 A–B, c2 B–C, c3 A–B.
* **Player can:** place 2 points and 1 crossover.
* **Goal:** A 1, **B 2**, C 1.
* **Untouched:** all to A.
* **Tempting build:** points c1 + points c2 gives 50/25/25, the wrong shape (η 0.44).
* **Solution:** points c1, points c2, then cross c3 (A–B) gives **25/50/25**, η 0.57 (the optimum for this demand;
  stars are relative to it).
* **Honest note:** a coin network does the same. Next level it doesn't.
* **Engine:** exists. Needs the η-vs-optimum star display.

### L9: Grand junction
*Teaches:* interference across four paths (a four-mode interferometer), where a *pattern* of rolls picks the exit.
This is the four-way split, seen in full.

```
        depot     c1     c2     c3     c4     c5     c6     c7     c8
  A   ●orange    PTS    ───    PTS    [·]    PTS    ───    PTS    S:4 ▶
  B              PTS    CRS    PTS    [·]    PTS    CRS    PTS    S:0 ▶
  C              ───    CRS    PTS    [·]    PTS    CRS    PTS    S:0 ▶
  D              ───    ───    PTS    [·]    PTS    ───    PTS    S:0 ▶
```
Fixed: c1 points A–B · c2 cross B–C · c3 points A–B and C–D (the train is now 25 % on every rail) · c5 points A–B and C–D ·
c6 cross B–C · c7 points A–B and C–D.
* **Player can:** place 2 twists.
* **Goal:** 4 passengers at A.
* **Untouched:** **100 % D**, all four ghosts reunite on D.
* **Wrong tries:** a single ½ twist anywhere spreads to **25 % on every station**.
* **Solution:** ½ twists on **B and C** (or on A and D) give 100 % A, η 1. (For reference: B needs {B, D} or {A, C};
  C needs {C, D} or {A, B}.)
* **Classical metro:** a coin network reaches A only 25 % of the time, η 0.25.
* **Hints:** (1) "One twist wrecks everything. You need a pattern." (2) "Pair the rails up."
* **Under the hood:** two layers of 50:50 points act as a 4×4 Hadamard-like transform. The roll pattern picks its column.
* **Engine:** exists.

---

## 4. Chapter III: Looking and losing

### L10: Nosy inspector
*Teaches:* that a mid-line station is a which-path detector. *Knowing* where the train is destroys
interference, even if nothing touches it. The ghosts after it are drawn dashed.

```
        depot     c1     c2     c3     c4     c5     c6
  A   ●orange    PTS    ───    [·]    ───    PTS    S:0 ▶
  B              PTS    [¦]    INS    [¦]    PTS    S:4 ▶
  C              ───    [¦]    ───    [¦]    ───    ─── ▶
```
Slots: c2 B–C, c4 B–C, c3 A (a decoy twist slot).
* **Player can:** place 2 crossovers and 1 twist.
* **Goal:** 4 passengers at B.
* **Untouched:** the inspector sees the train half the time, and the final split is **50/50** (η 0.5) instead of 100 % B.
* **Wrong tries:** a twist (the L4 trick) gives still 50/50. Only the first crossover: the ghost is stranded on C (50 % lost to an
  empty exit).
* **Solution:** a **detour**: cross at c2 (B → C), cross back at c4. The inspector never sees the train, so 100 % B, η 1.
* **Hints:** (1) "The inspector doesn't stop the train. Why does it still matter?" (2) "What if there's nothing on B to inspect?"
* **Under the hood:** the station is a `CX` into its own qubit, so the which-path information now lives in that qubit
  and the two ghosts can no longer interfere.
* **Engine:** exists (a station with `passengers: []`). Needs inspector art and the dashed "decohered" ghosts.

### L11: Broken bridge (bomb tester)
*Teaches:* the construction site (loss), **days** (the same map run in several scenarios), the closed station, and
interaction-free measurement (Elitzur–Vaidman).

```
        depot     c1     c2     c3     c4     c5
  A   ●orange    PTS    ───    [·]    PTS    Main  ▶
  B              PTS    BRG    [·]    PTS    Alarm ▶
```
* **Days:** Day 1, the bridge is fine: Main needs 4, and Alarm is **closed** (a train there is a false alarm, a strike).
  Day 2, the bridge is a **construction site**: Main needs 1, and Alarm has 1 repair crew to call.
* **Player can:** place 1 twist. One Run plays both days.
* **Untouched:** on day 1 **every** train rings the Alarm (false alarms), so the level fails.
* **Solution:** a ½ twist. Day 1: 100 % Main, Alarm silent. Day 2: 50 % lost at the site, 25 % Main, **25 % Alarm**
  (6 expected runs).
* **The lesson:** on day 2, every train that rang the Alarm went the *other* way. It detected the broken bridge without
  touching it. A classical train can only find a broken bridge by driving onto it, and it is lost every time.
* **Bonus idea:** with many weak points in a row (quantum Zeno), detection can approach 100 %. That would make a good bonus level.
* **Under the hood:** the site is a `SWAP` into a loss qubit measured at the end (deferred measurement, one circuit).
* **Engine:** new: construction site, days, closed station plus a strike rule.

### L12: The mist (Tomáš's idea)
*Teaches:* superposition as robustness. Spreading the train wider lets more of it survive an unknown blockage
and still reunite. The player builds both the split and the reunion.

```
        depot     c1   c2   c3   c4   c5   c6   c7   c8   c9
  A   ●orange    [¦]  ───  [¦]  ~~~  [·]  [¦]  ───  [¦]  S:0 ▶
  B              [¦]  [¦]  [¦]  ~~~  [·]  [¦]  [¦]  [¦]  S:0 ▶
  C              ───  [¦]  [¦]  ~~~  [·]  [¦]  [¦]  [¦]  S:0 ▶
  D              ───  ───  [¦]  ~~~  [·]  [¦]  ───  [¦]  Harbour (4 per day) ▶
```
Slots: c1 A–B · c2 B–C · c3 A–B, C–D · c5 twists · c6 A–B, C–D · c7 B–C · c8 A–B, C–D.
* **Days:** 4 days. Each day, one hidden track (A, B, C or D, shuffled) has a construction site under the mist.
  It is revealed after the run.
* **Player can:** place 7 points, 3 crossovers and 4 twists.
* **Results by strategy (4 passengers per day; total expected runs over the 4 days):**

  | Build | Harbour per day | Total runs |
  |---|---|---|
  | Route along one track | 100 % on 3 days, **0 %** on 1 day | ∞ (can't finish) |
  | Spread over 2 tracks (points c1, points c6, cross c7, cross c8) | 25 / 25 / 100 / 100 % | 40 |
  | **Spread over 4 tracks** (L9's split at c1–c3, L9's reunion at c6–c8) | **56 % every day** | **28.4** |
  | Classical coin network over 4 tracks | 19 % | 85 |
* **The lesson:** with N tracks and one blocked, the reunion still delivers ((N−1)/N)². The wider the spread, the
  safer the run. This only works because the ghosts recombine coherently.
* **Hints:** (1) "You can't see the blocked track, so don't bet on one." (2) "Level 9 showed how to split in four and reunite."
* **Engine:** construction site + days (from L11), plus the mist overlay.

---

## 5. Chapter IV: Inside the train (one train, more properties)

### L13: Tilting cars
*Teaches:* the **tilt** of the cars, which is the photon's polarization: a second qubit carried by the same train. Also the
**tilter** (tap = +45°) and the **sorting switch**: upright cars stay, flat cars cross to the neighbouring rail.

```
        depot     c1     c2     c3     c4     c5
  A   ●orange    [·]    PBS    [·]    PBS    S:0 ▶
  B              ───    PBS    [·]    PBS    S:4 ▶
```
* **Player can:** place 2 tilters.
* **Goal:** 4 passengers at B.
* **Untouched:** upright cars stay, so 100 % A.
* **The trap:** lay the cars flat at c1. They cross to B at the first switch… and **back to A** at the second.
* **Solutions:** lay the cars flat at c3 on A (one tilter), or flat at c1 and upright again at c3 on B. Either gives 100 % B.
* **Bonus observation:** tilt 45° at c1 splits the train by tilt (upright ghost on A, flat ghost on B). The second switch
  reunites them: **100 % A** again, a tilt interferometer. Between the switches, the rail and the tilt are entangled
  inside one photon.
* **Under the hood:** the sorting switch is a polarizing beam splitter, a deterministic CNOT from tilt to path
  (`CSWAP(tilt, a, b)`). The tilter is a half-wave plate (`RY` on the tilt qubit, controlled by the rail).
* **Engine:** new: a tilt qubit per train, the tilter and the sorting switch, plus car-tilt art.

### L14: Paint shop (quantum eraser)
*Teaches:* that interference needs the two paths to be **indistinguishable**. If anything about the train tells
which way it went, even its own tilt, there's no interference. Make both ways look the same and it comes back.

```
        depot     c1     c2     c3     c4     c5     c6
  A   ●orange    PTS    ───    [·]    [·]    PTS    S:4 ▶
  B              PTS    PNT    ───    [·]    PTS    S:0 ▶
```
`PNT` = paint shop, a fixed tilter that lays every car on B flat. B's tunnel has no slot, so the mark can't be undone there.
* **Player can:** place 1 tilter and 1 twist.
* **Goal:** 4 passengers at A.
* **Untouched:** 50/50.
* **The trap:** the dark-port trick (½ twist) gives **still 50/50**.
* **Solution:** lay A's cars flat too (2 steps at c3), which gives 100 % B (interference is back). Then add a ½ twist, which gives
  **100 % A**, η 1.
* **Bonus observations:** tilting A by −90° (6 steps; the car lies on its *other* side) gives 100 % A with no twist. That
  side is a half-turn roll. Tilting only 45° gives a partial interference of 85/15. Partial marking means partial fringes.
* **Classical metro:** η 0.50.
* **Under the hood:** quantum eraser / which-path marking via polarization.
* **Engine:** tilt (from L13).

### L15: Long siding (balance your interferometer)
*Teaches:* that arrival time is another way to know the path. A long delay on one arm kills interference unless the
other arm is delayed equally. This is the time-bin degree of freedom.

```
        depot     c1     c2     c3     c4     c5
  A   ●orange    PTS    [·]    [·]    PTS    S:0 ▶
  B              PTS    SID2   [·]    PTS    S:4 ▶
```
* **Player can:** place 1 siding (tap to set 1–3 ticks) and 1 twist.
* **Goal:** 4 passengers at B.
* **Untouched:** the ghost on B arrives 2 ticks late and misses its partner, so 50/50.
* **Wrong tries:** a twist gives still 50/50. A siding of 1 or 3 ticks also gives 50/50.
* **Solution:** a **2-tick siding on A**. Both ghosts are late together, so 100 % B, η 1.
* **Classical metro:** η 0.50.
* **Under the hood:** real photonic chips must match arm lengths to within the photon's coherence length. A delay
  long enough to tell the paths apart acts as a which-path record.
* **Engine:** new: a siding with a 2-qubit clock per train (controlled +1 per tick), plus late-ghost animation.

---

## 6. Chapter V: Twin trains (entanglement)

Shared layout: a grey **pump** train runs on rails P/Q. Each **pair source** turns the pump into two trains: pump on
P gives blue on B and teal on C (the *inner* couple); pump on Q gives blue on A and teal on D (the *outer* couple).
Blue owns A/B and teal owns C/D, and the pump disappears at the source.

### L16: Twin source
*Teaches:* the pair source, and couples (partner stations, which already exist) that only board together.

```
        depot     c1     c2     c3     c4
  A              ───    SRC    ───    S (outer couple, with D) ▶
  B              ───    SRC    ───    S (inner couple, with C) ▶
  P   ●pump      [¦]    SRC
  Q              [¦]    SRC
  C              ───    SRC    ───    S (inner couple, with B) ▶
  D              ───    SRC    ───    S (outer couple, with A) ▶
```
* **Player can:** place 1 points (on the pump).
* **Goal:** 2 inner couples, 2 outer couples.
* **Untouched:** the pump always fires source P, so only inner couples travel and the outer ones are stranded.
* **Solution:** points on the pump. Each run is 50 % inner couple, 50 % outer, and every run carries a couple. η 0.73.
* **Honest note:** "A coin choosing which source fires would do the same. Next level shows it can't."
* **Under the hood:** two coherently pumped pair sources give the Bell state (|BC⟩ + |AD⟩)/√2. This is how on-chip
  entangled photons are made, with no interlock needed.
* **Engine:** new: the pump train and the pair-source element (`SWAP(pump, signal)` + `CX(signal, idler)`). It is the only
  element allowed to join rails of different trains.

### L17: Mirror couples
*Teaches:* that the pair has **one shared phase**. A twist on *either* train, or even on the pump before the trains
exist, changes how they pair up. Each train on its own stays 50/50 whatever you do (no signalling).

```
        depot     c1     c2     c3     c4     c5     c6
  A              ───    ───    SRC    [·]    PTS    S (outer, with D) ▶
  B              ───    ───    SRC    [·]    PTS    S (inner, with C) ▶
  P   ●pump      PTS    ───    SRC
  Q              PTS    [·]    SRC
  C              ───    ───    SRC    [·]    PTS    S (inner, with B) ▶
  D              ───    ───    SRC    [·]    PTS    S (outer, with A) ▶
```
* **Player can:** place 1 twist (on Q, A, B, C or D).
* **Goal:** the same couples as L16. Now each train meets points before its platform.
* **Untouched:** trains end on A+C or B+D, so the couples **always** split up (0 couples carried).
* **Solution:** a ½ twist on **any one** of A, B, C, D or Q gives B+C / A+D, so every run carries a couple, η 0.73.
* **Wrong tries:** two ½ twists cancel. A ¼ twist gives 25 % on each combination (half the runs carry a couple).
* **Classical metro:** a coin chooses the source and each points is an independent coin, giving 25 % each and η 0.36.
* **The lesson (results panel):** blue alone is 50/50 in every build, and teal alone too. Only the *pairing* changes,
  so no message can be sent this way.
* **Under the hood:** (Z⊗I)|Φ+⟩ = |Φ−⟩, and the points then turn correlation into anti-correlation.
* **Engine:** pair source (from L16).

### L18: Beat the classical metro (CHSH)
*Teaches:* that entangled trains win a game no classical metro can win more than 75 % of the time. Also free choice (lamps)
and the Bell / CHSH inequality.

```
        depot     c1     c2     c3     c4     c5     c6
  A              ───    SRC    ───    ───    PTS    S top ▶
  B              ───    SRC    [·]    [g]    PTS    S bottom ▶
  P   ●pump      PTS    SRC
  Q              PTS    SRC
  C              ───    SRC    ───    ───    PTS    S top ▶
  D              ───    SRC    [·]    [g]    PTS    S bottom ▶
```
* **Rules:** at the start of each run a referee flips a coin for each train's **lamp** (red/green). Each train sees only
  its own lamp. **Win** if both trains end on the same level (both top or both bottom), *except* when both lamps are
  green; then they must end on different levels.
* **Player can:** for each train, place a base twist `[·]` and a **green twist** `[g]`, which only turns when that train's lamp is
  green.
* **Untouched:** **75 %** wins, exactly the best any classical metro can do (the CHSH bound).
* **Solution:** blue: base 0, green +2 (¼ turn). Teal: base +1 (⅛ turn), green +6 (−¼ turn). This gives
  **85.4 % = cos²(π/8)**, the most quantum physics allows (the Tsirelson bound). 16 equivalent builds were found by brute force.
* **Stars:** ★ ≥ 75 % · ★★ ≥ 80 % · ★★★ 85.4 %. Stars come from the exact probabilities; the run tally shows the
  measured win rate with its error bar (a few hundred runs are needed to see the gap).
* **UI help:** a live "forecast" win meter while editing, so the player can hill-climb.
* **Under the hood:** lamps are quantum coins (`H` on a lamp qubit) and a green twist is `CP(φ)` from the lamp onto the rail.
  The whole run is one circuit.
* **Engine:** new: lamps, the green twist and a win-rule scoreboard.

### L19: Signal box
*Teaches:* **signals**: a station's click can throw a later element (feed-forward). Also causality: a signal can't act
before the train reaches its station.

```
        depot     c1     c2     c3     c4     c5
  A              ───    SRC    S:2    ───    ───  ▶
  B              ───    SRC    S:2    ───    ───  ▶
  P   ●pump      PTS    SRC
  Q              PTS    SRC
  C              ───    SRC    [¦]    [¦]    Home S:4 ▶
  D              ───    SRC    [¦]    [¦]    S:0 ▶
```
* **Player can:** place 1 signal crossover (C–D) and wire it to a blue station.
* **Goal:** teal always reaches Home.
* **Untouched:** teal is 50/50, η 0.5.
* **The trap:** placing it at c3 is refused, with the message "the signal can't arrive before blue reaches its station". Wiring from blue's B station
  sends teal Home **0 %**.
* **Solution:** crossover at c4, wired from **blue's A station** (blue on A means teal is on D). Teal goes Home 100 %, η 1.
* **Honest note:** once blue is seen, a coin-chosen source could do this too. Signals are the tool; the next level is the payoff.
* **Under the hood:** the classically controlled gate is replaced by a gate controlled by the station's qubit
  (deferred measurement), so there is still one circuit and no mid-circuit measurement.
* **Engine:** new: the signal element and wiring UI (`CSWAP` / `CP` controlled by a station qubit).

### L20: Teleport
*Teaches:* quantum teleportation. The *tilt* of blue's cargo moves onto teal's *rail* using one entangled pair and two
signals, and blue never goes to teal. Everything is linear optics plus feed-forward.

```
        depot     c1   c2   c3    c4   c5   c6   c7   c8   c9   c10  c11
  A1             ───  ───  ───   ───  ───  PBS  S    ───  ───  ───  ▶
  A              ───  SRC  LOAD  PBS  [·]  PBS  S    ───  ───  ───  ▶
  B              ───  SRC  LOAD  PBS  [·]  PBS  S    ───  ───  ───  ▶
  B1             ───  ───  ───   ───  ───  PBS  S    ───  ───  ───  ▶
  P   ●pump      PTS  SRC
  Q              PTS  SRC
  C              ───  SRC  ───   ───  ───  ───  ───  [¦]  ───  DEC  Home ▶
  D              ───  SRC  ───   ───  ───  ───  ───  [¦]  [·]  DEC  S:0 ▶
```
* **Fixed:** c3 `LOAD` (the day's cargo tilt on blue: day 1 upright, day 2 tilted 45°) · c4 sorting switch A–B · c6 readout
  switches (A1–A, B–B1: flat cars step outward) · c7 blue stations A1, A, B, B1 · c10 teal's decoder (day 1: nothing,
  day 2: points C–D).
* **Player can:** place 2 tilters (c5), 1 signal crossover (c8) and 1 signal ½ twist (c9 on D). Each signal can be wired
  to several stations and fires if any of them saw blue.
* **Goal:** teal reaches Home on **both** days.
* **Untouched:** 50 % Home on both days.
* **Solution:** tilters at 45° (1 step) on both A and B. Crossover wired from **A1 and A** ("blue ended on the A side").
  Twist wired from **A1 and B1** ("blue's cars arrived flat"). Result: **100 % Home on both days.**
* **Partial builds that teach:** crossover only gives day 1 100 % / day 2 50 %. Twist only gives day 1 50 % / day 2 100 %. Without
  the tilters, day 2 is 50 %. Day 1 tests one signal and day 2 tests the other.
* **The lesson:** the two signals are the two classical bits of teleportation (which rail, which tilt). The cargo state
  is gone from blue afterwards (no cloning).
* **Under the hood:** this is the Boschi–Popescu scheme (Rome, 1998): path entanglement teleports polarization, with the
  sorting switch as the CNOT of the Bell measurement. It runs on 15 qubits: 8 rails + 1 tilt + 6 stations.
* **Engine:** tilt + pair source + signals + days (all from earlier levels).

---

## 4. New mechanics needed

| Feature | Qiskit recipe | Levels | Cost guess |
|---|---|---|---|
| Level with no slots, a tutorial roll objective | none | 1, 2 | small |
| "Station can't be reached" warning (p = 0) | from the statevector | 3+ | small |
| Star display (η vs optimum, classical bar) | exact E[runs] from p (DP, already prototyped for this doc) | all | small |
| Inspector art + dashed decohered ghosts | station as now | 10 | small |
| Construction site (loss) | `SWAP(rail, loss_q)`, loss measured at the end | 11, 12 | small |
| **Days** (scenarios: fixed elements differ per day) | one circuit per day, all in one job | 11, 12, 20 | medium |
| Closed station + strikes | scoring | 11 | small |
| Mist overlay | none (art) | 12 | small |
| Tilt qubit per train, tilter, sorting switch, load | `CRY(k·π/2)` rail→tilt, `CSWAP(tilt, a, b)`, `RY` | 13, 14, 20 | medium–large (car-tilt art, reference sim gets (rail, tilt) configurations) |
| Siding (1–3 ticks) | 2-qubit clock per train, controlled +1 per tick | 15 | medium |
| Pump train + pair source | `SWAP(pump, signal)`, `CX(signal, idler)` | 16–20 | medium (the format needs trains born at a source) |
| Lamps + green twist | `H(lamp)`, `CP(φ, lamp, rail)` | 18 | medium (scoreboard, win rule) |
| Signals + wiring | `CSWAP` / `CP` controlled by station qubits | 19, 20 | medium (wiring UI) |

**Qubit budget (max):** L20 uses 15, L18 uses 12, L12 uses 9, and everything else uses 8 or fewer. Check against the IonQ simulator cap.

**Possible build order by cost** (so we always have a playable campaign):
1. L1–L10: engine already done; level files plus small UI.
2. Construction site + days: L11, L12.
3. Pair source: L16, L17. Then lamps: L18. That gives **15 levels**.
4. Signals: L19. Tilt: L13, L14, L20. Siding: L15.

---

## 5. Open questions for discussion

1. **L2 objective.** It is the only place where a lone train's roll is "checked". Keep it as a clearly labelled controls
   tutorial, or drop the objective and let L2 be "play with the dial, see that nothing changes"?
2. **Interlock.** This campaign is all-photonic (linear optics + detectors + feed-forward), with no interlock needed even for
   teleportation. Do we drop the interlock, or keep `04-entangled-couples` as a bonus "not quite photonic" level?
3. **Days.** Does one Run play all days in sequence (one job, as proposed), or does the player pick a day tab?
4. **Signals UI.** Drag a wire from a station to an element, or colour-coded signal tokens (a red station throws red
   elements)?
5. **L18 lamps.** Quantum coins in the circuit (proposed, one circuit) or classical random scenarios (4 circuits)?
6. **Star thresholds** (the PLAN placeholder: ★ beat classical, ★★ ≥ 90 %, ★★★ ≥ 98 % of optimum). These don't fit L3/L6/L8/16/19,
   where classical = optimum. Proposal: in those levels ★★★ = optimum, with no classical star.
7. **Redundancy.** If 20 is too many: L6 could fold into L8, and L19 into L20 (at the cost of a harder finale).
8. **Tilt sign.** A car lying on its left vs right side differs by a half-turn roll (L14 bonus). Show it, or hide it by allowing
   only +90°?
9. **L12 scoring.** Total expected runs over all days (proposed: it naturally rewards the 4-track spread). Or worst day?
10. **Bonus levels later:** quantum Zeno bomb tester, unbalanced interferometer with tunable points, Franson time-bin
    pair, Hong–Ou–Mandel (needs a two-photons-per-rail encoding).
