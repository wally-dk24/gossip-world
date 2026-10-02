"""Tests for gossip-world. Stdlib unittest, no dependencies.

Run: python -m unittest test_world -v
"""

import unittest

import world
from world import (World, BASELINE, GOSSIP, GOSSIP_DEAF, GOSSIP_DIR,
                   GOSSIP_DIR_DEAF, Config,
                   decode_action, get_bits, mutate, random_genome,
                   ACT_EAT, ACT_FORWARD, SIG_FOOD, SIG_DANGER, SIG_TTL,
                   DANGER_POL_BITS)


def tiny_config(base):
    """A fast config for tests: small grid, few creatures, few ticks."""
    c = Config(base.name, base.genome_bits, base.table_bits, base.n_sensors,
               base.signals_enabled,
               grid_w=12, grid_h=12, n_patches=3, patch_radius=2,
               init_pop=40, pop_cap=80, ticks_per_gen=10,
               neutral_offset=base.neutral_offset,
               neutral_width=base.neutral_width,
               signal_mode=base.signal_mode)
    return c


class TestGenome(unittest.TestCase):
    def test_decode_range(self):
        # every possible 3-bit entry value decodes to a valid action
        for entry_bits in range(8):
            genome = entry_bits  # entry 0 holds the value
            self.assertIn(decode_action(genome, 0), range(6))

    def test_decode_all_entries(self):
        rng = __import__("random").Random(0)
        g = random_genome(rng, 48)
        for entry in range(16):
            self.assertIn(decode_action(g, entry), range(6))

    def test_neutral_bits_do_not_change_behavior(self):
        # two genomes differing only in the neutral tail decode identically
        # and drive identical worlds
        w1 = World(tiny_config(BASELINE), seed=7)
        w2 = World(tiny_config(BASELINE), seed=7)
        flip = 1 << 50  # inside the neutral 8 bits
        for a, b in zip(w1.creatures, w2.creatures):
            b.genome = a.genome ^ flip
        w1.run(3)
        w2.run(3)
        self.assertEqual(w1.state_hash(), w2.state_hash())

    def test_mutate_rate_zero_is_identity(self):
        rng = __import__("random").Random(1)
        g = random_genome(rng, 56)
        self.assertEqual(mutate(g, rng, 56, 0.0), g)


class TestDeterminism(unittest.TestCase):
    def test_same_seed_same_world(self):
        cfg = tiny_config(GOSSIP)
        w1 = World(cfg, seed=42)
        w2 = World(cfg, seed=42)
        w1.run(5)
        w2.run(5)
        self.assertEqual(w1.state_hash(), w2.state_hash())
        self.assertEqual(w1.history, w2.history)

    def test_different_seeds_differ(self):
        cfg = tiny_config(GOSSIP)
        w1 = World(cfg, seed=42)
        w2 = World(cfg, seed=43)
        w1.run(5)
        w2.run(5)
        self.assertNotEqual(w1.state_hash(), w2.state_hash())


class TestSelection(unittest.TestCase):
    def test_eaters_outreproduce_spinners(self):
        # hand-built genomes: always-eat vs always-turn-left, same start.
        # eaters must hold more total energy after several generations.
        cfg = tiny_config(BASELINE)
        eat_entry = 3  # ACT_EAT encoded in every table slot
        spin_entry = 1  # ACT_LEFT
        eat_genome = 0
        spin_genome = 0
        for e in range(16):
            eat_genome |= (eat_entry << (3 * e))
            spin_genome |= (spin_entry << (3 * e))

        def total_energy(genome, seed):
            w = World(cfg, seed=seed)
            for cr in w.creatures:
                cr.genome = genome
            w.run(6)
            return sum(cr.energy for cr in w.creatures)

        # eaters start on food-rich cells often enough to beat spinners;
        # compare totals across the same seed
        e = total_energy(eat_genome, 11)
        s = total_energy(spin_genome, 11)
        self.assertGreater(e, s)


class TestSignals(unittest.TestCase):
    def test_emission_costs_energy(self):
        w = World(tiny_config(GOSSIP), seed=3)
        cr = w.creatures[0]
        # force FOOD policy 01 (emit on eat, always): bits 192-193 = 01,
        # and force table entry 1 (sensor pattern food-here) to ACT_EAT
        cr.genome = (cr.genome & ~(0b11 << 192)) | (0b01 << 192)
        cr.genome = (cr.genome & ~(0b111 << 3)) | (ACT_EAT << 3)
        before = cr.energy
        w.food[(cr.x, cr.y)] = 5
        w._rebuild_cell_pop()
        w.act(cr, (True, False, False, False, False, False))
        # ate (+15) and emitted (-1): net +14 vs +15 without emission
        self.assertEqual(cr.energy, before + 15 - 1)
        self.assertIn((cr.x, cr.y), w.signals)

    def test_signal_sensed_within_radius(self):
        w = World(tiny_config(GOSSIP), seed=3)
        cr = w.creatures[0]
        w.signals[(cr.x, cr.y)] = {SIG_FOOD: SIG_TTL}
        w._rebuild_cell_pop()
        s = w.sense(cr)
        self.assertTrue(s[4])   # FOOD heard
        self.assertFalse(s[5])  # DANGER not heard

    def test_signal_not_sensed_far_away(self):
        w = World(tiny_config(GOSSIP), seed=3)
        cr = w.creatures[0]
        far = ((cr.x + 6) % 12, (cr.y + 6) % 12)
        w.signals[far] = {SIG_FOOD: SIG_TTL}
        w._rebuild_cell_pop()
        s = w.sense(cr)
        self.assertFalse(s[4])

    def test_signal_decays(self):
        w = World(tiny_config(GOSSIP), seed=3)
        w.signals[(0, 0)] = {SIG_FOOD: SIG_TTL}
        for _ in range(SIG_TTL):
            w._decay_signals()
        self.assertNotIn((0, 0), w.signals)

    def test_deaf_world_never_senses_signals(self):
        w = World(tiny_config(GOSSIP_DEAF), seed=3)
        cr = w.creatures[0]
        # even with a live signal under its nose, a deaf creature hears nothing
        w.signals[(cr.x, cr.y)] = {SIG_FOOD: SIG_TTL}
        w._rebuild_cell_pop()
        s = w.sense(cr)
        self.assertFalse(s[4])
        self.assertFalse(s[5])

    def test_food_and_danger_coexist_on_one_cell(self):
        # regression: one signal per cell meant FOOD overwrote DANGER.
        # both types must survive on the same cell and both be sensed.
        w = World(tiny_config(GOSSIP), seed=3)
        cr = w.creatures[0]
        w.signals[(cr.x, cr.y)] = {SIG_FOOD: SIG_TTL}
        # emit a DANGER on the same cell via the engine
        cr.genome = (cr.genome & ~(0b11 << 194)) | (0b10 << 194)  # pol 10: emit when energy < 40
        cr.energy = 10
        w.food[(cr.x, cr.y)] = 0
        w._rebuild_cell_pop()
        w._maybe_emit(cr, SIG_DANGER)
        cell = w.signals[(cr.x, cr.y)]
        self.assertIn(SIG_FOOD, cell)
        self.assertIn(SIG_DANGER, cell)
        s = w.sense(cr)
        self.assertTrue(s[4])
        self.assertTrue(s[5])


class TestDirectionSignals(unittest.TestCase):
    """Experiment A: direction-signal semantics."""

    def _dir_world(self, seed=3):
        cfg = tiny_config(GOSSIP_DIR)
        return World(cfg, seed=seed)

    def _arrival_genome(self, cr):
        # emit policy 01 (always on arrival): bits 192-193 = 01
        cr.genome = (cr.genome & ~(0b11 << 192)) | (0b01 << 192)

    def test_arrival_emits_direction_signal(self):
        w = self._dir_world()
        cr = w.creatures[0]
        self._arrival_genome(cr)
        # put food to the EAST of the creature, none elsewhere nearby
        ex = (cr.x + 2) % 12
        w.food[(ex, cr.y)] = 5
        w._rebuild_cell_pop()
        before = cr.energy
        d = w._nearest_food_dir(cr)
        self.assertEqual(d, 1)  # east
        w._maybe_emit_dir(cr)
        self.assertIn((cr.x, cr.y), w.signals)
        self.assertIn(1, w.signals[(cr.x, cr.y)])  # east payload present
        self.assertEqual(cr.energy, before - 1)  # emission cost

    def test_no_nearby_food_suppresses_emission(self):
        w = self._dir_world()
        cr = w.creatures[0]
        self._arrival_genome(cr)
        # clear all food near the creature
        for k in list(w.food):
            w.food[k] = 0
        self.assertIsNone(w._nearest_food_dir(cr))
        w._maybe_emit_dir(cr)
        self.assertEqual(len(w.signals), 0)

    def test_own_cell_food_ignored_in_scan(self):
        # food only under the emitter's feet: nothing to point at
        w = self._dir_world()
        cr = w.creatures[0]
        for k in list(w.food):
            w.food[k] = 0
        w.food[(cr.x, cr.y)] = 5
        self.assertIsNone(w._nearest_food_dir(cr))

    def test_eating_does_not_emit_in_dir_mode(self):
        # classic FOOD-on-eat emission must not fire in direction mode
        # (its payload 0 would read as a bogus "north" signal)
        w = self._dir_world()
        cr = w.creatures[0]
        self._arrival_genome(cr)
        cr.genome = (cr.genome & ~(0b111 << 3)) | (ACT_EAT << 3)
        w.food[(cr.x, cr.y)] = 5
        w._rebuild_cell_pop()
        w.act(cr, (True, False, False, False, False, False))
        self.assertEqual(len(w.signals), 0)

    def test_s5_agrees_with_facing(self):
        w = self._dir_world()
        cr = w.creatures[0]
        cr.facing = 0  # north
        w.signals[(cr.x, cr.y)] = {0: 3}  # "food is north"
        w._rebuild_cell_pop()
        s = w.sense(cr)
        self.assertTrue(s[4])   # heard
        self.assertTrue(s[5])   # agrees with facing
        cr.facing = 1  # east
        s = w.sense(cr)
        self.assertTrue(s[4])
        self.assertFalse(s[5])  # north != east

    def test_dir_deaf_hears_nothing(self):
        cfg = tiny_config(GOSSIP_DIR_DEAF)
        w = World(cfg, seed=3)
        cr = w.creatures[0]
        w.signals[(cr.x, cr.y)] = {2: 3}  # live signal under its nose
        w._rebuild_cell_pop()
        s = w.sense(cr)
        self.assertFalse(s[4])
        self.assertFalse(s[5])

    def test_dir_neutral_bits_do_not_change_behavior(self):
        # bits 194-195 are spare drift in dir mode: flipping them must not
        # change the world trajectory
        cfg = tiny_config(GOSSIP_DIR)
        w1 = World(cfg, seed=7)
        w2 = World(cfg, seed=7)
        flip = 1 << 194
        for a, b in zip(w1.creatures, w2.creatures):
            b.genome = a.genome ^ flip
        w1.run(3)
        w2.run(3)
        self.assertEqual(w1.state_hash(), w2.state_hash())

    def test_dir_determinism(self):
        cfg = tiny_config(GOSSIP_DIR)
        w1 = World(cfg, seed=42)
        w2 = World(cfg, seed=42)
        w1.run(5)
        w2.run(5)
        self.assertEqual(w1.state_hash(), w2.state_hash())
        self.assertEqual(w1.history, w2.history)


class TestBaselineShape(unittest.TestCase):
    def test_baseline_flatlines_at_96(self):
        # the published signature: repertoire saturates at exactly 96
        # (16 entries x 6 actions) and then stops climbing.
        # full-size config: saturation happens within the first few gens.
        w = World(BASELINE, seed=5)
        w.run(12)
        reps = [h["repertoire"] for h in w.history]
        self.assertEqual(reps[-1], 96)
        # flat for the last 6 generations (the ratchet has stopped)
        self.assertEqual(len(set(reps[-6:])), 1)
        # and it got there early, not by slow accumulation
        first96 = next(i + 1 for i, r in enumerate(reps) if r == 96)
        self.assertLessEqual(first96, 10)


class TestBugFixes(unittest.TestCase):
    """Regression tests for the five review bugs (round 2)."""

    def test_newborn_does_not_act_on_birth_tick(self):
        # regression (a): _spawn appended during the step_tick loop, so
        # newborns acted (and paid metabolism) on their birth tick.
        c = tiny_config(BASELINE)
        c.mut_rate = 0.0
        c.imit_prob = 0.0
        w = World(c, seed=3)
        wait_genome = 0
        for e in range(16):
            wait_genome |= (4 << (3 * e))  # ACT_WAIT everywhere
        for cr in w.creatures:
            cr.genome = wait_genome
            cr.energy = 50
        parent = w.creatures[0]
        parent.energy = 200  # capped; only this one reproduces
        max_cid_before = max(cr.cid for cr in w.creatures)
        w.step_tick()
        newborns = [cr for cr in w.creatures if cr.cid > max_cid_before]
        self.assertEqual(len(newborns), 1)
        child = newborns[0]
        # parent: 200 -> act WAIT -> metabolic -2 = 198 -> split 99/99.
        # with the bug the child then acted and paid metabolism (97).
        self.assertEqual(child.energy, 99)
        self.assertEqual(parent.energy, 99)

    def test_model_pool_excludes_newborns(self):
        # regression (e): _pick_model re-sorted the whole population per
        # birth and let newborns count as adults for imitation.
        c = tiny_config(GOSSIP)
        w = World(c, seed=3)
        n_alive = len([cr for cr in w.creatures if cr.alive])
        max_cid_before = max(cr.cid for cr in w.creatures)
        for cr in w.creatures:
            cr.energy = 200  # everyone reproduces this tick
        w.step_tick()
        # pool built once at tick start: sized as the top quartile...
        self.assertEqual(len(w._model_pool), max(1, n_alive // 4))
        # ...and no newborn is in it
        for m in w._model_pool:
            self.assertLessEqual(m.cid, max_cid_before)
        # every model pick comes from the cached pool
        for _ in range(20):
            self.assertIn(w._pick_model(), w._model_pool)

    def test_compare_p5_short_history_no_crash(self):
        # regression (d): P5 printout crashed on f"{eb:.1f}" when eb was
        # None (fewer than 50 generations recorded).
        import json
        import os
        import tempfile
        import run

        def fake_hist(gens):
            return [{"generation": g + 1, "population": 400,
                     "mean_energy": 90.0, "total_energy": 36000.0,
                     "births": 10, "repertoire": 50, "signals_live": 0,
                     "emitter_frac": 0.0, "row_consensus": 0.5,
                     "rows_settled": 8, "row_persistence": None}
                    for g in range(gens)]

        data = {
            "baseline": {"mode": "baseline", "seeds": {"1": fake_hist(10)}},
            "gossip": {"mode": "gossip", "seeds": {"1": fake_hist(10)}},
            "gossip-deaf": {"mode": "gossip-deaf", "seeds": {"1": fake_hist(10)}},
        }
        paths = []
        try:
            for d in data.values():
                fd, p = tempfile.mkstemp(suffix=".json")
                with os.fdopen(fd, "w") as f:
                    json.dump(d, f)
                paths.append(p)
            run.compare(paths, sig_mode="gossip")  # must not raise
        finally:
            for p in paths:
                os.unlink(p)


if __name__ == "__main__":
    unittest.main()
