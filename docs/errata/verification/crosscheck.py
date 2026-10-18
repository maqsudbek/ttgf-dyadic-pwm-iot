#!/usr/bin/env python3
"""Cross-check the Verilog core against dpwm.vhd (GHDL) and against the Python model.

    python3 crosscheck.py normal                       # Normal mode, all 4096 codes, 5 widths (submitted RTL)
    python3 crosscheck.py static  --dut submitted      # table of the errata (E1, E2, E5 ...)
    python3 crosscheck.py static  --dut fixed          # must be all '='
    python3 crosscheck.py static  --dut fixed --const  # constant dyadic word
    python3 crosscheck.py dynamic --dut fixed          # control word changes every period

Needs: ghdl (set GHDL=/path/to/ghdl and GHDL_OPTS="--PREFIX=..." if it is not in PATH) and iverilog.
Each case runs the VHDL and the Verilog with the same 12-bit control word and compares the
PWM_HIGH cycles of every switching period.

Table symbols (3 random control words per cell):
    =  all periods equal          P  same set of values per window, different order
    M  same average, other values X  different average
"""

import argparse
import atexit
import collections
import os
import random
import shutil
import subprocess
import sys
import tempfile
from multiprocessing import get_context

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(HERE, "..", "test"))

from vhdl_model import vhdl_sequence  # noqa: E402

VHDL_DIR = os.path.join(ROOT, "docs", "dyadic_vhdl")
CORES = {
    "submitted": os.path.join(ROOT, "src", "dyadic.v"),
    "fixed": os.path.join(HERE, "..", "rtl", "dyadic_fixed.v"),
}
GHDL = os.environ.get("GHDL", "ghdl")
GHDL_OPTS = os.environ.get("GHDL_OPTS", "").split()
BUILD = None
DUT = None


def sh(cmd, **kw):
    subprocess.run(cmd, check=True, capture_output=True, text=True, **kw)


def build(dut):
    global BUILD
    BUILD = tempfile.mkdtemp(prefix="crosscheck_")
    atexit.register(shutil.rmtree, BUILD, True)
    sh([GHDL, "-a", "--std=08"] + GHDL_OPTS + [os.path.join(VHDL_DIR, "pwm_97466hz.vhd"),
       os.path.join(VHDL_DIR, "dpwm.vhd"), os.path.join(HERE, "tb_dpwm.vhd")], cwd=BUILD)
    sh([GHDL, "-e", "--std=08"] + GHDL_OPTS + ["tb_dpwm"], cwd=BUILD)
    sh(["iverilog", "-g2012", "-o", os.path.join(BUILD, "rtl.vvp"), os.path.join(HERE, "tb_rtl.v"),
        os.path.join(ROOT, "src", "project.v"), CORES[dut]])


def run_vhdl(uin, bits, m, mode, const, word, nper, ramp=0):
    cmd = [os.path.join(BUILD, "tb_dpwm"), "-gG_UIN=%d" % uin, "-gG_BITS=%d" % bits, "-gG_LEN=%d" % m,
           "-gG_MODE=%d" % mode, "-gG_CONST=%d" % const, "-gG_WORD=%d" % word, "-gG_NPER=%d" % nper,
           "-gG_RAMP=%d" % ramp]
    out = subprocess.run(cmd, capture_output=True, text=True, cwd=BUILD).stdout
    rows = []
    for line in out.splitlines():
        p = line.split()
        if len(p) == 6 and p[0].isdigit():
            rows.append((int(p[1] == "1"), int(p[2] == "1")))
    return rows


def run_rtl(uin, bits, m, mode, const, word, nper, ramp=0):
    name = "rtl_%d.txt" % os.getpid()
    subprocess.run(["vvp", "rtl.vvp", "+UIN=%d" % uin, "+BITS=%d" % bits, "+LEN=%d" % m,
                    "+MODE=%d" % mode, "+CONST=%d" % const, "+WORD=%d" % word, "+NPER=%d" % nper,
                    "+RAMP=%d" % ramp, "+OUT=" + name], capture_output=True, text=True, cwd=BUILD, check=True)
    with open(os.path.join(BUILD, name)) as f:
        return [(int(p[1]), int(p[2])) for p in (line.split() for line in f)]


def high_per_period(rows):
    """PWM_HIGH cycles of each period. A period starts at a PWM_HIGH rising edge."""
    out, prev, cur = [], 0, None
    for h, _ in rows:
        if h and not prev:
            cur = [0]
            out.append(cur)
        if cur is not None:
            cur[0] += h
        prev = h
    return [c[0] for c in out]


def static_case(args):
    uin, bits, m, mode, const, word = args
    nper = max(2 ** m * 2, 8) + 6
    a = high_per_period(run_vhdl(uin, bits, m, mode, const, word, nper))[2:]   # VHDL: first full period has k = 1
    b = high_per_period(run_rtl(uin, bits, m, mode, const, word, nper))[1:]    # RTL: period 0 is a start-up period
    n = min(len(a), len(b)) - 1
    a, b = a[:n], b[:n]
    full = (n // 2 ** m) * 2 ** m
    model = vhdl_sequence([uin] * (n + 1), bits, m, mode, const, word)[1:]
    if a == b:
        kind = "="
    elif sorted(a[:full]) == sorted(b[:full]):
        kind = "P"
    elif sum(a[:full]) == sum(b[:full]):
        kind = "M"
    else:
        kind = "X"
    return args, kind, a == model


def dynamic_case(args):
    bits, m, mode, start = args
    nper = 600
    a = high_per_period(run_vhdl(start, bits, m, mode, 0, 0, nper, 1))
    b = high_per_period(run_rtl(start, bits, m, mode, 0, 0, nper, 1))
    best = None
    for sa in range(0, 5):          # the two benches differ by 0..4 periods at start-up
        for sb in range(0, 4):
            n = min(len(a) - sa, len(b) - sb) - 2
            diff = sum(1 for i in range(n) if a[sa + i] != b[sb + i])
            if best is None or diff < best[0]:
                best = (diff, n)
    return args, best


def normal_case(bits):
    """Normal mode, control word ramp 0..4095: PWM_HIGH and PWM_LOW of every clock must be equal."""
    nper = 4100
    ra = run_vhdl(0, bits, 0, 0, 0, 0, nper, 1)
    rb = run_rtl(0, bits, 0, 0, 0, 0, nper, 1)

    def start(rows, k):
        prev, count = 0, 0
        for i, (h, _) in enumerate(rows):
            if h and not prev:
                count += 1
                if count == k:
                    return i
            prev = h

    wa = ra[start(ra, 3):]       # start-up differs (E7): VHDL 3rd period, RTL 2nd period
    wb = rb[start(rb, 2):]
    n = min(len(wa), len(wb))
    return bits, n // 513, sum(1 for i in range(n) if wa[i] != wb[i])


def main():
    global DUT
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("kind", choices=("static", "dynamic", "normal"))
    ap.add_argument("--dut", choices=sorted(CORES), default="submitted")
    ap.add_argument("--const", action="store_true", help="use the constant dyadic word (static)")
    ap.add_argument("--jobs", type=int, default=os.cpu_count() or 1)
    ap.add_argument("--seed", type=int, default=7)
    opt = ap.parse_args()
    DUT = opt.dut
    build(opt.dut)
    rnd = random.Random(opt.seed)
    ctx = get_context("fork")
    if opt.kind == "normal":
        with ctx.Pool(opt.jobs) as pool:
            res = pool.map(normal_case, range(5, 10))
        for bits, periods, diff in res:
            print("bits=%d: %d periods compared (PWM_HIGH and PWM_LOW of every clock): %d differences" % (bits, periods, diff))
        sys.exit(0 if all(diff == 0 for _, _, diff in res) else 1)
    if opt.kind == "static":
        jobs = [(rnd.randrange(4096), bits, m, mode, int(opt.const), rnd.randrange(128))
                for mode in (1, 2, 3, 4) for bits in range(5, 10) for m in range(1, 8) for _ in range(3)]
        with ctx.Pool(opt.jobs) as pool:
            res = pool.map(static_case, jobs)
        table = collections.defaultdict(list)
        model_ok = 0
        for (uin, bits, m, mode, const, word), kind, ok in res:
            table[(mode, bits, m)].append(kind)
            model_ok += ok
        print("DUT = %s%s. Cells: 3 random control words each." % (opt.dut, ", constant word" if opt.const else ""))
        for mode in (1, 2, 3, 4):
            print("mode %d   m: %s" % (mode, " ".join("%4d" % m for m in range(1, 8))))
            for bits in range(5, 10):
                print("  bits %d   " % bits + " ".join("%4s" % "".join(sorted(table[(mode, bits, m)]))
                                                      for m in range(1, 8)))
        counts = collections.Counter(k for _, k, _ in res)
        print("cases: %d   =: %d  P: %d  M: %d  X: %d" % (len(res), counts["="], counts["P"], counts["M"], counts["X"]))
        print("Python model equals the VHDL in %d of %d cases" % (model_ok, len(res)))
        bad = len(res) - counts["="]
        sys.exit(0 if (bad == 0 or opt.dut == "submitted") and model_ok == len(res) else 1)
    else:
        jobs = [(bits, m, mode, start) for (bits, m, start) in ((8, 4, 0x400), (9, 3, 0x7F0), (6, 6, 0x100), (5, 7, 0xA00))
                for mode in (1, 2, 3, 4)]
        with ctx.Pool(opt.jobs) as pool:
            res = pool.map(dynamic_case, jobs)
        worst = 0
        for (bits, m, mode, start), (diff, n) in res:
            print("bits=%d m=%d mode=%d start=0x%03x: %d of %d periods differ" % (bits, m, mode, start, diff, n))
            worst = max(worst, diff)
        sys.exit(0 if worst == 0 or opt.dut == "submitted" else 1)


if __name__ == "__main__":
    main()
