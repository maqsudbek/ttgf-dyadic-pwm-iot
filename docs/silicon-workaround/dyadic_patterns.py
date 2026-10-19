#!/usr/bin/env python3
"""Which period gets the +1 in dyadic mode: the papers, and the chip (GF26a, commit 750f492).

Self-contained. No packages needed.
  python3 dyadic_patterns.py owners [M]   table: owner bit of every period (papers and chip)
  python3 dyadic_patterns.py example [M] VALUE   +1 pattern of one value, both rules
  python3 dyadic_patterns.py tones [M]    strongest low-frequency tone of every value
  python3 dyadic_patterns.py static [M]   how many values a static word can fix on the chip
"""
import cmath
import sys


def owner_papers(c, M):
    """Data bit used in period c (papers, TPEL 2020 eq. 11): D[M-1-k], k = lowest set bit of c."""
    if c == 0:
        return None
    k = (c & -c).bit_length() - 1
    return M - 1 - k


def owner_chip(c, M):
    """Data bit used in period c by the chip: D[h], h = highest set bit of c."""
    return None if c == 0 else c.bit_length() - 1


def frame(rule, M, value):
    own = owner_papers if rule == "papers" else owner_chip
    return [0 if own(c, M) is None else (value >> own(c, M)) & 1 for c in range(1 << M)]


def thermo(M, value):
    """Papers' thermometric rule: +1 in the first `value` periods."""
    return [int(c < value) for c in range(1 << M)]


def tone(pattern):
    """Strongest tone at the frame rate (k=1) or twice the frame rate (k=2), in high-resolution LSB."""
    n = len(pattern)
    mu = sum(pattern) / n
    return max(abs(sum((pattern[c] - mu) * cmath.exp(-2j * cmath.pi * k * c / n)
                       for c in range(n))) / n for k in (1, 2))


def row(label, cells, w=3):
    return "| %-8s | %s |" % (label, " | ".join("%-*s" % (w, x) for x in cells))


def cmd_owners(M):
    n = 1 << M
    hdr = ["period"] + [str(c) for c in range(n)]
    name = lambda o: "-" if o is None else "D%d" % o
    print(row(hdr[0], hdr[1:]))
    print("|" + "---|" * (n + 1))
    print(row("binary", [format(c, "0%db" % M) for c in range(n)], M))
    print(row("papers", [name(owner_papers(c, M)) for c in range(n)], M))
    print(row("chip", [name(owner_chip(c, M)) for c in range(n)], M))


def cmd_example(M, value):
    n = 1 << M
    print("value %s (D%d..D0), %d periods" % (format(value, "0%db" % M), M - 1, n))
    print(row("period", [str(c) for c in range(n)]))
    for rule in ("papers", "chip"):
        print(row(rule, ["+1" if b else "." for b in frame(rule, M, value)]))
    print(row("thermo", ["+1" if b else "." for b in thermo(M, value)]))


def cmd_tones(M):
    n = 1 << M
    print("| value | papers | chip | thermometric |\n|---|---|---|---|")
    tot = [0.0, 0.0, 0.0]
    for v in range(n):
        t = [tone(frame("papers", M, v)), tone(frame("chip", M, v)), tone(thermo(M, v))]
        tot = [a + b for a, b in zip(tot, t)]
        print("| %d | %.3f | %.3f | %.3f |" % (v, *t))
    print("| mean | %.3f | %.3f | %.3f |" % tuple(x / n for x in tot))


def cmd_static(M):
    n = 1 << M
    good = [v for v in range(n)
            if any(frame("chip", M, w) == frame("papers", M, v) for w in range(n))]
    print("M=%d: %d of %d values can be made on the chip with a static word: %s"
          % (M, len(good), n, good if n <= 32 else "..."))


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    M = int(a[1]) if len(a) > 1 else 4
    if a[0] == "owners":
        cmd_owners(M)
    elif a[0] == "example":
        cmd_example(int(a[1]), int(a[2], 0))
    elif a[0] == "tones":
        cmd_tones(M)
    elif a[0] == "static":
        cmd_static(M)
    else:
        sys.exit(__doc__)
