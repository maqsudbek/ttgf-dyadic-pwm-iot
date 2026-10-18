# SPDX-FileCopyrightText: © 2024 Tiny Tapeout
# SPDX-License-Identifier: Apache-2.0

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, RisingEdge

PWM_PERIOD = 513


async def reset_dut(dut):
    """Apply reset and wait for it to take effect."""
    dut.ena.value = 1
    dut.ui_in.value = 0
    dut.uio_in.value = 0
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 10)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 2)


@cocotb.test()
async def test_reset(dut):
    """Test that outputs are low during reset."""
    dut._log.info("Test: reset state")
    clock = Clock(dut.clk, 20, unit="ns")  # 50MHz
    cocotb.start_soon(clock.start())

    dut.ena.value = 1
    dut.ui_in.value = 0
    dut.uio_in.value = 0
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 10)

    # During reset, PWM outputs should be low
    val = int(dut.uo_out.value)
    assert not (val & 0x01), "PWM_HIGH should be 0 during reset"
    assert not (val & 0x02), "PWM_LOW should be 0 during reset"

    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 2)


@cocotb.test()
async def test_normal_mode_50pct(dut):
    """Test normal mode with ~50% duty cycle (MSB=128)."""
    dut._log.info("Test: normal mode 50% duty")
    clock = Clock(dut.clk, 20, unit="ns")
    cocotb.start_soon(clock.start())

    await reset_dut(dut)

    # Normal mode: ui_in=128 (50% duty), uio_in=0 (normal mode, no dyadic)
    dut.ui_in.value = 128
    dut.uio_in.value = 0

    # Wait for one full PWM period + margin to latch duty
    await ClockCycles(dut.clk, PWM_PERIOD + 10)

    # Count high cycles over one PWM period
    high_count = 0
    for _ in range(PWM_PERIOD):
        await RisingEdge(dut.clk)
        if int(dut.uo_out.value) & 0x01:
            high_count += 1

    dut._log.info(f"50% duty: PWM_HIGH was high for {high_count}/{PWM_PERIOD} cycles")

    # duty=128, scaled = 128*2+1 = 257. High from cycle 1 to 257 = 257 cycles.
    expected = 257
    assert high_count == expected, f"Expected {expected} high cycles, got {high_count}"


@cocotb.test()
async def test_normal_mode_zero_duty(dut):
    """Test normal mode with minimum duty (MSB=0)."""
    dut._log.info("Test: normal mode min duty")
    clock = Clock(dut.clk, 20, unit="ns")
    cocotb.start_soon(clock.start())

    await reset_dut(dut)

    # Normal mode: ui_in=0, uio_in=0
    dut.ui_in.value = 0
    dut.uio_in.value = 0

    await ClockCycles(dut.clk, PWM_PERIOD + 10)

    high_count = 0
    for _ in range(PWM_PERIOD):
        await RisingEdge(dut.clk)
        if int(dut.uo_out.value) & 0x01:
            high_count += 1

    dut._log.info(f"Min duty: PWM_HIGH was high for {high_count}/{PWM_PERIOD} cycles")

    # duty=0, scaled = 0*2+1 = 1. High at cycle 1 only = 1 cycle.
    assert high_count == 1, f"Expected 1 high cycle at min duty, got {high_count}"


@cocotb.test()
async def test_normal_mode_max_duty(dut):
    """Test normal mode with maximum duty (MSB=255)."""
    dut._log.info("Test: normal mode max duty")
    clock = Clock(dut.clk, 20, unit="ns")
    cocotb.start_soon(clock.start())

    await reset_dut(dut)

    # Normal mode: ui_in=255, uio_in=0
    dut.ui_in.value = 255
    dut.uio_in.value = 0

    await ClockCycles(dut.clk, PWM_PERIOD + 10)

    high_count = 0
    low_count = 0
    for _ in range(PWM_PERIOD):
        await RisingEdge(dut.clk)
        val = int(dut.uo_out.value)
        if val & 0x01:
            high_count += 1
        if val & 0x02:
            low_count += 1

    dut._log.info(f"Max duty: HIGH={high_count}, LOW={low_count} / {PWM_PERIOD} cycles")

    # duty=255, scaled = 255*2+1 = 511. High from cycle 1 to 511 = 511 cycles.
    assert high_count == 511, f"Expected 511 high cycles at max duty, got {high_count}"
    # Low-side should be disabled at max duty (duty_compare=511 > MAX_DUTY=505)
    assert low_count == 0, f"Expected 0 low cycles at max duty, got {low_count}"


@cocotb.test()
async def test_complementary_deadtime(dut):
    """Test that PWM_HIGH and PWM_LOW are never both on (dead-time)."""
    dut._log.info("Test: dead-time / no shoot-through")
    clock = Clock(dut.clk, 20, unit="ns")
    cocotb.start_soon(clock.start())

    await reset_dut(dut)

    # Mid-range duty so both HIGH and LOW are active
    dut.ui_in.value = 100
    dut.uio_in.value = 0

    await ClockCycles(dut.clk, PWM_PERIOD + 10)

    # Check over 2 full PWM periods
    for _ in range(PWM_PERIOD * 2):
        await RisingEdge(dut.clk)
        val = int(dut.uo_out.value)
        pwm_h = val & 1
        pwm_l = (val >> 1) & 1
        assert not (pwm_h and pwm_l), "Shoot-through! PWM_HIGH and PWM_LOW both active"


@cocotb.test()
async def test_sync_clock(dut):
    """Test that sync clock toggles at PWM frequency."""
    dut._log.info("Test: sync clock")
    clock = Clock(dut.clk, 20, unit="ns")
    cocotb.start_soon(clock.start())

    await reset_dut(dut)

    dut.ui_in.value = 128
    dut.uio_in.value = 0

    await ClockCycles(dut.clk, PWM_PERIOD + 10)

    # Count sync clock rising edges over 3 PWM periods
    edges = 0
    prev_sync = (int(dut.uo_out.value) >> 2) & 1
    for _ in range(PWM_PERIOD * 3):
        await RisingEdge(dut.clk)
        sync = (int(dut.uo_out.value) >> 2) & 1
        if sync and not prev_sync:
            edges += 1
        prev_sync = sync

    dut._log.info(f"Sync clock rising edges in {PWM_PERIOD*3} clocks: {edges}")
    assert edges == 3, f"Expected 3 sync clock edges in 3 PWM periods, got {edges}"


@cocotb.test()
async def test_dyadic_mode_4bit(dut):
    """Test dyadic mode with 4-bit LSB: average duty should reflect LSB value."""
    dut._log.info("Test: dyadic mode 4-bit LSB")
    clock = Clock(dut.clk, 20, unit="ns")
    cocotb.start_soon(clock.start())

    await reset_dut(dut)

    # Dyadic mode: MSB=100, LSB=8 (0b1000), dyadic_len=4, mode=dyadic
    # uio_in = {mode=1, dyadic_len=100, lsb=1000} = 1_100_1000 = 0xC8
    dut.ui_in.value = 100
    dut.uio_in.value = 0xC8

    await ClockCycles(dut.clk, PWM_PERIOD + 10)

    # Run for 16 PWM periods (full 4-bit dyadic cycle)
    total_high = 0
    for _ in range(16 * PWM_PERIOD):
        await RisingEdge(dut.clk)
        if int(dut.uo_out.value) & 0x01:
            total_high += 1

    avg_high_per_period = total_high / 16

    # Base duty = 100, scaled = 201. With dyadic LSB=8, expect 8/16 periods at 201+2=203
    # and 8/16 at 201. Average = 201 + 8*2/16 = 202. Allow small tolerance.
    base_scaled = 100 * 2 + 1  # 201
    boosted_scaled = 101 * 2 + 1  # 203
    # 8 of 16 periods should add +1 to duty (LSB value = 8 out of 16)
    expected_avg = (8 * boosted_scaled + 8 * base_scaled) / 16  # 202
    tolerance = 2

    dut._log.info(f"Dyadic 4-bit: avg HIGH/period = {avg_high_per_period:.1f}, expected ~{expected_avg:.1f}")
    assert abs(avg_high_per_period - expected_avg) <= tolerance, \
        f"Average high cycles {avg_high_per_period:.1f} not close to expected {expected_avg:.1f}"


@cocotb.test()
async def test_uio_all_inputs(dut):
    """Test that all bidirectional pins are configured as inputs."""
    dut._log.info("Test: uio_oe all inputs")
    clock = Clock(dut.clk, 20, unit="ns")
    cocotb.start_soon(clock.start())

    await reset_dut(dut)
    await ClockCycles(dut.clk, 5)

    assert int(dut.uio_oe.value) == 0, f"uio_oe should be 0x00 (all inputs), got {dut.uio_oe.value}"
