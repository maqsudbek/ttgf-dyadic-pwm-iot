"""The corrected RTL (docs/errata/rtl/dyadic_fixed.v) must match dpwm.vhd.

The reference is the Python model of the VHDL (vhdl_model.py). Every mode, width
and word length is compared period by period.
"""

import random

import cocotb

from chip import ctrl_regs, host, model_high, run_words

MODES = (1, 2, 3, 4)


def n_periods(m):
    return min(2 * (1 << m), 140)


async def compare(dut, bits, m, mode, words, const=False, word=0):
    n = len(words)
    regs = ctrl_regs(m, mode, const, bits, word if const else None)
    got = await run_words(dut, regs, lambda j: words[j - 1], n)
    exp = model_high(words, bits, m, mode, int(const), word)
    assert got == exp, (
        "bits=%d m=%d mode=%d const=%s\n got %s\n exp %s" % (bits, m, mode, const, got[:24], exp[:24])
    )


@cocotb.test()
async def test_static_control_all_modes(dut):
    """Fixed control word: all modes x widths 5..9 x lengths 1..7 equal the VHDL model."""
    rnd = random.Random(2024)
    count = 0
    for mode in MODES:
        for bits in range(5, 10):
            for m in range(1, 8):
                control = rnd.randrange(4096)
                n = n_periods(m)
                await compare(dut, bits, m, mode, [control] * n)
                count += 1
    dut._log.info("%d static cases equal to the VHDL model", count)


@cocotb.test()
async def test_changing_control_all_modes(dut):
    """New random control word every period: sample-and-hold of modes 3 and 4 equals the VHDL model."""
    rnd = random.Random(77)
    count = 0
    for mode in MODES:
        for bits, m in ((5, 7), (6, 3), (7, 2), (8, 4), (9, 1), (9, 3), (8, 1), (6, 5)):
            n = min(n_periods(m), 70)
            await compare(dut, bits, m, mode, [rnd.randrange(4096) for _ in range(n)])
            count += 1
    dut._log.info("%d dynamic cases equal to the VHDL model", count)


@cocotb.test()
async def test_constant_word_all_lengths(dut):
    """Constant dyadic word (including m = 1, where the VHDL ignores it) equals the VHDL model."""
    rnd = random.Random(5)
    count = 0
    for bits in range(5, 10):
        for m in range(1, 8):
            control = rnd.randrange(4096)
            word = rnd.randrange(1, 128) | 1   # bit 0 set: this exposes E5 at m = 1
            n = n_periods(m)
            await compare(dut, bits, m, 1, [control] * n, const=True, word=word)
            count += 1
    dut._log.info("%d constant-word cases equal to the VHDL model", count)


@cocotb.test()
async def test_normal_mode_unchanged(dut):
    """Normal mode (m = 0) is still the same for every width and a ramp of control words."""
    for bits in range(5, 10):
        words = [(c * 53) & 0xFFF for c in range(1, 70)]
        regs = [(host.CFG_BITS, host.cfg_bits_data(bits))]
        got = await run_words(dut, regs, lambda j: words[j - 1], len(words))
        exp = model_high(words, bits, 0, 0)
        assert got == exp, "normal mode, bits=%d" % bits
