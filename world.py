"""gossip-world engine: a toroidal foraging ALife world.

Two configurations share this engine:
  - baseline: 56-bit genomes, 4 sensors, 16-entry policy table, no signals.
  - gossip: 208-bit genomes, 6 sensors (2 signal sensors), 64-entry table,
    event-driven FOOD/DANGER signaling with an energy cost per emission.
  - gossip-deaf: gossip genome/table, signaling fully disabled (ablation).
  - gossip-dir (Experiment A): gossip architecture, but the signal encodes
    the direction (N/E/S/W) of the nearest known food, emitted on arrival
    at a food cell before depletion. DANGER dropped.
  - gossip-dir-deaf: gossip-dir genome/table, signaling disabled (ablation).

Stdlib only. Deterministic per seed: one random.Random instance is threaded
through everything, no wall-clock dependence, fixed tick order by creature id.
"""

import random

# ---------------------------------------------------------------------------
# actions
# ---------------------------------------------------------------------------
ACT_FORWARD = 0
ACT_LEFT = 1
ACT_RIGHT = 2
ACT_EAT = 3
ACT_WAIT = 4
ACT_REST = 5
N_ACTIONS = 6

# signal types (classic mode)
SIG_FOOD = 0
SIG_DANGER = 1
# direction payload values (direction mode): 0=N 1=E 2=S 3=W (facing convention)
SIG_TTL = 3          # ticks before a signal fades
SIG_RADIUS = 2       # chebyshev radius within which a signal is sensed
SIG_COST = 1         # energy per emission
SIG_DIR_SCAN = 4     # chebyshev radius scanned for nearest food on emission

# ---------------------------------------------------------------------------
# configs
# ---------------------------------------------------------------------------
class Config:
    def __init__(self, name, genome_bits, table_bits, n_sensors,
                 signals_enabled, grid_w=40, grid_h=40, n_patches=12,
                 patch_radius=4, food_max=5, food_regrow_ticks=4,
                 init_pop=400, pop_cap=600, ticks_per_gen=60,
                 imit_prob=0.2, copy_err=0.01, mut_rate=0.005,
                 eat_gain=15, move_cost=1, rest_gain=2, metabolic_cost=2,
                 repro_threshold=160, energy_max=200,
                 neutral_offset=0, neutral_width=0, signal_mode=None):
        self.name = name
        self.genome_bits = genome_bits
        self.table_bits = table_bits      # bits encoding the policy table
        self.n_sensors = n_sensors
        self.n_entries = 1 << n_sensors
        self.signals_enabled = signals_enabled
        # None (no signals), "classic" (FOOD/DANGER types), or
        # "direction" (Experiment A: 2-bit N/E/S/W food-direction payload)
        self.signal_mode = signal_mode
        self.grid_w = grid_w
        self.grid_h = grid_h
        self.n_patches = n_patches
        self.patch_radius = patch_radius
        self.food_max = food_max
        self.food_regrow_ticks = food_regrow_ticks
        self.init_pop = init_pop
        self.pop_cap = pop_cap
        self.ticks_per_gen = ticks_per_gen
        self.imit_prob = imit_prob
        self.copy_err = copy_err
        self.mut_rate = mut_rate
        self.eat_gain = eat_gain
        self.move_cost = move_cost
        self.rest_gain = rest_gain
        self.metabolic_cost = metabolic_cost
        self.repro_threshold = repro_threshold
        self.energy_max = energy_max
        self.neutral_offset = neutral_offset
        self.neutral_width = neutral_width


BASELINE = Config("baseline", genome_bits=56, table_bits=48, n_sensors=4,
                  signals_enabled=False, neutral_offset=48, neutral_width=8,
                  grid_w=40, grid_h=40, n_patches=10, patch_radius=4,
                  food_regrow_ticks=6, metabolic_cost=3.5)

GOSSIP = Config("gossip", genome_bits=208, table_bits=192, n_sensors=6,
                signals_enabled=True, neutral_offset=196, neutral_width=12,
                signal_mode="classic",
                grid_w=40, grid_h=40, n_patches=10, patch_radius=4,
                food_regrow_ticks=6, metabolic_cost=3.5)

GOSSIP_DEAF = Config("gossip-deaf", genome_bits=208, table_bits=192,
                     n_sensors=6, signals_enabled=False,
                     neutral_offset=196, neutral_width=12,
                     signal_mode="classic",
                     grid_w=40, grid_h=40, n_patches=10, patch_radius=4,
                     food_regrow_ticks=6, metabolic_cost=3.5)

# Experiment A: same architecture as gossip, direction-signal semantics.
# Bits 194-195 (DANGER policy in gossip) are spare drift here, so the
# neutral mask covers 194-207.
GOSSIP_DIR = Config("gossip-dir", genome_bits=208, table_bits=192,
                    n_sensors=6, signals_enabled=True,
                    neutral_offset=194, neutral_width=14,
                    signal_mode="direction",
                    grid_w=40, grid_h=40, n_patches=10, patch_radius=4,
                    food_regrow_ticks=6, metabolic_cost=3.5)

GOSSIP_DIR_DEAF = Config("gossip-dir-deaf", genome_bits=208, table_bits=192,
                         n_sensors=6, signals_enabled=False,
                         neutral_offset=194, neutral_width=14,
                         signal_mode="direction",
                         grid_w=40, grid_h=40, n_patches=10, patch_radius=4,
                         food_regrow_ticks=6, metabolic_cost=3.5)

# signal-module bit offsets inside the gossip genome
FOOD_POL_BITS = (192, 2)
DANGER_POL_BITS = (194, 2)


def get_bits(genome, offset, width):
    return (genome >> offset) & ((1 << width) - 1)


def decode_action(genome, entry):
    """Decode one 3-bit policy-table entry to an action 0..5."""
    return ((genome >> (3 * entry)) & 0b111) % N_ACTIONS


def random_genome(rng, bits):
    return rng.getrandbits(bits)


def mutate(genome, rng, bits, rate):
    for i in range(bits):
        if rng.random() < rate:
            genome ^= (1 << i)
    return genome


# ---------------------------------------------------------------------------
# creatures
# ---------------------------------------------------------------------------
class Creature:
    __slots__ = ("cid", "x", "y", "facing", "energy", "genome", "alive")

    def __init__(self, cid, x, y, facing, energy, genome):
        self.cid = cid
        self.x = x
        self.y = y
        self.facing = facing  # 0=N 1=E 2=S 3=W
        self.energy = energy
        self.genome = genome
        self.alive = True


DX = (0, 1, 0, -1)
DY = (-1, 0, 1, 0)


# ---------------------------------------------------------------------------
# world
# ---------------------------------------------------------------------------
class World:
    def __init__(self, config, seed):
        self.cfg = config
        self.rng = random.Random(seed)
        self.seed = seed
        self.tick = 0
        self.generation = 0
        self.next_cid = 0
        self.creatures = []
        # food: dict[(x,y)] -> units
        self.food = {}
        # signals: dict[(x,y)] -> [sigtype, ttl]
        self.signals = {}
        self._init_food()
        self._init_population()
        # cumulative repertoire: set of (sensor_tuple, action)
        self.repertoire = set()
        # history of per-generation metrics
        self.history = []

    # -- setup -------------------------------------------------------------
    def _init_food(self):
        c = self.cfg
        for _ in range(c.n_patches):
            cx = self.rng.randrange(c.grid_w)
            cy = self.rng.randrange(c.grid_h)
            for ox in range(-c.patch_radius, c.patch_radius + 1):
                for oy in range(-c.patch_radius, c.patch_radius + 1):
                    if ox * ox + oy * oy <= c.patch_radius * c.patch_radius:
                        x = (cx + ox) % c.grid_w
                        y = (cy + oy) % c.grid_h
                        self.food[(x, y)] = self.rng.randint(2, c.food_max)

    def _init_population(self):
        c = self.cfg
        for _ in range(c.init_pop):
            self._spawn(self.rng.randrange(c.grid_w),
                        self.rng.randrange(c.grid_h),
                        self.rng.randrange(4), 100,
                        random_genome(self.rng, c.genome_bits))

    def _spawn(self, x, y, facing, energy, genome):
        cr = Creature(self.next_cid, x % self.cfg.grid_w, y % self.cfg.grid_h,
                      facing, energy, genome)
        self.next_cid += 1
        self.creatures.append(cr)
        return cr

    # -- sensing -----------------------------------------------------------
    def _offsets(self, radius):
        if not hasattr(self, "_offset_cache"):
            self._offset_cache = {}
        if radius not in self._offset_cache:
            offs = [(ox, oy)
                    for ox in range(-radius, radius + 1)
                    for oy in range(-radius, radius + 1)
                    if max(abs(ox), abs(oy)) <= radius]
            self._offset_cache[radius] = offs
        return self._offset_cache[radius]

    def _crowded_here(self, cr):
        c = self.cfg
        n = 0
        for (ox, oy) in self._offsets(1):
            if ox == 0 and oy == 0:
                continue
            x = (cr.x + ox) % c.grid_w
            y = (cr.y + oy) % c.grid_h
            n += self._cell_pop.get((x, y), 0)
        return n > 3

    def _signal_sensed(self, cr, sigtype):
        c = self.cfg
        for (ox, oy) in self._offsets(SIG_RADIUS):
            x = (cr.x + ox) % c.grid_w
            y = (cr.y + oy) % c.grid_h
            s = self.signals.get((x, y))
            if s is not None and s[0] == sigtype:
                return True
        return False

    def _signal_dir_sensed(self, cr):
        """Direction-mode: payload (0..3 = N/E/S/W) of a heard signal,
        or None. First signal found in fixed scan order wins."""
        c = self.cfg
        for (ox, oy) in self._offsets(SIG_RADIUS):
            x = (cr.x + ox) % c.grid_w
            y = (cr.y + oy) % c.grid_h
            s = self.signals.get((x, y))
            if s is not None:
                return s[0]
        return None

    def sense(self, cr):
        c = self.cfg
        fx = (cr.x + DX[cr.facing]) % c.grid_w
        fy = (cr.y + DY[cr.facing]) % c.grid_h
        s = [self.food.get((cr.x, cr.y), 0) > 0,
             self.food.get((fx, fy), 0) > 0,
             self._crowded_here(cr),
             cr.energy < 40]
        if c.n_sensors > 4:
            if c.signal_mode == "direction":
                heard = (self._signal_dir_sensed(cr)
                         if c.signals_enabled else None)
                s.append(heard is not None)
                s.append(heard is not None and heard == cr.facing)
            else:
                heard = c.signals_enabled
                s.append(heard and self._signal_sensed(cr, SIG_FOOD))
                s.append(heard and self._signal_sensed(cr, SIG_DANGER))
        return tuple(s)

    # -- acting ------------------------------------------------------------
    def act(self, cr, sensors):
        entry = 0
        for i, bit in enumerate(sensors):
            if bit:
                entry |= (1 << i)
        action = decode_action(cr.genome, entry)
        self.repertoire.add((sensors, action))
        c = self.cfg
        if action == ACT_FORWARD:
            cr.x = (cr.x + DX[cr.facing]) % c.grid_w
            cr.y = (cr.y + DY[cr.facing]) % c.grid_h
            cr.energy -= c.move_cost
            # Experiment A: arrival at a food cell emits a direction signal
            # (before any depletion), gated by the emit policy.
            if (c.signal_mode == "direction"
                    and self.food.get((cr.x, cr.y), 0) > 0):
                self._maybe_emit_dir(cr)
        elif action == ACT_LEFT:
            cr.facing = (cr.facing - 1) % 4
        elif action == ACT_RIGHT:
            cr.facing = (cr.facing + 1) % 4
        elif action == ACT_EAT:
            if self.food.get((cr.x, cr.y), 0) > 0:
                self.food[(cr.x, cr.y)] -= 1
                cr.energy += c.eat_gain
                # classic mode only: direction mode emits on arrival instead
                if c.signal_mode == "classic":
                    self._maybe_emit(cr, SIG_FOOD, ate=True)
        elif action == ACT_REST:
            cr.energy += c.rest_gain
        # ACT_WAIT: nothing

    # -- signaling ---------------------------------------------------------
    def _maybe_emit(self, cr, sigtype, ate=False):
        c = self.cfg
        if not c.signals_enabled:
            return
        if sigtype == SIG_FOOD and ate:
            pol = get_bits(cr.genome, *FOOD_POL_BITS)
            crowded = self._crowded_here(cr)
            if pol == 0:
                return
            if pol == 2 and cr.energy <= 100:
                return
            if pol == 3 and crowded:
                return
        elif sigtype == SIG_DANGER:
            pol = get_bits(cr.genome, *DANGER_POL_BITS)
            if pol == 0:
                return
            poor = self.food.get((cr.x, cr.y), 0) == 0
            crowded = self._crowded_here(cr)
            low = cr.energy < 40
            if pol == 1 and not (poor and crowded):
                return
            if pol == 2 and not low:
                return
            if pol == 3 and not (low and crowded):
                return
        else:
            return
        if cr.energy > SIG_COST:
            cr.energy -= SIG_COST
            self.signals[(cr.x, cr.y)] = [sigtype, SIG_TTL]

    def _decay_signals(self):
        dead = [k for k, v in self.signals.items() if v[1] <= 1]
        for k in dead:
            del self.signals[k]
        for v in self.signals.values():
            v[1] -= 1

    # -- direction signaling (Experiment A) --------------------------------
    def _nearest_food_dir(self, cr):
        """Direction (0=N 1=E 2=S 3=W) from the creature toward the
        food-richest cell within SIG_DIR_SCAN, excluding its own cell.
        Ties: nearest, then fixed scan order (deterministic).
        None if no other food is in radius."""
        c = self.cfg
        best_key = None
        best_ox = best_oy = 0
        for (ox, oy) in self._offsets(SIG_DIR_SCAN):
            if ox == 0 and oy == 0:
                continue
            x = (cr.x + ox) % c.grid_w
            y = (cr.y + oy) % c.grid_h
            f = self.food.get((x, y), 0)
            if f <= 0:
                continue
            key = (f, -max(abs(ox), abs(oy)))
            if best_key is None or key > best_key:
                best_key = key
                best_ox, best_oy = ox, oy
        if best_key is None:
            return None
        if abs(best_ox) >= abs(best_oy):
            return 1 if best_ox > 0 else 3
        return 2 if best_oy > 0 else 0

    def _maybe_emit_dir(self, cr):
        c = self.cfg
        if not c.signals_enabled:
            return
        pol = get_bits(cr.genome, *FOOD_POL_BITS)
        if pol == 0:
            return
        if pol == 2 and cr.energy <= 100:
            return
        if pol == 3 and self._crowded_here(cr):
            return
        direction = self._nearest_food_dir(cr)
        if direction is None:
            return
        if cr.energy > SIG_COST:
            cr.energy -= SIG_COST
            self.signals[(cr.x, cr.y)] = [direction, SIG_TTL]

    # -- ecology -----------------------------------------------------------
    def _rebuild_cell_pop(self):
        self._cell_pop = {}
        for cr in self.creatures:
            if cr.alive:
                self._cell_pop[(cr.x, cr.y)] = \
                    self._cell_pop.get((cr.x, cr.y), 0) + 1

    def _regrow_food(self):
        c = self.cfg
        if self.tick % c.food_regrow_ticks != 0:
            return
        for k, v in self.food.items():
            if v < c.food_max:
                self.food[k] = v + 1

    def _reproduce(self, cr):
        c = self.cfg
        if cr.energy < c.repro_threshold:
            return
        cr.energy //= 2
        child_energy = cr.energy
        # transmission: noisy imitation vs genetic inheritance
        if self.rng.random() < c.imit_prob:
            model = self._pick_model()
            table = get_bits(model.genome, 0, c.table_bits)
            # copy errors on the table bits
            copied = 0
            for i in range(c.table_bits):
                bit = (table >> i) & 1
                if self.rng.random() < c.copy_err:
                    bit ^= 1
                copied |= (bit << i)
            # non-table bits inherited from the genetic parent
            rest_mask = ((1 << c.genome_bits) - 1) ^ ((1 << c.table_bits) - 1)
            child_genome = copied | (cr.genome & rest_mask)
            child_genome = mutate(child_genome, self.rng,
                                  c.genome_bits, c.mut_rate)
        else:
            child_genome = mutate(cr.genome, self.rng,
                                  c.genome_bits, c.mut_rate)
        nx = (cr.x + self.rng.choice((-1, 0, 1))) % c.grid_w
        ny = (cr.y + self.rng.choice((-1, 0, 1))) % c.grid_h
        self._spawn(nx, ny, self.rng.randrange(4), child_energy, child_genome)

    def _pick_model(self):
        # a random adult from the top energy quartile
        alive = [cr for cr in self.creatures if cr.alive]
        alive.sort(key=lambda cr: cr.energy, reverse=True)
        q = max(1, len(alive) // 4)
        return self.rng.choice(alive[:q])

    def _deaths(self):
        c = self.cfg
        self.creatures = [cr for cr in self.creatures
                          if cr.alive and cr.energy > 0]
        # carrying capacity: when over cap, the weakest are culled.
        # this keeps turnover (and selection) operating at the top end.
        if len(self.creatures) > c.pop_cap:
            self.creatures.sort(key=lambda cr: cr.energy, reverse=True)
            self.creatures = self.creatures[:c.pop_cap]

    # -- main loop ---------------------------------------------------------
    def step_tick(self):
        c = self.cfg
        self._rebuild_cell_pop()
        for cr in self.creatures:
            if not cr.alive or cr.energy <= 0:
                continue
            sensors = self.sense(cr)
            self.act(cr, sensors)
            cr.energy -= c.metabolic_cost  # basal metabolism: living costs
            if cr.energy > c.energy_max:
                cr.energy = c.energy_max  # storage cap: hoarding is wasted
            if cr.energy <= 0:
                continue
            # danger emission checked once per tick after acting
            # (classic mode only; direction mode emits on arrival)
            if (c.signals_enabled and c.signal_mode == "classic"
                    and cr.energy > 0
                    and get_bits(cr.genome, *DANGER_POL_BITS) != 0):
                self._maybe_emit(cr, SIG_DANGER)
            if cr.energy >= c.repro_threshold:
                self._reproduce(cr)
        self._decay_signals()
        self._regrow_food()
        self._deaths()
        self.tick += 1

    def step_generation(self):
        for _ in range(self.cfg.ticks_per_gen):
            self.step_tick()
        self.generation += 1
        alive = [cr for cr in self.creatures if cr.energy > 0]
        mean_e = (sum(cr.energy for cr in alive) / len(alive)) if alive else 0
        # emitter fraction: creatures whose FOOD emit policy is not "never"
        # (bits 192-193; zero for 56-bit baseline genomes)
        emitters = sum(1 for cr in alive
                       if get_bits(cr.genome, *FOOD_POL_BITS) != 0)
        self.history.append({
            "generation": self.generation,
            "population": len(alive),
            "mean_energy": mean_e,
            "repertoire": len(self.repertoire),
            "signals_live": len(self.signals),
            "emitter_frac": (emitters / len(alive)) if alive else 0,
        })

    def run(self, generations):
        for _ in range(generations):
            self.step_generation()
        return self.history

    def state_hash(self):
        """Deterministic fingerprint of the behavior-relevant world state.

        Neutral/drift genome bits are masked out: two worlds differing only
        in bits that cannot affect behavior must hash identically.
        """
        c = self.cfg
        mask = ((1 << c.genome_bits) - 1)
        if c.neutral_width:
            mask ^= (((1 << c.neutral_width) - 1) << c.neutral_offset)
        parts = [self.tick, self.generation, len(self.creatures)]
        for cr in sorted(self.creatures, key=lambda c: c.cid):
            parts += [cr.cid, cr.x, cr.y, cr.facing, cr.energy,
                      cr.genome & mask]
        parts += [len(self.food)]
        for k in sorted(self.food):
            parts += [k[0], k[1], self.food[k]]
        return hash(tuple(parts))
