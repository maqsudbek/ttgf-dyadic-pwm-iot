"""Tests on the SUBMITTED RTL (src/dyadic.v).

Each errata item is shown (characterisation) and its workaround is checked.
The reference is the Python model of dpwm.vhd (vhdl_model.py).
"""

import random

import cocotb
from cocotb.triggers import FallingEdge, Timer

import dyadic_host as host
from chip import (CLK_NS, collect, ctrl_regs, duty_codes, model_high, ripple,
                  run_words, set_word, start_chip, window)

MODE_DYADIC = host.MODE_DYADIC


def total(highs, bits, m, which=1):
    return sum(window(duty_codes(highs, bits), m, which=which))


# ---------------------------------------------------------------------------
# E1: dyadic order
# ---------------------------------------------------------------------------
@cocotb.test()
async def test_e1_order_differs_but_average_is_equal(dut):
    """8-bit, m = 4, fraction 8: same average as the VHDL, but one burst instead of alternation."""
    bits, m, word = 8, 4, (100 << 4) | 8
    n = 3 * (1 << m)
    got = await run_words(dut, ctrl_regs(m, MODE_DYADIC), lambda j: word, n)
    exp = model_high([word] * n, bits, m, MODE_DYADIC)
    g, e = window(got, m, which=1), window(exp, m, which=1)
    assert sorted(g) == sorted(e), "same multiset: the average duty is correct"
    assert g != e, "E1: the order differs from the VHDL"
    # silicon: 8 equal periods in a row, then 8 boosted periods. VHDL: alternation.
    assert g == [201] * 8 + [203] * 8, g
    assert e == [201, 203] * 8, e
    ideal = 100 + 8 / 16
    r_chip = ripple(window(duty_codes(got, bits), m), ideal)
    r_vhdl = ripple(window(duty_codes(exp, bits), m), ideal)
    dut._log.info("E1 ripple (base steps x periods): chip %.2f, VHDL %.2f", r_chip, r_vhdl)
    assert r_chip > 3 * r_vhdl


@cocotb.test()
async def test_e1_workaround_host_dyadic_is_exact(dut):
    """Chip in Normal mode + SoftDyadic in the host = dpwm.vhd, period by period."""
    rnd = random.Random(31)
    cases = 0
    for bits in range(5, 10):
        for m in range(1, host.max_len(bits) + 1):
            n = min(2 * (1 << m), 140)
            values = [rnd.randrange(1 << (bits + m)) for _ in range(n + 1)]
            soft = host.SoftDyadic(bits, m)
            words = [soft.next_word(v) for v in values]          # words[j] is for period j
            regs = [(host.CFG_BITS, host.cfg_bits_data(bits))]
            got = await run_words(dut, regs, lambda j: words[j], n)
            vhdl_words = [v << (12 - bits - m) for v in values]  # contiguous layout of the VHDL
            exp = model_high(vhdl_words[1:], bits, m, MODE_DYADIC)
            assert got == exp, "bits=%d m=%d\n got %s\n exp %s" % (bits, m, got[:20], exp[:20])
            cases += 1
    dut._log.info("%d width/length cases: host dyadic equals the VHDL", cases)


# ---------------------------------------------------------------------------
# E2: source bits of the LSB word
# ---------------------------------------------------------------------------
@cocotb.test()
async def test_e2_pin_layout(dut):
    """Fraction in the lowest bits (host.control_word) gives the VHDL average. The VHDL layout does not."""
    rnd = random.Random(9)
    wrong_with_vhdl_layout = 0
    for bits in range(5, 10):
        for m in range(1, host.max_len(bits) + 1):
            value = rnd.randrange(1, ((1 << bits) - 2) << m)        # no saturation (E3 test only)
            n = 2 * (1 << m) + 1
            # (a) workaround layout
            w = host.control_word(value, bits, m)
            got = await run_words(dut, ctrl_regs(m, MODE_DYADIC, False, bits), lambda j: w, n)
            exp = model_high([value << (12 - bits - m)] * n, bits, m, MODE_DYADIC)
            assert total(got, bits, m) == value
            assert sorted(window(got, m)) == sorted(window(exp, m)), "bits=%d m=%d" % (bits, m)
            # (b) VHDL layout (fraction directly below the base duty)
            v = value << (12 - bits - m)
            got2 = await run_words(dut, ctrl_regs(m, MODE_DYADIC, False, bits), lambda j: v, n)
            if bits + m < 12 and total(got2, bits, m) != value:
                wrong_with_vhdl_layout += 1
    dut._log.info("E2: %d width/length cases are wrong with the VHDL layout", wrong_with_vhdl_layout)
    assert wrong_with_vhdl_layout >= 10


# ---------------------------------------------------------------------------
# E3: dither bias
# ---------------------------------------------------------------------------
@cocotb.test()
async def test_e3_dither_bias_and_workaround(dut):
    rnd = random.Random(3)
    for mode in (2, 3, 4):
        for bits, m in ((8, 4), (7, 3), (9, 2), (6, 5)):
            n = 2 * (1 << m) + 2
            value = rnd.randrange(1, ((1 << bits) - 2) << m)       # no saturation
            regs = ctrl_regs(m, mode, False, bits)
            naive = host.control_word(value, bits, m)
            got = await run_words(dut, regs, lambda j: naive, n)
            assert total(got, bits, m) == value + 1, "E3: the chip adds 1/2^m (mode %d)" % mode
            fixed = host.dither_control_word(value, bits, m)
            got = await run_words(dut, regs, lambda j: fixed, n)
            assert total(got, bits, m) == value, "workaround: send value - 1 (mode %d)" % mode


# ---------------------------------------------------------------------------
# E5: constant word with m = 1
# ---------------------------------------------------------------------------
@cocotb.test()
async def test_e5_constant_word_m1(dut):
    bits, m, word = 8, 1, (60 << 4)
    n = 12
    got = await run_words(dut, ctrl_regs(m, MODE_DYADIC, True, bits, 0x7F), lambda j: word, n)
    assert total(got, bits, m) == 2 * 60 + 1, "E5: the chip uses bit 0 of the constant word"
    got = await run_words(dut, ctrl_regs(m, MODE_DYADIC, True, bits, 0x7E), lambda j: word, n)
    exp = model_high([word] * n, bits, m, MODE_DYADIC, 1, 0x7F)
    assert got == exp and total(got, bits, m) == 2 * 60, "workaround: keep bit 0 of the word at 0"


# ---------------------------------------------------------------------------
# E6: config-write pin order
# ---------------------------------------------------------------------------
@cocotb.test()
async def test_e6_config_pin_order(dut):
    reg = dut.user_project.u_dyadic_pwm.pwm_bits_sel
    await start_chip(dut)
    assert int(reg.value) == 3

    async def write(first_then):
        await FallingEdge(dut.clk)
        dut.uio_in.value = 0x80 | (host.CFG_BITS << 4)
        dut.ui_in.value = 0x04                      # width 9 bit
        await Timer(CLK_NS, unit="ns")
        first_then()
        await Timer(CLK_NS, unit="ns")

    # Unsafe: ui_in changes to the control MSBs while the strobe is still high.
    def unsafe():
        dut.ui_in.value = 0x80
    await write(unsafe)
    dut.uio_in.value = 0
    await Timer(CLK_NS, unit="ns")
    assert int(reg.value) == 0, "E6: the register took the control byte (0x80 & 7 = 0)"

    # Safe: the strobe falls first, then ui_in changes.
    def safe():
        dut.uio_in.value = 0
        dut.ui_in.value = 0x80
    await write(safe)
    await Timer(CLK_NS, unit="ns")
    assert int(reg.value) == 4, "safe order keeps the written value"
