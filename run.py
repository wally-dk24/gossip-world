"""Runner for gossip-world seed comparisons.

Usage:
  python3 run.py --mode baseline|gossip|gossip-deaf|gossip-dir|gossip-dir-deaf \
      --seeds 1,2,3,4,5 --generations 150 --out results_<mode>.json

Then:
  python3 run.py --compare results_baseline.json results_gossip.json \
      results_gossip-deaf.json [--sig gossip]

  python3 run.py --compare results_baseline.json results_gossip-dir.json \
      results_gossip-dir-deaf.json --sig gossip-dir

The --compare step evaluates the falsifiable predictions P1-P6 from
DESIGN.md against the recorded histories. Seeds are paired: the same seed
across modes shares its initial randomness, so per-seed differences isolate
the mechanism.
"""

import argparse
import json
import sys
import time

from world import World, BASELINE, GOSSIP, GOSSIP_DEAF, GOSSIP_DIR, GOSSIP_DIR_DEAF

MODES = {"baseline": BASELINE, "gossip": GOSSIP, "gossip-deaf": GOSSIP_DEAF,
         "gossip-dir": GOSSIP_DIR, "gossip-dir-deaf": GOSSIP_DIR_DEAF}


def run_mode(mode, seeds, generations):
    cfg = MODES[mode]
    out = {"mode": mode, "generations": generations, "seeds": {}}
    for seed in seeds:
        t0 = time.time()
        w = World(cfg, seed=seed)
        w.run(generations)
        out["seeds"][str(seed)] = w.history
        el = time.time() - t0
        print(f"mode={mode} seed={seed} gens={generations} "
              f"pop={w.history[-1]['population']} "
              f"rep={w.history[-1]['repertoire']} "
              f"E={w.history[-1]['mean_energy']:.1f} "
              f"emit={w.history[-1]['emitter_frac']:.2f} "
              f"({el:.1f}s)", flush=True)
    return out


def load(path):
    with open(path) as f:
        return json.load(f)


def mean(xs):
    return sum(xs) / len(xs) if xs else 0


def compare(paths, sig_mode="gossip"):
    """Evaluate the falsifiable predictions against recorded histories.

    sig_mode names the signaling variant under test ("gossip" for week 1,
    "gossip-dir" for Experiment A); its ablation is sig_mode + "-deaf".
    Thresholds are identical across experiments so verdicts are comparable.
    """
    data = {d["mode"]: d for d in (load(p) for p in paths)}
    deaf_mode = sig_mode + "-deaf"
    modes = list(data)
    seeds = sorted(set().union(*[set(d["seeds"]) for d in data.values()]),
                   key=int)
    print(f"comparing modes {modes} over seeds {seeds} "
          f"(signal variant: {sig_mode})\n")

    def hist(mode, seed):
        return data[mode]["seeds"][seed]

    # P1: signal-mode repertoire > 96 by gen 40 and >= 150 by gen 150
    print("P1 (ratchet climbs past the 96 ceiling):")
    p1 = 0
    for s in seeds:
        h = hist(sig_mode, s)
        r40 = h[39]["repertoire"] if len(h) >= 40 else None
        r150 = h[-1]["repertoire"]
        ok = (r40 is not None and r40 > 96 and r150 >= 150)
        p1 += ok
        print(f"  seed {s}: rep@40={r40} rep@150={r150} -> {'PASS' if ok else 'FAIL'}")
    print(f"  P1: {p1}/{len(seeds)} seeds pass (need >=4)\n")

    # P2: signal-mode mean energy (gens 50-150) beats deaf control by >= 5
    print("P2 (signaling buys foraging efficiency vs deaf control):")
    p2 = 0
    for s in seeds:
        hg = hist(sig_mode, s)
        hd = hist(deaf_mode, s)
        eg = mean([x["mean_energy"] for x in hg[49:]])
        ed = mean([x["mean_energy"] for x in hd[49:]])
        ok = (eg - ed) >= 5
        p2 += ok
        print(f"  seed {s}: {sig_mode} E={eg:.1f} deaf E={ed:.1f} "
              f"diff={eg - ed:+.1f} -> {'PASS' if ok else 'FAIL'}")
    print(f"  P2: {p2}/{len(seeds)} seeds pass (need >=4)\n")

    # P3: deaf energy stays in the baseline band (no free lunch from tables)
    print("P3 (deaf control: bigger table alone buys nothing):")
    p3 = 0
    for s in seeds:
        hd = hist(deaf_mode, s)
        ed = mean([x["mean_energy"] for x in hd[49:]])
        ok = 75 <= ed <= 105
        p3 += ok
        print(f"  seed {s}: deaf E={ed:.1f} in [75,105] -> "
              f"{'PASS' if ok else 'FAIL'}")
    print(f"  P3: {p3}/{len(seeds)} seeds pass\n")

    # P4 (kill shot): signal mode not >= 3 above deaf in a majority of
    # seeds, or emitters purged below 10% -> the mechanism is dead
    print("P4 (kill shot):")
    p4_energy = 0
    p4_purged = 0
    for s in seeds:
        hg = hist(sig_mode, s)
        hd = hist(deaf_mode, s)
        eg = mean([x["mean_energy"] for x in hg[49:]])
        ed = mean([x["mean_energy"] for x in hd[49:]])
        p4_energy += (eg - ed) >= 3
        ef = hg[-1]["emitter_frac"]
        p4_purged += ef < 0.10
        print(f"  seed {s}: diff={eg - ed:+.1f} (>=3: {(eg - ed) >= 3}) "
              f"emitter_frac={ef:.2f} (purged<0.10: {ef < 0.10})")
    dead = (p4_energy <= len(seeds) // 2) or (p4_purged > len(seeds) // 2)
    print(f"  energy edge in {p4_energy}/{len(seeds)} seeds; "
          f"purged in {p4_purged}/{len(seeds)} seeds")
    print(f"  P4 verdict: mechanism {'DEAD' if dead else 'ALIVE'}\n")

    # P5: baseline fidelity
    print("P5 (baseline rebuild fidelity):")
    p5 = 0
    for s in seeds:
        hb = hist("baseline", s)
        reps = [x["repertoire"] for x in hb]
        first96 = next((i + 1 for i, r in enumerate(reps) if r == 96), None)
        eb = mean([x["mean_energy"] for x in hb[49:]]) if len(hb) >= 50 else None
        ok = (first96 is not None and first96 <= 15
              and eb is not None and 75 <= eb <= 105)
        p5 += ok
        print(f"  seed {s}: rep96@gen{first96} E={eb:.1f} -> "
              f"{'PASS' if ok else 'FAIL'}")
    print(f"  P5: {p5}/{len(seeds)} seeds pass\n")

    # P6 (channel check, Experiment A+): the signal channel is actually
    # used -- live signals in a majority of generations 50-150, in a
    # majority of seeds. A vestigial channel makes energy results
    # uninterpretable.
    print("P6 (channel is actually used):")
    p6 = 0
    for s in seeds:
        hg = hist(sig_mode, s)
        active = sum(1 for x in hg[49:] if x["signals_live"] > 0)
        frac = active / len(hg[49:])
        ok = frac > 0.5
        p6 += ok
        print(f"  seed {s}: live-signal gens={active}/{len(hg[49:])} "
              f"({frac:.2f}) -> {'PASS' if ok else 'FAIL'}")
    print(f"  P6: {p6}/{len(seeds)} seeds pass (need >{len(seeds) // 2})")


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=list(MODES))
    ap.add_argument("--seeds", default="1,2,3,4,5")
    ap.add_argument("--generations", type=int, default=150)
    ap.add_argument("--out", default=None)
    ap.add_argument("--compare", nargs="+", default=None)
    ap.add_argument("--sig", default="gossip",
                    help="signal variant under test in --compare "
                         "(ablation is <sig>-deaf)")
    a = ap.parse_args(argv)

    if a.compare:
        compare(a.compare, sig_mode=a.sig)
        return

    seeds = [int(s) for s in a.seeds.split(",") if s.strip()]
    out = run_mode(a.mode, seeds, a.generations)
    if a.out:
        with open(a.out, "w") as f:
            json.dump(out, f)
        print(f"wrote {a.out}", flush=True)


if __name__ == "__main__":
    main(sys.argv[1:])
