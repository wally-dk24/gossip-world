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
  point). 150 generations run in about a minute. 25 tests.

Reconstruction choices where the spec is silent (documented so the teardown
can attack them):

- Sensors: S0 food on current cell, S1 food in facing cell, S2 crowded
  (neighbors within radius 1 > 3), S3 low energy (< 40).
- Actions: 0 move forward (-1 energy), 1 turn left, 2 turn right, 3 eat
  (+15 energy per food unit), 4 wait, 5 rest (+2 energy).
- Reproduction is automatic, not an action: energy >= 160 splits into two
  at 80/80, child placed on an adjacent cell.
- Food: 40x40 grid, 10 patches of radius 4, each cell holds 0-5 units,
  regrows +1 per 6 ticks. Eating consumes one unit.
- One generation = 60 ticks. Population capped at 600 via culling the
  weakest when over cap (carrying capacity through competition; keeps
  turnover and selection operating at the top end).
- Energy economy (tuned so the rebuild matches the published signature):
  basal metabolism -3.5/tick, eat +15 per food unit, move -1, rest +2,
  per-creature energy cap 200 (storage limit; hoarding is wasted).
  Reproduction at >= 160 splits 80/80.
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
  at exactly 96 by generation <= 15 and holds mean energy within 75-105
  across seeds (the published 85-90 is a typical-seed mean; real seeds vary).
  If it does not, the rebuild is wrong and no gossip conclusions can be
  drawn. Fix the rebuild first.

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

---

# Follow-up experiments (2026-10-02)

Week-1 result: the FOOD/DANGER signaling mechanism is DEAD by P4 (0/5
seeds; signaling a net fitness cost). Failure analysis in RESULTS.md:

1. Perverse information: FOOD signals marked just-depleted cells.
2. Search-space explosion: 56 -> 208 bits, 16 -> 64-entry table.
3. Emission cost was pure deadweight.

The harness (`run.py --compare`) is reused. Experiments run in order;
STOP at the first PASS (a pass means advancing to packaging, not piling on
more mechanisms).

## Experiment A: patch-direction signals

Change of signal *semantics*; architecture identical to gossip (208-bit
genome, 64-entry table, 6 sensors). This isolates semantics as the single
changed variable.

- The signal encodes the direction of the nearest known food from the
  emitter's position: N/E/S/W in 2 bits (0=N, 1=E, 2=S, 3=W, matching the
  facing convention).
- Emission happens on *arrival* at a food cell (ACT_FORWARD steps onto a
  cell with food > 0), *before* any depletion. The emitter scans Chebyshev
  radius 4 (excluding its own cell) for the food cell with the most units
  (ties: nearest, then fixed scan order) and emits the dominant-axis
  direction toward it. If no other food is in radius, emission is
  suppressed (nothing worth sharing; "food here" was the old perverse
  signal).
- Emission policy reuses bits 192-193: 00 never, 01 always on arrival,
  10 only if energy > 100, 11 only if not crowded. Energy cost stays 1
  (same honesty pressure as week 1).
- DANGER is dropped for this experiment: one mechanism, clean test.
  Bits 194-195 become spare drift (masked as neutral).
- Receiver sensors: S4 = "direction signal heard" (any, radius 2, TTL 3,
  unchanged channel physics), S5 = "heard direction agrees with my
  facing". The table can discover "signal ahead -> move forward" and
  "signal elsewhere -> turn" without decoding N/E/S/W into table entries.
  This keeps 6 sensors / 64 entries: the architecture is byte-identical
  to gossip, only the meaning changed.
- Ablation: gossip-dir-deaf, same genome/table, channel fully disabled,
  sensors hardwired false.

Why this might work where week 1 failed: the old signal said "food was
here (now partially eaten)" — unactionable. The new signal says "food is
that way" — it maps directly onto move/turn, a much shorter causal chain
for the table to discover. Arrival-time emission means the food is still
there when receivers arrive (regrow is slow; receivers are within 2
cells).

### Predictions for Experiment A (written before any run)

- PA1 (efficiency): gossip-dir mean energy over generations 50-150
  exceeds gossip-dir-deaf over the same window by >= 5 points, in at
  least 4 of 5 seeds.
- PA2 (kill shot): if gossip-dir is not >= 3 points above gossip-dir-deaf
  in mean energy in a majority of seeds, direction signaling is dead too.
  If emitter fraction (bits 192-193 != never) falls below 10% by gen 150
  in a majority of seeds, selection is purging it. Dead.
- PA3 (sanity): the 56-bit baseline rebuild still flatlines repertoire at
  exactly 96 by generation <= 15 (re-verified; the lab has not drifted).
- PA4 (channel check): live direction signals > 0 in more than half of
  generations 50-150, in a majority of seeds. If the channel is vestigial,
  any energy result is uninterpretable.

Seeds for Experiment A: 6,7,8,9,10 (fresh seeds; tests generalization,
not seed-specific luck).

---

# Round 2: hardened controls (2026-10-02)

An external code review of the week-1 result found the "DEAD" verdict
rests on confounded controls. This round does not add mechanisms. It
decomposes the week-1 energy gap (gossip 1.5-11.5 points below deaf)
into: signal information value, emission-cost masking, and bigger-table
cost. The original RESULTS.md verdict stands untouched; new results are
appended alongside it.

## Bugs fixed before any new run (all real, all with regression tests)

1. Newborns acted on their birth tick (`_spawn` appended during the
   `step_tick` loop, and `_cell_pop` was stale). The loop now iterates
   over a snapshot; newborns wait one tick.
2. One signal per cell: FOOD overwrote DANGER and vice versa. Signals
   are now per-cell dicts `{type: ttl}`; both types coexist. Note:
   `signals_live` now counts live signal *instances*, not cells.
3. Docs mismatched code (12 vs 10 patches, regrow every 4 vs 6 ticks,
   stale test count). Docs now match the code, which is what reproduces
   the published P5 signature.
4. P5 (and P6) printouts crashed when the history was short
   (`f"{eb:.1f}"` with `eb is None`). Safe formatting now.
5. `_pick_model` re-sorted the whole population per birth and let
   newborns count as adults. A top-quartile pool is now built once per
   tick from tick-start creatures only.

## New metrics (mean energy is a weak fitness proxy)

Every generation now records, alongside the old fields: `births`,
`total_energy`, and retention-based repertoire measures. The old
repertoire counts visited (sensor, action) combos; the new measures ask
whether the population has *settled*:

- `row_consensus`: mean over table rows of the population's action
  agreement per row (fraction sharing the row's most common action).
- `rows_settled`: rows with agreement >= 0.8.
- `row_persistence`: fraction of rows whose consensus action is unchanged
  from the previous generation (None at gen 1).

## H2: the unselected-rows hypothesis (hypothesis, not fact)

Hearing a signal routes a creature to table rows with little selection
history, so its action there is near-random. Under H2 the week-1 cost
is not "perverse information" but routing: the 64-entry table spreads
selection thin over rows the deaf control never visits. H2 predicts
PB4/PB5 below. It is written here as a prediction to be tested, not an
adopted explanation.

## The new arms

- **gossip-noise**: 208-bit genome, 64-entry table, never emits. S4/S5
  fire randomly at the marginal hearing rates measured in real gossip
  runs (p_food, p_danger from the calibration pilot below; independent
  per-sensor draws; no emission cost). gossip vs gossip-noise isolates
  signal INFORMATION (same table, same routing, correlated vs random
  cues). gossip-noise vs gossip-deaf measures the bigger-table cost.
  Caveat, stated plainly: this loses the spatial clustering of real
  signals (bursty vs uniform), so it is a slightly generous control.
- **gossip-free**: real gossip signals with emission cost set to zero.
- **gossip-imitable**: real gossip, but noisy imitation also copies the
  emit-policy bits 192-195 from the model (with copy errors). Tests
  whether the tradition mechanism can spread signaling at all. Run LAST
  as its own arm: it changes the mechanism, not the measurement.

## Predictions PB1-PB6 (written before the 20-seed comparison runs)

Seeds 1-20, seed-paired across baseline, gossip-deaf, gossip,
gossip-noise, gossip-free. Window: generations 50-150. Two-sided sign
tests on paired differences.

- PB1 (information value): if |mean E_gossip - E_noise| <= 2 points, the
  week-1 gap comes from the bigger table, not the signal: signal
  information content is ~0.
- PB2 (table cost): if mean(E_noise - E_deaf) < -2, the 64-entry table
  carries a real cost (mutation load and/or H2 routing). If
  |mean(E_noise - E_deaf)| <= 2, the table is costless and the week-1
  gap was the signal channel itself.
- PB3 (cost masking): if mean(E_free - E_noise) > 2, the signal
  information has positive value that the 1-energy emission cost
  masked. If |mean(E_free - E_noise)| <= 2, the information is worthless
  even when free.
- PB4 (H2, consensus): mean row_consensus at gen 150 in gossip-deaf
  exceeds gossip-noise by >= 0.10 (deaf's reachable set is 16 rows, so
  agreement can concentrate; noise spreads creatures over all 64).
- PB5 (H2, retention): mean row_persistence in gossip-deaf exceeds
  gossip-noise by > 0.05 (noise-routed rows churn).
- PB6 (sanity): P5 still holds on the fixed engine in >= 80% of the 20
  seeds (repertoire flatlines at exactly 96 by gen <= 15, energy
  75-105). If not, the lab drifted and nothing downstream means
  anything.

## Prediction PI1 (gossip-imitable, pre-registered before its runs)

- PI1: if emitter_frac at gen 150 in gossip-imitable exceeds gossip by
  > 0.15 in a majority of seeds, imitation can carry the emit policy
  and the tradition mechanism is repaired. Energy is reported as
  secondary; this arm tests transmission, not fitness.

## Calibration pilot

p_food and p_danger for gossip-noise are the mean marginal hearing
rates over generations 50-150 of a 5-seed gossip pilot (seeds 1-5) on
the fixed engine. Values: p_food = TBD, p_danger = TBD.
