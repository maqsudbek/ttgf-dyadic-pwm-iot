# SPDX-FileCopyrightText: © 2024 Tiny Tapeout
# SPDX-License-Identifier: Apache-2.0

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, RisingEdge

PWM_PERIOD = 513
DEAD_TIME = 6

# Config register addresses
CFG_CTRL = 0  # data[2:0]=dyadic_len, data[5:3]=dpwm_mode, data[6]=const_dyadic_flag
CFG_BITS = 1  # data[2:0]=pwm_bits_sel (0->5b .. 4->9b)
CFG_WORD = 2  # data[6:0]=dyadic_word


def scaled_duty(ui_val, uio_lsb, bits, add=0):
    """Mirror of the RTL duty->compare scaling for a given control word."""
    control = ((ui_val & 0xFF) << 4) | (uio_lsb & 0xF)
    base = (control >> (12 - bits)) & ((1 << bits) - 1)
    duty_b = min(base + add, (1 << bits) - 1)
    factor = 1 << (9 - bits)
    offset = 1 if factor == 1 else factor >> 1
    return duty_b * factor + offset


async def reset_dut(dut):
    """Apply reset and release into a clean run-mode state."""
    dut.ena.value = 1
    dut.ui_in.value = 0
    dut.uio_in.value = 0
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 10)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 2)


async def write_cfg(dut, addr, data):
    """Write one config register (uio[7]=we, uio[6:4]=addr, ui_in=data)."""
    dut.uio_in.value = 0x80 | ((addr & 0x7) << 4)
    dut.ui_in.value = data & 0xFF
    await ClockCycles(dut.clk, 1)
    # Return to run mode (caller drives control next)
    dut.uio_in.value = 0
    dut.ui_in.value = 0
    await ClockCycles(dut.clk, 1)


async def count_high(dut, periods=1):
    """Count PWM_HIGH cycles over the given number of PWM periods."""
    total = 0
    for _ in range(PWM_PERIOD * periods):
        await RisingEdge(dut.clk)
        if int(dut.uo_out.value) & 0x01:
            total += 1
    return total


@cocotb.test()
async def test_reset(dut):
    """Outputs are low while reset is asserted."""
    clock = Clock(dut.clk, 20, unit="ns")  # 50 MHz
    cocotb.start_soon(clock.start())

    dut.ena.value = 1
    dut.ui_in.value = 0
    dut.uio_in.value = 0
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 10)

    val = int(dut.uo_out.value)
    assert not (val & 0x01), "PWM_HIGH should be 0 during reset"
    assert not (val & 0x02), "PWM_LOW should be 0 during reset"

    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 2)


@cocotb.test()
async def test_normal_default_8bit(dut):
    """Default config is 8-bit normal: MSB=128 -> ~50% duty."""
    clock = Clock(dut.clk, 20, unit="ns")
    cocotb.start_soon(clock.start())
    await reset_dut(dut)

    dut.ui_in.value = 128
    dut.uio_in.value = 0
    await ClockCycles(dut.clk, PWM_PERIOD + 10)

    high = await count_high(dut, 1)
    expected = scaled_duty(128, 0, 8)  # 257
    assert high == expected, f"expected {expected} high cycles, got {high}"


@cocotb.test()
async def test_selectable_widths(dut):
    """Each PWM width (5..9) scales the duty onto the shared 513-cycle period."""
    clock = Clock(dut.clk, 20, unit="ns")
    cocotb.start_soon(clock.start())

    sel = {5: 0, 6: 1, 7: 2, 8: 3, 9: 4}
    for bits in (5, 6, 7, 8, 9):
        await reset_dut(dut)
        await write_cfg(dut, CFG_BITS, sel[bits])

        ui_val = 0x80  # mid-scale control
        dut.ui_in.value = ui_val
        dut.uio_in.value = 0
        await ClockCycles(dut.clk, PWM_PERIOD + 10)

        high = await count_high(dut, 1)
        expected = scaled_duty(ui_val, 0, bits)
        assert high == expected, f"{bits}-bit: expected {expected} high, got {high}"


@cocotb.test()
async def test_normal_max_duty(dut):
    """8-bit max duty: high saturates and low-side stays off (no dead-time room)."""
    clock = Clock(dut.clk, 20, unit="ns")
    cocotb.start_soon(clock.start())
    await reset_dut(dut)

    dut.ui_in.value = 255
    dut.uio_in.value = 0
    await ClockCycles(dut.clk, PWM_PERIOD + 10)

    high = low = 0
    for _ in range(PWM_PERIOD):
        await RisingEdge(dut.clk)
        val = int(dut.uo_out.value)
        high += val & 0x01
        low += (val >> 1) & 0x01

    assert high == scaled_duty(255, 0, 8), f"expected 511 high, got {high}"
    assert low == 0, f"expected low-side disabled at max duty, got {low}"


@cocotb.test()
async def test_deadtime_no_shoot_through(dut):
    """PWM_HIGH and PWM_LOW are never both active."""
    clock = Clock(dut.clk, 20, unit="ns")
    cocotb.start_soon(clock.start())
    await reset_dut(dut)

    dut.ui_in.value = 100
    dut.uio_in.value = 0
    await ClockCycles(dut.clk, PWM_PERIOD + 10)

    for _ in range(PWM_PERIOD * 2):
        await RisingEdge(dut.clk)
        val = int(dut.uo_out.value)
        assert not ((val & 1) and ((val >> 1) & 1)), "shoot-through detected"


@cocotb.test()
async def test_sync_clock(dut):
    """Sync clock toggles once per PWM period."""
    clock = Clock(dut.clk, 20, unit="ns")
    cocotb.start_soon(clock.start())
    await reset_dut(dut)

    dut.ui_in.value = 128
    dut.uio_in.value = 0
    await ClockCycles(dut.clk, PWM_PERIOD + 10)

    edges = 0
    prev = (int(dut.uo_out.value) >> 2) & 1
    for _ in range(PWM_PERIOD * 3):
        await RisingEdge(dut.clk)
        cur = (int(dut.uo_out.value) >> 2) & 1
        if cur and not prev:
            edges += 1
        prev = cur
    assert edges == 3, f"expected 3 sync edges, got {edges}"


async def _avg_high_over_window(dut, ui_val, uio_lsb, periods):
    dut.ui_in.value = ui_val
    dut.uio_in.value = uio_lsb
    await ClockCycles(dut.clk, PWM_PERIOD + 10)
    total = await count_high(dut, periods)
    return total / periods


@cocotb.test()
async def test_dyadic_mode_4bit(dut):
    """Dyadic mode, 4-bit LSB=8: average duty reflects the LSB value."""
    clock = Clock(dut.clk, 20, unit="ns")
    cocotb.start_soon(clock.start())
    await reset_dut(dut)

    # addr0: const=0, mode=1 (dyadic), dyadic_len=4
    await write_cfg(dut, CFG_CTRL, (1 << 3) | 4)

    avg = await _avg_high_over_window(dut, 100, 0x8, 16)
    # 8 of 16 periods add +1 -> (8*scaled(+1) + 8*scaled)/16
    exp = (8 * scaled_duty(100, 8, 8, add=1) + 8 * scaled_duty(100, 8, 8, add=0)) / 16
    assert abs(avg - exp) <= 2, f"dyadic avg {avg:.1f}, expected ~{exp:.1f}"


@cocotb.test()
async def test_dither_modes(dut):
    """Dithering v1/v2/v3 each average to base + (lsb+1)/2^m."""
    clock = Clock(dut.clk, 20, unit="ns")
    cocotb.start_soon(clock.start())

    lsb, m = 7, 4
    # v1->mode2, v2->mode3, v3->mode4 ; LSB=7 -> 8 of 16 periods add +1
    exp = (8 * scaled_duty(100, lsb, 8, add=1) + 8 * scaled_duty(100, lsb, 8, add=0)) / 16
    for mode in (2, 3, 4):
        await reset_dut(dut)
        await write_cfg(dut, CFG_CTRL, (mode << 3) | m)
        avg = await _avg_high_over_window(dut, 100, lsb, 16)
        assert abs(avg - exp) <= 2, f"dither mode {mode} avg {avg:.1f}, expected ~{exp:.1f}"


@cocotb.test()
async def test_constant_dyadic_word(dut):
    """Constant dyadic word drives the sequence independent of control LSBs."""
    clock = Clock(dut.clk, 20, unit="ns")
    cocotb.start_soon(clock.start())
    await reset_dut(dut)

    # addr0: const=1, mode=1, dyadic_len=4 ; addr2: dyadic_word=8
    await write_cfg(dut, CFG_CTRL, (1 << 6) | (1 << 3) | 4)
    await write_cfg(dut, CFG_WORD, 8)

    # uio LSBs = 0, yet the constant word (=8) still yields 8/16 boosted periods
    avg = await _avg_high_over_window(dut, 100, 0x0, 16)
    exp = (8 * scaled_duty(100, 0, 8, add=1) + 8 * scaled_duty(100, 0, 8, add=0)) / 16
    assert abs(avg - exp) <= 2, f"const-word avg {avg:.1f}, expected ~{exp:.1f}"


@cocotb.test()
async def test_uio_all_inputs(dut):
    """All bidirectional pins are configured as inputs."""
    clock = Clock(dut.clk, 20, unit="ns")
    cocotb.start_soon(clock.start())
    await reset_dut(dut)
    await ClockCycles(dut.clk, 5)
    assert int(dut.uio_oe.value) == 0, f"uio_oe should be 0x00, got {dut.uio_oe.value}"
