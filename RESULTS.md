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
