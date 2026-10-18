"""Plain-Python tests of docs/errata/host/dyadic_host.py (no simulator).

Run: python -m pytest test_host.py
The board class is tested with a mock of the Tiny Tapeout `tt` object.
These tests do not use real hardware.
"""

import os
import random
import sys
import types

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "host"))
sys.path.insert(0, HERE)

import dyadic_host as h  # noqa: E402
from vhdl_model import vhdl_sequence  # noqa: E402


# --------------------------------------------------------------------------- layout
def test_control_word_layout_is_what_the_chip_reads():
    rnd = random.Random(1)
    for bits in range(5, 10):
        for m in range(0, h.max_len(bits) + 1):
            for _ in range(50):
                value = rnd.randrange(1 << (bits + m))
                w = h.control_word(value, bits, m)
                assert w < 4096
                assert w >> (12 - bits) == value >> m              # the chip reads the base duty here
                assert w & ((1 << m) - 1) == value & ((1 << m) - 1)  # and the fraction here


def test_control_word_limits():
    assert h.max_len(8) == 4 and h.max_len(9) == 3 and h.max_len(5) == 7
    with pytest.raises(ValueError):
        h.control_word(0, 8, 5)       # E4: the fraction would overlap the base duty
    with pytest.raises(ValueError):
        h.control_word(1 << 12, 8, 4)


def test_split_pins_keeps_run_mode():
    ui, uio = h.split_pins(0xABC)
    assert (ui, uio) == (0xAB, 0xC)
    assert uio & 0x80 == 0


def test_dither_control_word_subtracts_one():
    assert h.dither_control_word(37, 8, 4) == h.control_word(36, 8, 4)
    assert h.dither_control_word(0, 8, 4) == h.control_word(0, 8, 4)


# --------------------------------------------------------------------------- E1
def test_soft_dyadic_equals_vhdl_model():
    rnd = random.Random(2)
    for bits in range(5, 10):
        for m in range(1, h.max_len(bits) + 1):
            n = 3 * (1 << m)
            values = [rnd.randrange(1 << (bits + m)) for _ in range(n)]
            soft = h.SoftDyadic(bits, m)
            duties = [soft.next_duty(v) for v in values]
            vhdl = vhdl_sequence([v << (12 - bits - m) for v in values], bits, m, h.MODE_DYADIC)
            factor = 1 << (9 - bits)
            offset = 1 if factor == 1 else factor // 2
            assert [d * factor + offset for d in duties] == vhdl


def test_dyadic_add_uses_each_bit_2_pow_i_times_and_alternates():
    for m in range(1, 8):
        frac_all = (1 << m) - 1
        adds = [h.dyadic_add(frac_all, m, k) for k in range(1 << m)]
        assert sum(adds) == (1 << m) - 1
        assert adds[1::2] == [1] * (1 << (m - 1))       # the MSB of the word is used in every odd period
        assert adds[0] == 0


def test_soft_dyadic_saturates():
    soft = h.SoftDyadic(8, 4)
    soft.k = 1
    assert soft.next_duty(((1 << 8) - 1) << 4 | 0xF) == 255


# --------------------------------------------------------------------------- board mock
class Port:
    def __init__(self, log, name):
        self._log, self._name, self._v = log, name, 0

    @property
    def value(self):
        return self._v

    @value.setter
    def value(self, v):
        self._v = v
        self._log.append(("set", self._name, v))


class FakeTT:
    def __init__(self):
        self.log = []
        self.ui_in = Port(self.log, "ui_in")
        self.uio_in = Port(self.log, "uio_in")
        self.uio_oe_pico = Port(self.log, "uio_oe_pico")
        self.uo_out = types.SimpleNamespace(value=0)
        self.is_auto_clocking = True
        proj = types.SimpleNamespace(enable=lambda: self.log.append(("enable",)))
        self.shuttle = types.SimpleNamespace(tt_um_maqsudbek_dyadic_pwm=proj)

    def reset_project(self, b):
        self.log.append(("reset", b))

    def clock_project_once(self):
        self.is_auto_clocking = False
        self.log.append(("once", self.ui_in.value, self.uio_in.value))

    def clock_project_PWM(self, hz):
        self.is_auto_clocking = True
        self.log.append(("pwm", hz))

    def clock_project_stop(self):
        self.is_auto_clocking = False
        self.log.append(("stop",))


def names(log):
    return [e[0] if e[0] != "set" else "set:" + e[1] for e in log]


def test_write_cfg_steps_one_clock_with_the_clock_stopped():
    tt = FakeTT()
    chip = h.Chip(tt, 50000)
    chip.word = 0x5A3
    chip.write_cfg(h.CFG_BITS, 4)
    assert names(tt.log)[0] == "stop"
    once = [e for e in tt.log if e[0] == "once"][0]
    assert once[1:] == (4, 0x80 | (h.CFG_BITS << 4))      # data on ui_in, strobe + address on uio_in
    # after the edge: the run pins hold the control word again, strobe low
    assert tt.ui_in.value == 0x5A and tt.uio_in.value == 0x3
    assert tt.log[-1] == ("pwm", 50000)                    # the clock was running before: it runs again


def test_start_sequence():
    tt = FakeTT()
    chip = h.Chip(tt, 100000)
    chip.start(bits=8, m=0, mode=h.MODE_NORMAL)
    n = names(tt.log)
    assert n.index("enable") < n.index("set:uio_oe_pico")
    assert ("set", "uio_oe_pico", 0xFF) in tt.log           # the RP2 must drive the uio pins
    assert n.index("stop") < n.index("set:uio_oe_pico")     # the clock is stopped before the pins change
    first_once = n.index("once")
    assert n.index("reset") < first_once
    assert tt.log[-1] == ("pwm", 100000)
    onces = [e for e in tt.log if e[0] == "once"]
    assert [o[2] >> 4 & 7 for o in onces] == [h.CFG_BITS, h.CFG_CTRL]   # width first, mode/length last


def test_start_with_constant_word_writes_word_before_mode():
    tt = FakeTT()
    h.Chip(tt).start(bits=8, m=4, mode=h.MODE_DYADIC, const=True, word=8)
    addrs = [e[2] >> 4 & 7 for e in tt.log if e[0] == "once"]
    assert addrs == [h.CFG_BITS, h.CFG_WORD, h.CFG_CTRL]


def test_run_soft_dyadic_writes_once_per_sync_rising_edge():
    tt = FakeTT()
    chip = h.Chip(tt, 100000)
    chip.start(bits=8)
    tt.log.clear()
    levels = [0, 0, 4, 4, 4, 0, 0, 4, 0, 4]          # three rising edges after the first read
    state = {"i": 0}

    class Out:
        @property
        def value(self):
            v = levels[min(state["i"], len(levels) - 1)]
            state["i"] += 1
            return v

    tt.uo_out = Out()
    values = iter(range(100, 200))
    chip.run_soft_dyadic(lambda: next(values), m=4, periods=3)
    word_writes = [e for e in tt.log if e[0] == "set" and e[1] == "ui_in"]
    assert len(word_writes) == 1 + 3                  # one for the first period, one per detected edge
    assert tt.uio_in.value & 0x80 == 0                # run mode all the time


def test_run_soft_dyadic_needs_normal_mode():
    tt = FakeTT()
    chip = h.Chip(tt)
    chip.start(bits=8, m=4, mode=h.MODE_DYADIC)
    with pytest.raises(ValueError):
        chip.run_soft_dyadic(lambda: 0, m=4, periods=1)


def test_start_rejects_bad_arguments():
    for kw in ({"bits": 4}, {"bits": 8, "m": 5}, {"bits": 9, "m": 4}, {"mode": 5}):
        tt = FakeTT()
        with pytest.raises(ValueError):
            h.Chip(tt).start(**kw)
        assert tt.log == []                    # nothing is written to the board


def test_safe_clock_hz():
    assert h.safe_clock_hz(100) == 625000
    assert h.safe_clock_hz(1000) == 62500
