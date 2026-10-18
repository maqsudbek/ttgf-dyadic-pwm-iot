"""Examples for the demo board. Copy dyadic_host.py to the board, then run this file.

    mpremote fs cp docs/errata/host/dyadic_host.py :dyadic_host.py
    mpremote run docs/errata/host/example_board.py

These examples are NOT tested on real silicon. The logic is tested in simulation
(docs/errata/test). Change EXAMPLE to select an example.
"""

import time

import dyadic_host as h
from ttboard.demoboard import DemoBoard

EXAMPLE = "B"

tt = DemoBoard.get()

if EXAMPLE == "A":
    # A. Plain 8-bit PWM. No errata apply.
    chip = h.Chip(tt, clock_hz=1000000)
    chip.start(bits=8)
    for duty in (0x20, 0x80, 0xE0):
        chip.set_word(duty << 4)
        time.sleep(2)

elif EXAMPLE == "B":
    # B. The chip's own dyadic mode (average is correct, ripple is higher: E1).
    #    8-bit PWM with m = 4: the value has 12 bits. 1234 = 77.125 base steps.
    chip = h.Chip(tt, clock_hz=1000000)
    chip.start(bits=8, m=4, mode=h.MODE_DYADIC)
    chip.set_word(h.control_word(1234, bits=8, m=4))      # E2: fraction in the lowest bits

elif EXAMPLE == "C":
    # C. Host-side dyadic modulation: same result as the VHDL on the FPGA.
    #    The chip runs in Normal mode. The host adds the +1 bit in each period.
    chip = h.Chip(tt, clock_hz=100000)
    chip.start(bits=8)                                    # Normal mode, register 0 = 0
    loop_us = chip.measure_loop_us()
    print("loop pass: %.0f us. Highest safe clock: %d Hz" % (loop_us, h.safe_clock_hz(loop_us)))
    value = [1234]
    chip.run_soft_dyadic(lambda: value[0], m=4, periods=1000)
    print("late periods:", chip.late_periods)             # must be 0

elif EXAMPLE == "D":
    # D. Dither v1 with the E3 correction: send value - 1.
    chip = h.Chip(tt, clock_hz=1000000)
    chip.start(bits=8, m=4, mode=h.MODE_DITHER_V1)
    chip.set_word(h.dither_control_word(1234, bits=8, m=4))
