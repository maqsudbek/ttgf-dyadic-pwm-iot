#!/usr/bin/env python3
"""Simulate the chip as taped out (commit 750f492) and check what it does, and the workarounds.

Needs: Icarus Verilog (iverilog, vvp) on PATH, and git (to read src/dyadic.v of 750f492).
Run from anywhere:  python3 -I docs/silicon-workaround/check_workarounds.py
Exit code 0 = all checks pass.
"""
import os
import subprocess
import sys
import tempfile

here = os.path.dirname(os.path.abspath(__file__))
repo = os.path.abspath(os.path.join(here, "..", ".."))
sys.path.insert(0, here)
import dyadic_patterns as dp  # noqa: E402

TAPED_OUT = "750f492"


def build(tmp):
    rtl = os.path.join(tmp, "dyadic_taped_out.v")
    with open(rtl, "w") as f:
        f.write(subprocess.run(["git", "-C", repo, "show", "%s:src/dyadic.v" % TAPED_OUT],
                               check=True, capture_output=True, text=True).stdout)
    out = os.path.join(tmp, "chip.vvp")
    subprocess.run(["iverilog", "-g2005", "-o", out, "-s", "tb",
                    os.path.join(here, "tb_chip.v"), rtl], check=True)
    return out


def sim(vvp, **kw):
    args = ["+%s=%s" % (k.upper(), v) for k, v in kw.items()]
    out = subprocess.run(["vvp", "-n", vvp] + args, capture_output=True, text=True, check=True).stdout
    line = [l for l in out.splitlines() if l.startswith("TT")][0]
    return [int(x) for x in line.split()[1:]]


def highs(B, base, pattern):
    """High time of each period: (base + bit) * factor + offset, with factor = 2^(9-B)."""
    fac = 1 << (9 - B)
    off = max(1, fac // 2)
    return [(base + b) * fac + off for b in pattern]


fails = 0


def check(name, ok, detail=""):
    global fails
    fails += 0 if ok else 1
    print("%-4s %s %s" % ("OK" if ok else "FAIL", name, "" if ok else detail))


with tempfile.TemporaryDirectory() as tmp:
    vvp = build(tmp)

    # 1. The chip's dyadic mode uses the highest set bit (the tables in the document).
    for B, M, base, val in ((8, 4, 100, 0b0101), (8, 4, 100, 0b1000), (8, 4, 100, 0b0011), (7, 5, 60, 21)):
        word = (base << M) | val                     # N + M = 12: the lowest M bits are the dyadic bits
        got = sim(vvp, case=0, mode=1, len=M, b=B, word=word)
        check("chip dyadic B=%d M=%d value=%s follows the CHIP rule" % (B, M, format(val, "0%db" % M)),
              got == highs(B, base, dp.frame("chip", M, val)), str(got[:8]))
        check("chip dyadic B=%d M=%d value=%s is NOT the papers' pattern" % (B, M, format(val, "0%db" % M)),
              got != highs(B, base, dp.frame("papers", M, val)) or val in (0, 2 ** M - 1))

    # 2. Error 2: with N + M < 12 the chip reads the lowest M bits, not the bits under the N MSBs.
    B, M, base, val = 5, 4, 11, 0b0101
    right = (base << 7) | (val << 3)                 # as the interface table says: bits 6..3
    low = (base << 7) | val                          # the workaround: bits 3..0
    check("N=5 M=4: value in bits 6..3 is NOT read correctly",
          sim(vvp, case=0, mode=1, len=M, b=B, word=right) != highs(B, base, dp.frame("chip", M, val)))
    check("N=5 M=4: value in bits 3..0 is read (chip rule)",
          sim(vvp, case=0, mode=1, len=M, b=B, word=low) == highs(B, base, dp.frame("chip", M, val)))

    # 3. Thermometric: send D-1 and the +1 comes in the first f periods (papers' rule).
    for B in (5, 6, 7, 8, 9):
        M = 12 - B
        base = 11 if B == 5 else 7
        bad = []
        for f in range(0, 1 << M, max(1, (1 << M) // 16)):
            word = (base << M) + f - 1 if f else (base << M) - 1
            got = sim(vvp, case=0, mode=2, len=M, b=B, word=word)
            if got != highs(B, base, dp.thermo(M, f)):
                bad.append(f)
        check("thermometric, send D-1, B=%d M=%d" % (B, M), not bad, "values %s" % bad)

    # 4. Dyadic with the outside controller in Normal mode: the papers' pattern.
    for B, f in ((8, 5), (8, 8), (8, 1), (8, 15), (9, 5), (7, 21), (6, 37), (5, 100)):
        M = 12 - B
        base = 50 if B >= 7 else 20
        got = sim(vvp, case=1, b=B, n=base, f=f, len=M)
        want = highs(B, base, dp.frame("papers", M, f))
        # the controller starts at any period of the frame: compare the whole cycle
        ok = any(got[:len(want)] == want[j:] + want[:j] for j in range(len(want)))
        check("outside controller, B=%d M=%d value=%d gives the papers' pattern" % (B, M, f), ok, str(got[:10]))

print("result: %s" % ("all pass" if fails == 0 else "%d FAILED" % fails))
sys.exit(1 if fails else 0)
