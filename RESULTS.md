# gossip-world: week-1 results

5 seeds x 3 modes x 150 generations, seed-paired (same seed = same initial
randomness across modes). Raw histories in results_*.json. Verdicts from
`python3 run.py --compare`.

## Prediction scorecard

| ID | Prediction | Result |
|----|------------|--------|
| P1 | gossip repertoire > 96 by gen 40, >= 150 by gen 150, 4/5 seeds | **5/5 PASS** (372-384) |
| P2 | gossip energy beats gossip-deaf by >= 5 (gens 50-150), 4/5 seeds | **0/5 FAIL** (gossip 1.5-11.5 pts *lower*) |
| P3 | deaf energy stays in 75-105 band | **5/5 PASS** |
| P4 | kill shot: energy edge >= 3 in majority of seeds, else DEAD | **DEAD** (0/5) |
| P5 | baseline rebuild: flatline at 96 by gen <= 15, energy 75-105 | **5/5 PASS** |

## What actually happened

**The baseline rebuild is faithful.** All 5 seeds flatline repertoire at
exactly 96 rules within 15 generations (most by gen 6), mean energy stable
in the 85-101 band, populations a few hundred. The published signature
reproduces. P5 passing means the gossip conclusions below rest on a solid
control.

**The ablation is clean.** gossip-deaf (208-bit genomes, signaling disabled)
flatlines at exactly 96 like the baseline and holds energy in the 90-98
band. With the signal sensors hardwired false, only 16 of 64 table entries
are reachable, so deaf is effectively a 208-bit baseline. Bigger genomes
alone buy nothing. P3 passing means any gossip/deaf difference is the
signaling channel, not table size.

**Signaling is a net cost.** This is the headline. Across all 5 seeds,
gossip-world forages *worse* than its own deaf control:

- seed 1: gossip 79.2 vs deaf 90.7 (diff -11.5)
- seed 2: gossip 88.4 vs deaf 97.9 (diff -9.5)
- seed 3: gossip 84.7 vs deaf 95.8 (diff -11.1)
- seed 4: gossip 88.7 vs deaf 90.2 (diff -1.5)
- seed 5: gossip 89.3 vs deaf 96.7 (diff -7.4)

**The repertoire result is real but hollow.** Gossip reaches 372-384
distinct rules (of 384 possible) vs the 96 ceiling. P1 passes dramatically.
But per the pre-registered branch in DESIGN.md: P1 passes while P2 fails,
so signaling adds expressiveness without fitness. The extra "rules" are
creatures reacting to signal noise through a 4x larger table, not
transmitted foraging knowledge. A bigger rule count is not a ratchet.

**Emitters are not consistently purged, which makes it worse.** Emitter
fractions at gen 150: 0.02, 0.62, 0.15, 0.09, 0.96. In seed 5, signaling
fixed at 96% of the population and the channel stayed active (30 live
signals at gen 150) — and the population *still* foraged 7.4 points worse
than deaf. Selection does not reliably kill signaling, but it never pays
for itself. The 1-energy emission cost is a deadweight loss; the
information (a FOOD signal marks a cell that was just partially eaten)
is too weak and too local to cover it.

## Why it failed (my read)

1. **Discovery problem.** Useful signal-response requires co-evolved table
   entries ("if FOOD heard and no food here, move toward it") in a 192-bit
   table. 150 generations is not enough search for that joint discovery.
2. **Perverse information.** A FOOD signal marks a cell with *less* food
   than before the emitter ate. The honest signal would be patch direction,
   not "I ate here."
3. **Noise.** With most creatures emitting on every eat, receivers swim in
   signals. The channel never becomes a reliable cue.

## Honest assessment for the 2026-10-09 review

The hypothesis as designed is dead, by the pre-registered kill criterion.
This is not "promising with tweaks" — DESIGN.md said dead means dead, and
I am holding to that.

What week 1 *did* produce, and it matters:

- A faithful, tested Baseline rebuild (13 tests green, deterministic per
  seed) that the challenge currently cannot offer, since the original
  source zip is dead.
- A seed-paired experiment harness (P1-P5) reusable for any future
  mechanism. The next idea can be tested in an afternoon.
- A clean negative result with a mechanism-level explanation, which is
  exactly what the challenge's falsifiability norm asks for.

Whether to continue is Master's call. If we do, the honest next bets are
narrower: a small dedicated signal-response module instead of a 4x table,
or an information-richer signal (patch direction, not depletion marks).
If we do not, the week still bought a working lab and an honest answer.

---

# Round 2: hardened controls (2026-10-02)

The week-1 verdict above stands untouched. An external review found it
rested on confounded controls, so this round decomposes the gap instead
of re-litigating the verdict. Five bugs were fixed first (see DESIGN.md;
25 tests green), P5 was re-verified on the fixed engine (5/5 PASS), and
predictions PB1-PB6 were pre-registered before the comparison runs.

## Battery

20 seeds x 5 arms x 150 generations, seed-paired. Arms: baseline,
gossip-deaf, gossip (original mechanism), gossip-noise (S4/S5 fire
randomly at calibrated marginal rates p_food=0.3685, p_danger=0.3809, no
emissions), gossip-free (real signals, zero emission cost). Raw histories
in results_C_*.json (not committed; on disk).

Per-arm means over seeds, generations 50-150 (row metrics at gen 150):

| arm         | E    | pop | births/gen | Etot  | rep@150 | consensus | settled |
|-------------|------|-----|------------|-------|---------|-----------|---------|
| baseline    | 94.0 | 466 | 167.5      | 44169 | 96      | 0.84      | 11.0    |
| gossip-deaf | 94.2 | 476 | 172.2      | 45069 | 96      | 0.83      | 43.4    |
| gossip      | 78.5 | 196 | 71.2       | 17000 | 358     | 0.76      | 32.5    |
| gossip-noise| 89.2 | 314 | 91.4       | 28070 | 383     | 0.81      | 40.4    |
| gossip-free | 80.7 | 234 | 79.8       | 20300 | 361     | 0.77      | 33.4    |

## Prediction scorecard (pre-registered)

| ID  | Prediction | Result |
|-----|------------|--------|
| PB1 | \|E_gossip - E_noise\| <= 2 (signal info ~ 0) | **FAIL** (\|-10.66\|; 3/20 seeds positive, sign p=0.003) |
| PB2 | E_noise - E_deaf < -2 (table is costly) | **PASS** (-5.04; 2/20 positive, sign p=0.0004) |
| PB3 | E_free - E_noise > 2 (cost masked info) | **FAIL** (-8.53; 5/20 positive, sign p=0.041) |
| PB4 | consensus(deaf) - consensus(noise) >= 0.10 (H2) | **FAIL** (+0.02) |
| PB5 | persistence(deaf) - persistence(noise) > 0.05 (H2) | **FAIL** (+0.01) |
| PB6 | P5 holds on fixed engine (>= 80% of seeds) | **PASS** (17/20; 3 marginal misses: seed 6 peaked at rep 95, seeds 11/20 flatlined at 96 but at gens 18/22) |

Week-1 gap replication: gossip - deaf = -15.70 mean over 20 seeds
(0/20 positive, sign p<0.0001). The negative result replicates and is
larger than week 1's -1.5 to -11.5.

## Decomposition of the gap

gossip - deaf = (gossip - noise) + (noise - deaf) = -10.66 + -5.04.

- **Bigger-table cost: ~5 points (PB2 PASS).** gossip-noise vs
  gossip-deaf isolates it: same 64-entry table, random vs no signal
  routing. No extinctions in either arm, so this is clean. Mechanism
  uncertain: PB4/PB5 did not support the unselected-rows hypothesis
  (H2) in its predicted form, though the metrics may be insensitive
  (imitation homogenizes even unvisited rows, so consensus cannot
  discriminate visited from unvisited). The remaining candidate is
  mutation load: 192 bits under selection vs 48 at the same per-bit
  rate.
- **Signal channel: ~10.7 points (PB1 FAIL).** gossip vs gossip-noise
  isolates information (same table, same routing, correlated vs random
  cues). The signal is not neutral; it is actively harmful.
- **Cost masking: no (PB3 FAIL).** gossip-free (real signals, zero
  cost) is 8.5 points WORSE than noise. The information is worthless
  even when free; if anything it is perverse (FOOD marks depletion,
  DANGER saturates).

## The extinction finding (not pre-registered; reported transparently)

On 5/20 seeds (7, 11, 12, 13, 14) the gossip arm collapses to ≤7
creatures by generation ~3 and never recovers (a 2-creature limit
cycle). gossip-free collapses on 2/20 (seeds 7, 13). gossip-noise,
gossip-deaf, and baseline: 0/20. The original pre-fix engine also
collapses on seeds 12 and 13, so this instability is a property of the
mechanism, not an artifact of the bug fixes (the per-cell signal dict
fix shifts more seeds across the knife-edge, but the knife-edge is
pre-existing). Mechanism: DANGER is emitted every tick by most
creatures; saturation routes everyone to unselected rows; the
population starves before selection can act.

Viable-only subset (seeds where both arms keep pop >= 50; post-hoc,
reported alongside the pre-registered full sample):

- gossip - noise: -3.09 (3/15 positive, p=0.035) — still significantly
  harmful conditional on survival.
- noise - deaf: -5.04 (2/20, p=0.0004) — unchanged, extinction-free.
- free - noise: -5.93 (5/18, p=0.096) — harmful but not significant.
- gossip - deaf: -8.16 (0/15, p=0.0001).

Conditional on survival, the table (~5 pts, 62%) outweighs the signal
(~3 pts, 38%). Unconditionally, the signal adds a 25% extinction risk
on top.

## Verdict

Signaling is dead, more decisively than week 1. The decomposition
closes every escape hatch the review opened: the gap is not mutation
load alone (the signal channel is independently harmful, PB1), not
emission cost alone (free signals are still worse than noise, PB3),
and not an artifact of confounded controls (the battery isolates each
component with seed-paired sign tests at p<0.05 or better). The
mechanism also carries a 25% extinction risk. There is no version of
"but the information might still be valuable" left standing: random
noise beats the real signal.

## gossip-imitable (separate arm, run last)

20 seeds x 150 generations. PI1 pre-registered: emitter_frac@150 in
gossip-imitable exceeds gossip by > 0.15 in a majority of seeds.

- PI1: **FAIL** (7/20 seeds). Copying the emit-policy bits via
  imitation does not systematically spread signaling; emitter
  fractions vary 0.00-1.00 in both arms with no consistent direction.
- Energy: imitable - gossip = +2.91 mean (10/19 positive, sign p=1.0):
  no difference.
- Collapse rate: 5/20 in both arms (different seeds: imitable
  collapses on 4, 7, 12, 14, 15).

The review's transmission flaw (imitation could not copy bits 192-195)
is not the binding constraint. Even when imitation CAN copy the emit
policy, signaling does not spread — because there is nothing worth
transmitting. Selection does not favor a harmful trait regardless of
how faithfully it is copied. The hypothesis fails at the fitness
level, not just the transmission level.
