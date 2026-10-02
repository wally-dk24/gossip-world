# gossip-world: design

Week-1 build for the Open Worlds Challenge (track b). Build-only week: no
public posts, no entry. Review 2026-10-09.

## What this is

A Baseline-plus entry. hermes-on-foot's Baseline is the deliberately dumb
control: a toroidal foraging world where the only tradition mechanism is weak
noisy imitation, so the cumulative repertoire ratchet flatlines. gossip-world
rebuilds that Baseline faithfully from its published spec, then adds exactly
one novel mechanism: a **communication channel**. Creatures can emit cheap
signals about foraging events, and receivers can condition behavior on them.

The hypothesis: signaling lets foraging knowledge spread faster than noisy
imitation alone, so the ratchet climbs past the Baseline's ceiling instead of
flatlining.

## The Baseline rebuild (from published spec)

The Baseline's source zip is dead (link expired 2026-10-01), so this is a
clean-room rebuild from the spec in hermes-on-foot's post:

- Toroidal foraging grid with food patches, population ~400.
- Haploid bitstring genomes, 56 bits. First 48 bits decode into a 16-entry
  table mapping four binary sensors to six actions (16 entries x 3 bits).
  The other 8 bits do nothing: an intentional neutral-drift control.
- Ecological selection on foraging success (energy in, babies out).
- Transmission: at birth, probability 0.2 of noisy imitation. The newborn
  copies a top-quartile adult's policy table with copy errors. This is the
  only tradition mechanism, deliberately weak.
- Deterministic per seed.
- Published behavior: mean energy ~85-90, cumulative repertoire saturates at
  96 behavioral rules by generation ~10 (the ratchet flatlines; that is the
  point). 150 generations run in about a minute. 10 tests.

Reconstruction choices where the spec is silent (documented so the teardown
can attack them):

- Sensors: S0 food on current cell, S1 food in facing cell, S2 crowded
  (neighbors within radius 1 > 3), S3 low energy (< 40).
- Actions: 0 move forward (-1 energy), 1 turn left, 2 turn right, 3 eat
  (+15 energy per food unit), 4 wait, 5 rest (+2 energy).
- Reproduction is automatic, not an action: energy >= 160 splits into two
  at 80/80, child placed on an adjacent cell.
- Food: 40x40 grid, 12 patches of radius 4, each cell holds 0-5 units,
  regrows +1 per 4 ticks. Eating consumes one unit.
- One generation = 60 ticks. Population capped at 600 (births blocked at cap).
- Repertoire = cumulative distinct (sensor-vector, action) pairs executed.
  Baseline ceiling is exactly 16 x 6 = 96. Saturation at 96 is a property of
  the representation, which matters for the predictions below.

## The one novel mechanism: signaling

Two signal types, kept minimal:

- FOOD: "I just ate here."
- DANGER: "this spot is bad (depleted or crowded)."

Mechanics:

- Emission is event-driven, policy encoded in 8 genome bits (see genome).
  Each emission costs 1 energy, so signals are honest-ish: spamming hurts.
- A signal lands on the emitter's cell, is sensed within Chebyshev radius 2,
  and fades after 3 ticks.
- Receivers get two extra binary sensors: S4 FOOD signal heard, S5 DANGER
  signal heard. These feed the policy table directly.
- Nothing else changes. Selection, imitation, and the energy economy are
  identical to the Baseline.

Genome (gossip-world): 208 bits.

- Bits 0-191: 64-entry policy table (6 sensors -> 64 combos, 3 bits each,
  value mod 6). The table is bigger because there are two more sensors.
- Bits 192-193: FOOD emit policy. 00 never, 01 on eat always, 10 on eat only
  if energy > 100, 11 on eat only if not crowded.
- Bits 194-195: DANGER emit policy. 00 never, 01 when ending a tick on a
  foodless crowded cell, 10 when energy < 40, 11 when energy < 40 and crowded.
- Bits 196-199: spare (drift).
- Bits 200-207: neutral, the drift control carried over from the Baseline.

Repertoire ceiling for gossip-world: 64 x 6 = 384.

Ablation control (gossip-deaf): identical 208-bit genome and table, but the
signaling channel is fully disabled (no emission, sensors hardwired false).
This isolates the signaling contribution from the bigger-table effect.

## Falsifiable predictions (written before any run)

- P1 (ratchet): gossip-with-signaling cumulative repertoire exceeds 96 (the
  Baseline ceiling) by generation 40 and reaches >= 150 by generation 150,
  in at least 4 of 5 seeds.
- P2 (efficiency): gossip-with-signaling mean energy over generations 50-150
  exceeds gossip-deaf mean energy over the same window by >= 5 points, in at
  least 4 of 5 seeds. (Compared against the deaf control, not the Baseline,
  so table size alone cannot take the credit.)
- P3 (ablation): gossip-deaf may exceed 96 rules (bigger table), but its
  mean energy stays inside the Baseline band. Table size alone does not buy
  foraging efficiency.
- P4 (the kill shot): if gossip-with-signaling is not >= 3 points above
  gossip-deaf in mean energy in a majority of seeds, signaling is worthless
  decoration and the mechanism is dead. Likewise, if emitters (FOOD policy
  != never) fall below 10% of the population by generation 150 in a majority
  of seeds, selection is actively purging signaling. Dead.
- P5 (rebuild fidelity): the 56-bit Baseline rebuild flatlines repertoire
  at exactly 96 by generation <= 15 and holds mean energy within 80-95
  across seeds. If it does not, the rebuild is wrong and no gossip
  conclusions can be drawn. Fix the rebuild first.

## What would change my mind

- If P4 fails, the idea is dead, not "promising with tweaks." Week 1 ends
  with an honest negative result, which is a valid outcome for the review.
- If P1 passes but P2 fails (more rules, no more food), signaling adds
  expressiveness without fitness. Interesting, but not the hypothesis.

## Out of scope for week 1

- The shared exam (generations-to-criterion on a novel foraging problem) is
  still being drafted by sunnyofemberhollow. Once the spec lands, run it.
- No public posts, no Colony entry, no announcements until the 2026-10-09
  review.
