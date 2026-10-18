"""Shared helpers for the errata tests (cocotb 2.x, tb_errata.v)."""

import os
import sys

from cocotb.triggers import FallingEdge, RisingEdge, Timer

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "host"))

import dyadic_host as host  # noqa: E402
from vhdl_model import duty_from_high, vhdl_sequence  # noqa: E402,F401

CLK_NS = 20
PERIOD = 513


def ctrl_regs(m, mode, const=False, bits=None, word=None):
    """Config writes (addr, data) for a test case."""
    regs = [(host.CFG_CTRL, host.cfg_ctrl_data(m, mode, const))]
    if bits is not None:
        regs.append((host.CFG_BITS, host.cfg_bits_data(bits)))
    if word is not None:
        regs.append((host.CFG_WORD, word))
    return regs


def set_word(dut, word):
    """Drive the run-mode pins (uio_in[7] = 0)."""
    ui, uio = host.split_pins(word)
    dut.ui_in.value = ui
    dut.uio_in.value = uio


async def start_chip(dut, regs=(), word=0):
    """Reset the chip, write the config registers, then drive the run-mode pins.

    All pin changes happen on a falling clock edge. The first config write is
    made together with the reset release.
    """
    await FallingEdge(dut.clk)
    dut.rst_n.value = 0
    dut.ui_in.value = 0
    dut.uio_in.value = 0
    await Timer(3 * CLK_NS, unit="ns")
    dut.rst_n.value = 1
    for addr, data in regs:
        dut.uio_in.value = 0x80 | ((addr & 7) << 4)
        dut.ui_in.value = data & 0xFF
        await Timer(CLK_NS, unit="ns")
    set_word(dut, word)


async def collect(dut, n, first=1, hook=None):
    """HIGH cycles of periods first .. first+n-1.

    hook(j) runs 5.5 clocks after the start of period j. A control word that the
    hook writes is used by period j+1.
    """
    out = {}
    last = first + n - 1
    for _ in range(n + 8):          # a period that never ends is an error, not a hang
        await RisingEdge(dut.sync_w)
        await Timer(11 * CLK_NS // 2, unit="ns")
        j = int(dut.started.value) - 1
        if hook is not None:
            hook(j)
        idx = int(dut.last_index.value)
        if idx >= first:
            out[idx] = int(dut.last_high.value)
        if last in out:
            break
    assert last in out, "the sync output stopped before period %d" % last
    return [out[i] for i in range(first, first + n)]


async def run_words(dut, regs, word_for, n):
    """Run the chip with control word word_for(j) in period j. Return HIGH counts of periods 1..n."""
    await start_chip(dut, regs, word_for(1))
    return await collect(dut, n, hook=lambda j: set_word(dut, word_for(min(j + 1, n))))


def model_high(words_by_period, bits, m, mode, const=0, word=0):
    """dpwm.vhd model for periods 1..n. words_by_period[j-1] is the word of period j."""
    seq = vhdl_sequence([0] + list(words_by_period), bits, m, mode, const, word)
    return seq[1:]


def duty_codes(highs, bits):
    return [int(duty_from_high(h, bits)) for h in highs]


def window(seq, m, start_period=1, which=1):
    """Periods of one full 2^m window (index `which`, window 0 holds period 0)."""
    size = 1 << m
    lo = which * size - start_period
    return seq[lo:lo + size]


def ripple(duty_seq, ideal):
    """Largest accumulated error (in base steps x periods) over one window."""
    acc = 0.0
    worst = 0.0
    for d in duty_seq:
        acc += d - ideal
        worst = max(worst, abs(acc))
    return worst
