"""Optional dither fix E3: build with -DDYADIC_UNBIASED_DITHER.

The average over one 2^m window must be exactly value / 2^m in dither modes 2..4.
"""

import random

import cocotb

from chip import ctrl_regs, duty_codes, run_words, window


@cocotb.test()
async def test_unbiased_dither_average(dut):
    rnd = random.Random(11)
    for mode in (2, 3, 4):
        for bits, m in ((8, 4), (7, 3), (9, 2), (6, 5), (5, 7)):
            top = ((1 << bits) - 2) << m          # stay away from the saturation corner
            for value in (0, 1, rnd.randrange(1, top), top):
                word = value << (12 - bits - m)      # VHDL layout: fraction directly below the base duty
                n = 2 * (1 << m) + 2
                got = await run_words(dut, ctrl_regs(m, mode, False, bits), lambda j: word, n)
                total = sum(window(duty_codes(got, bits), m, which=1))
                assert total == value, "mode=%d bits=%d m=%d value=%d got=%d" % (mode, bits, m, value, total)
