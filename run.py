"""Runner for gossip-world seed comparisons.

Usage:
  python3 run.py --mode baseline|gossip|gossip-deaf|gossip-noise|gossip-free|gossip-imitable|gossip-dir|gossip-dir-deaf \
      --seeds 1,2,3,4,5 --generations 150 --out results_<mode>.json

Then:
  python3 run.py --compare results_baseline.json results_gossip.json \
      results_gossip-deaf.json [--sig gossip]

  python3 run.py --controls results_B_baseline.json results_B_gossip-deaf.json \
      results_B_gossip.json results_B_gossip-noise.json results_B_gossip-free.json
      (round-2 control battery: evaluates pre-registered PB1-PB6)

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

from world import World, BASELINE, GOSSIP, GOSSIP_DEAF, GOSSIP_DIR, GOSSIP_DIR_DEAF, \
    GOSSIP_NOISE, GOSSIP_FREE, GOSSIP_IMITABLE

MODES = {"baseline": BASELINE, "gossip": GOSSIP, "gossip-deaf": GOSSIP_DEAF,
         "gossip-dir": GOSSIP_DIR, "gossip-dir-deaf": GOSSIP_DIR_DEAF,
         "gossip-noise": GOSSIP_NOISE, "gossip-free": GOSSIP_FREE,
         "gossip-imitable": GOSSIP_IMITABLE}


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
        eb_s = f"{eb:.1f}" if eb is not None else "n/a"
        f96_s = f"gen{first96}" if first96 is not None else "never"
        print(f"  seed {s}: rep96@{f96_s} E={eb_s} -> "
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
        tail = hg[49:]
        active = sum(1 for x in tail if x["signals_live"] > 0)
        frac = (active / len(tail)) if tail else 0
        ok = frac > 0.5
        p6 += ok
        print(f"  seed {s}: live-signal gens={active}/{len(tail)} "
              f"({frac:.2f}) -> {'PASS' if ok else 'FAIL'}")
    print(f"  P6: {p6}/{len(seeds)} seeds pass (need >{len(seeds) // 2})")


def sign_test_p(diffs):
    """Two-sided binomial sign-test p-value for paired differences.

    Ties (diff == 0) are dropped, per the standard sign test.
    """
    import math
    nz = [d for d in diffs if d != 0]
    n = len(nz)
    if n == 0:
        return 1.0
    k = sum(1 for d in nz if d > 0)
    lo = min(k, n - k)
    p = sum(math.comb(n, i) for i in range(lo + 1)) / (2 ** n)
    return min(1.0, 2 * p)


def window_mean(hist, key, lo=49, hi=None):
    xs = [x[key] for x in hist[lo:hi] if x.get(key) is not None]
    return mean(xs)


def compare_controls(paths):
    """Evaluate the round-2 pre-registered predictions (PB1-PB6) against
    the 20-seed control battery.

    Expects five result files with modes: baseline, gossip-deaf, gossip,
    gossip-noise, gossip-free. Seeds are paired across modes.
    """
    data = {d["mode"]: d for d in (load(p) for p in paths)}
    modes = ["baseline", "gossip-deaf", "gossip", "gossip-noise",
             "gossip-free"]
    for m in modes:
        if m not in data:
            print(f"missing mode {m} in {paths}; aborting")
            return
    seeds = sorted(set().union(*[set(data[m]["seeds"]) for m in modes]),
                   key=int)
    print(f"control battery: modes {modes} over {len(seeds)} seeds\n")

    def hist(mode, seed):
        return data[mode]["seeds"][seed]

    # -- per-arm summary (gens 50-150 window, gen-150 snapshots) ---------
    print("per-arm summary (window = generations 50-150; @150 = gen 150):")
    print(f"{'mode':<14}{'E':>7}{'pop':>7}{'births':>8}{'Etot':>8}"
          f"{'rep@150':>8}{'cons@150':>9}{'set@150':>8}{'pers@150':>9}")
    arm = {}
    for m in modes:
        E = [window_mean(hist(m, s), "mean_energy") for s in seeds]
        pop = [window_mean(hist(m, s), "population") for s in seeds]
        births = [window_mean(hist(m, s), "births") for s in seeds]
        etot = [window_mean(hist(m, s), "total_energy") for s in seeds]
        cons = [hist(m, s)[-1].get("row_consensus") or 0 for s in seeds]
        sett = [hist(m, s)[-1].get("rows_settled") or 0 for s in seeds]
        pers = [x for x in
                (hist(m, s)[-1].get("row_persistence") for s in seeds)
                if x is not None]
        arm[m] = {"E": E, "pop": pop, "births": births, "etot": etot,
                  "cons": cons, "sett": sett, "pers": pers}
        print(f"{m:<14}{mean(E):>7.1f}{mean(pop):>7.0f}{mean(births):>8.1f}"
              f"{mean(etot):>8.0f}{mean([hist(m, s)[-1]['repertoire'] for s in seeds]):>8.0f}"
              f"{mean(cons):>9.2f}{mean(sett):>8.1f}"
              f"{(mean(pers) if pers else float('nan')):>9.2f}")
    print()

    # -- paired differences ------------------------------------------------
    def diffs(a, b, key="mean_energy"):
        return [window_mean(hist(a, s), key) - window_mean(hist(b, s), key)
                for s in seeds]

    pairs = [("gossip", "gossip-noise", "information value "
              "(gossip - noise)"),
             ("gossip-noise", "gossip-deaf", "bigger-table cost "
              "(noise - deaf)"),
             ("gossip-free", "gossip-noise", "cost masking "
              "(free - noise)"),
             ("gossip", "gossip-deaf", "week-1 gap replicated "
              "(gossip - deaf)")]
    print("paired mean-energy differences (gens 50-150):")
    pd = {}
    for a, b, label in pairs:
        ds = diffs(a, b)
        k = sum(1 for d in ds if d > 0)
        p = sign_test_p(ds)
        pd[(a, b)] = ds
        print(f"  {label}: mean {mean(ds):+.2f}  "
              f"seeds>0: {k}/{len(ds)}  sign-test p={p:.3f}")
    print()

    # -- PB verdicts ---------------------------------------------------------
    print("prediction scorecard:")
    d_gn = pd[("gossip", "gossip-noise")]
    d_nd = pd[("gossip-noise", "gossip-deaf")]
    d_fn = pd[("gossip-free", "gossip-noise")]
    d_gd = pd[("gossip", "gossip-deaf")]

    pb1 = abs(mean(d_gn)) <= 2
    print(f"  PB1 (info ~ 0: |E_gossip - E_noise| <= 2): "
          f"|{mean(d_gn):+.2f}| -> {'PASS' if pb1 else 'FAIL'}")

    pb2 = mean(d_nd) < -2
    print(f"  PB2 (table is costly: E_noise - E_deaf < -2): "
          f"{mean(d_nd):+.2f} -> {'PASS' if pb2 else 'FAIL'}")

    pb3 = mean(d_fn) > 2
    print(f"  PB3 (cost masked info: E_free - E_noise > 2): "
          f"{mean(d_fn):+.2f} -> {'PASS' if pb3 else 'FAIL'}")

    cons_gap = mean(arm["gossip-deaf"]["cons"]) - mean(arm["gossip-noise"]["cons"])
    pb4 = cons_gap >= 0.10
    print(f"  PB4 (unselected rows: consensus(deaf) - consensus(noise) >= 0.10): "
          f"{cons_gap:+.2f} -> {'PASS' if pb4 else 'FAIL'}")

    pers_gap = mean(arm["gossip-deaf"]["pers"]) - mean(arm["gossip-noise"]["pers"])
    pb5 = pers_gap > 0.05
    print(f"  PB5 (retention: persistence(deaf) - persistence(noise) > 0.05): "
          f"{pers_gap:+.2f} -> {'PASS' if pb5 else 'FAIL'}")

    # PB6: P5 sanity on the fixed engine
    p5 = 0
    for s in seeds:
        hb = hist("baseline", s)
        reps = [x["repertoire"] for x in hb]
        first96 = next((i + 1 for i, r in enumerate(reps) if r == 96), None)
        eb = window_mean(hb, "mean_energy")
        if first96 is not None and first96 <= 15 and 75 <= eb <= 105:
            p5 += 1
    pb6 = p5 >= 0.8 * len(seeds)
    print(f"  PB6 (P5 sanity on fixed engine): {p5}/{len(seeds)} seeds -> "
          f"{'PASS' if pb6 else 'FAIL'}")

    print(f"\nweek-1 gap replication check: mean(gossip - deaf) = "
          f"{mean(d_gd):+.2f} over {len(seeds)} seeds "
          f"(week 1: -1.5 to -11.5 over 5 seeds)")


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=list(MODES))
    ap.add_argument("--seeds", default="1,2,3,4,5")
    ap.add_argument("--generations", type=int, default=150)
    ap.add_argument("--out", default=None)
    ap.add_argument("--compare", nargs="+", default=None)
    ap.add_argument("--controls", nargs="+", default=None,
                    help="evaluate round-2 predictions on 5 control-battery "
                         "result files (baseline, deaf, gossip, noise, free)")
    ap.add_argument("--sig", default="gossip",
                    help="signal variant under test in --compare "
                         "(ablation is <sig>-deaf)")
    a = ap.parse_args(argv)

    if a.compare:
        compare(a.compare, sig_mode=a.sig)
        return

    if a.controls:
        compare_controls(a.controls)
        return

    seeds = [int(s) for s in a.seeds.split(",") if s.strip()]
    out = run_mode(a.mode, seeds, a.generations)
    if a.out:
        with open(a.out, "w") as f:
            json.dump(out, f)
        print(f"wrote {a.out}", flush=True)


if __name__ == "__main__":
    main(sys.argv[1:])
