"""Host-side helpers for the taped-out chip tt_um_maqsudbek_dyadic_pwm.

Use this file to work around the known errata of the chip (see docs/errata/README.md).
The file runs on MicroPython (RP2 microcontroller of the Tiny Tapeout demo board) and on
CPython (PC, tests). It uses no typing, no dataclasses and no standard library
module that MicroPython lacks. The board helpers are at the end of the file.

Terms
    bits   PWM width in the chip (5..9).
    m      dyadic/dither word length (1..7).
    value  duty with m extra fraction bits: a (bits + m)-bit integer.
           value / 2^m is the duty in units of one base step.
    word   the 12-bit control word. The pins carry it as
           ui_in[7:0] = word[11:4] and uio_in[3:0] = word[3:0].
"""

import time

PROJECT = "tt_um_maqsudbek_dyadic_pwm"

# Config register addresses (uio_in[6:4]) and mode codes (data[5:3] of register 0)
CFG_CTRL = 0
CFG_BITS = 1
CFG_WORD = 2

MODE_NORMAL = 0
MODE_DYADIC = 1
MODE_DITHER_V1 = 2
MODE_DITHER_V2 = 3
MODE_DITHER_V3 = 4

PERIOD_CLOCKS = 513   # clock cycles per switching period

_BITS_SEL = {5: 0, 6: 1, 7: 2, 8: 3, 9: 4}


def max_len(bits):
    """Largest m for which the fraction does not overlap the base duty (E4)."""
    return min(7, 12 - bits)


def cfg_ctrl_data(m, mode, const=False):
    """Data byte for config register 0."""
    return (m & 7) | ((mode & 7) << 3) | ((1 << 6) if const else 0)


def cfg_bits_data(bits):
    """Data byte for config register 1."""
    return _BITS_SEL[bits]


# ---------------------------------------------------------------------------
# Workaround for E2: pin layout of the fraction bits
# ---------------------------------------------------------------------------
def control_word(value, bits, m):
    """12-bit control word for the chip, for use with the chip's own dyadic mode.

    The base duty goes to the top `bits` bits. The m fraction bits go to the
    LOWEST m bits of the word (uio_in[3:0], then ui_in[2:0] when m > 4). The
    bits between the two fields are not used.
    """
    if not 5 <= bits <= 9:
        raise ValueError("bits must be 5..9")
    if not 0 <= m <= max_len(bits):
        raise ValueError("m must be 0..%d for %d-bit PWM" % (max_len(bits), bits))
    if not 0 <= value < (1 << (bits + m)):
        raise ValueError("value out of range")
    base = value >> m
    frac = value & ((1 << m) - 1)
    return (base << (12 - bits)) | frac


def dither_control_word(value, bits, m):
    """Control word for the chip's dither modes 2..4 (workaround for E3).

    The chip adds (lsb + 1) / 2^m in the dither modes. Send value - 1 to get
    `value`. The value 0 cannot be reached: the chip then gives 1 / 2^m.
    """
    return control_word(max(value - 1, 0), bits, m)


def split_pins(word):
    """Return (ui_in, uio_in) for a 12-bit control word. uio_in[7] stays 0 (run mode)."""
    return (word >> 4) & 0xFF, word & 0x0F


# ---------------------------------------------------------------------------
# Workaround for E1: dyadic modulation in the host (Normal mode in the chip)
# ---------------------------------------------------------------------------
def dyadic_add(frac, m, k):
    """The +1 flag of window position k, in the order of dpwm.vhd (lowest set bit)."""
    k &= (1 << m) - 1
    if k == 0:
        return 0
    j = 0
    while not (k >> j) & 1:
        j += 1
    return (frac >> (m - 1 - j)) & 1


class SoftDyadic:
    """Host-side dyadic modulator. The chip runs in Normal mode (register 0 = 0).

    Call next_word() once per switching period. It returns the control word
    for the next period. The result is the same as dpwm.vhd in dyadic mode.
    """

    def __init__(self, bits, m):
        if not 0 <= m <= max_len(bits):
            raise ValueError("m must be 0..%d for %d-bit PWM" % (max_len(bits), bits))
        self.bits = bits
        self.m = m
        self.k = 0

    def next_duty(self, value):
        """Duty code (a `bits`-bit integer) for the next period."""
        m = self.m
        base = value >> m
        frac = value & ((1 << m) - 1)
        duty = base + dyadic_add(frac, m, self.k)
        self.k = (self.k + 1) & ((1 << m) - 1) if m else 0
        top = (1 << self.bits) - 1
        return top if duty > top else duty

    def next_word(self, value):
        return self.next_duty(value) << (12 - self.bits)


# ---------------------------------------------------------------------------
# Board helpers. `tt` is the Tiny Tapeout demo-board object of the MicroPython SDK.
# ---------------------------------------------------------------------------
def _ticks_us():
    try:
        return time.ticks_us()
    except AttributeError:          # CPython
        return int(time.monotonic() * 1000000)


def _ticks_diff(a, b):
    try:
        return time.ticks_diff(a, b)
    except AttributeError:          # CPython
        return a - b


def safe_clock_hz(loop_us):
    """Highest project clock for the host loop, from the measured time of one loop pass.

    The host must see the sync edge and write the control word in the same period.
    About 500 of the 513 clocks are usable. The host can need two loop passes: one to
    see the edge and one to write. The function adds a safety factor of 4.
    """
    return int(500000000 / (8 * loop_us))


class Chip:
    """Safe access to the chip through the demo board object `tt`.

    Rules that this class follows (see docs/errata/workaround-guide.md):
      * The RP2 must drive the uio pins. It sets uio_oe_pico = 0xFF.
      * The clock is stopped while a config register is written (single step).
      * uio_in[7] (config strobe) is 0 in run mode.
    """

    def __init__(self, tt, clock_hz=100000):
        self.tt = tt
        self.clock_hz = clock_hz
        self.word = 0
        self.bits = 8
        self.m = 0
        self.mode = MODE_NORMAL
        self.late_periods = 0

    # -- pins ----------------------------------------------------------------
    def set_word(self, word):
        """Drive the 12-bit control word on the run-mode pins."""
        ui, uio = split_pins(word)
        self.word = word
        self.tt.ui_in.value = ui
        self.tt.uio_in.value = uio

    def sync(self):
        """Level of uo_out[2] (sync clock). It rises at the start of each period."""
        return (int(self.tt.uo_out.value) >> 2) & 1

    # -- configuration -------------------------------------------------------
    def write_cfg(self, addr, data):
        """Write one config register. Stops the clock, single-steps one edge, restarts the clock."""
        tt = self.tt
        running = tt.is_auto_clocking
        if running:
            tt.clock_project_stop()
        tt.ui_in.value = data & 0xFF
        tt.uio_in.value = 0x80 | ((addr & 7) << 4)
        tt.clock_project_once()             # one rising edge writes the register
        self.set_word(self.word)            # back to run mode. The clock is stopped: no edge sees a mixed state.
        if running:
            tt.clock_project_PWM(self.clock_hz)

    def start(self, bits=8, m=0, mode=MODE_NORMAL, const=False, word=0):
        """Select the project, reset it, write the config registers, start the clock."""
        if bits not in _BITS_SEL:
            raise ValueError("bits must be 5..9")
        if not 0 <= m <= max_len(bits):
            raise ValueError("m must be 0..%d for %d-bit PWM" % (max_len(bits), bits))
        if not 0 <= mode <= MODE_DITHER_V3:
            raise ValueError("mode must be 0..4")
        tt = self.tt
        getattr(tt.shuttle, PROJECT).enable()
        try:
            from ttboard.mode import RPMode
            tt.mode = RPMode.ASIC_RP_CONTROL
        except ImportError:                 # no SDK (PC or test)
            pass
        tt.clock_project_stop()             # enable() starts the clock at 50 MHz
        tt.uio_oe_pico.value = 0xFF         # the RP2 drives all uio pins
        tt.ui_in.value = 0
        tt.uio_in.value = 0
        tt.reset_project(True)
        time.sleep(0.002)
        tt.reset_project(False)
        time.sleep(0.002)
        self.word = 0
        self.write_cfg(CFG_BITS, cfg_bits_data(bits))
        if const:
            self.write_cfg(CFG_WORD, word)
        self.write_cfg(CFG_CTRL, cfg_ctrl_data(m, mode, const))   # last: modulation starts here
        self.bits, self.m, self.mode = bits, m, mode
        tt.clock_project_PWM(self.clock_hz)

    # -- host-side dyadic modulation (workaround for E1) ----------------------
    def run_soft_dyadic(self, next_value, m, periods=0):
        """Dyadic modulation in the host. The chip must run in Normal mode.

        next_value() returns the duty value ((bits + m)-bit integer) for the next
        period. The loop runs `periods` periods, or for ever when periods = 0.
        self.late_periods counts periods that the loop saw too late.
        """
        if self.mode != MODE_NORMAL or self.m != 0:
            raise ValueError("start the chip in Normal mode (m = 0, mode = 0) first")
        soft = SoftDyadic(self.bits, m)
        self.set_word(soft.next_word(next_value()))
        period_us = PERIOD_CLOCKS * 1000000 // self.clock_hz
        prev = self.sync()
        last = _ticks_us()
        n = 0
        while periods == 0 or n < periods:
            cur = self.sync()
            if cur and not prev:
                now = _ticks_us()
                gap = _ticks_diff(now, last)
                if gap > period_us * 3 // 2:
                    self.late_periods += gap // period_us - 1
                last = now
                self.set_word(soft.next_word(next_value()))
                n += 1
            prev = cur

    def measure_loop_us(self, passes=200):
        """Time of one loop pass (one sync read and one control-word write) in microseconds."""
        start = _ticks_us()
        for _ in range(passes):
            self.sync()
            self.set_word(self.word)
        return _ticks_diff(_ticks_us(), start) / passes
