"""Independent Python model of docs/dyadic_vhdl/dpwm.vhd + pwm_97466hz.vhd.

This model follows the VHDL text, not the Verilog. The tests use it as the
reference ("golden") behaviour. It was also compared with the real VHDL in GHDL
(see docs/errata/verification/).

Period index j = number of switching periods since reset. All VHDL window
counters count periods, so the window position of period j is k = j mod 2^m.
"""

PERIOD = 513
DEAD_TIME = 6


def factor_offset(bits):
    """Scale factor and offset that map a `bits`-bit duty to the 513-cycle period."""
    factor = 1 << (9 - bits)
    offset = 1 if factor == 1 else factor // 2
    return factor, offset


def high_cycles(duty, bits):
    """Number of PWM_HIGH cycles in one period for a given duty code."""
    factor, offset = factor_offset(bits)
    return duty * factor + offset


def duty_from_high(high, bits):
    """Inverse of high_cycles (exact for every legal value)."""
    factor, offset = factor_offset(bits)
    return (high - offset) / factor


def _ctz(k):
    j = 0
    while not (k >> j) & 1:
        j += 1
    return j


class VhdlDpwm:
    """Cycle-per-period model of dpwm.vhd (5..9 bits, modes 0..4)."""

    def __init__(self, bits, m, mode, const=0, word=0):
        self.bits = bits
        self.m = m
        self.mode = mode if m > 0 else 0   # VHDL: LSB length 0 forces Normal mode
        self.const = const
        self.word = word
        self.j = 0
        self.lsb_latch = 0                 # LSB_value_var (initial value 0)
        self.msb_latch = 0                 # MSB_unsigned_var (reads as 0 before first sample)

    def step(self, control):
        """Process one period. Return the duty code (before scaling)."""
        bits, m = self.bits, self.m
        k = self.j % (1 << m) if m else 0
        self.j += 1

        # LSB word: the m bits directly below the base duty (max_allowed_bits rule).
        max_bits = min(bits, 12 - m) if m else bits
        lsb = (control >> (12 - max_bits - m)) & ((1 << m) - 1) if m else 0
        base = control >> (12 - bits)

        add = 0
        if self.mode == 1:                                  # Dyadic
            if k > 0:
                idx = (m - 1) - _ctz(k)
                if not self.const:
                    add = (lsb >> idx) & 1
                elif m >= 2:
                    add = (self.word >> idx) & 1
        elif self.mode == 2:                                # Dither v1
            add = 1 if lsb >= k else 0
        elif self.mode == 3:                                # Dither v2
            if k == 1:
                self.lsb_latch = lsb
            add = 1 if self.lsb_latch >= k else 0
        elif self.mode == 4:                                # Dither v3
            if k == 1:
                self.lsb_latch = lsb
                self.msb_latch = base
            base = self.msb_latch
            add = 1 if self.lsb_latch >= k else 0

        return min(base + add, (1 << bits) - 1)

    def step_high(self, control):
        return high_cycles(self.step(control), self.bits)


def vhdl_sequence(controls, bits, m, mode, const=0, word=0):
    """HIGH cycles for each period j = 0..len(controls)-1."""
    model = VhdlDpwm(bits, m, mode, const, word)
    return [model.step_high(c) for c in controls]
