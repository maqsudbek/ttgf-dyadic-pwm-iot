# Dyadic PWM Generator for Tiny Tapeout

## Overview

This module implements a **Digital PWM (DPWM) generator** with **dyadic modulation** support, designed specifically for the Tiny Tapeout ASIC platform. It converts a 12-bit control signal into a PWM output, with the option to use dyadic sequences to achieve higher effective resolution than the base PWM bit-width allows.

## What is Dyadic Modulation?

Dyadic modulation is a technique to increase the effective resolution of a PWM signal beyond its native bit-width. Instead of simply truncating the lower bits of a control signal, dyadic modulation uses those bits to create a **sequence of +1 adjustments** to the base duty cycle over multiple switching periods.

### The Dyadic Sequence

The key insight is that the sequence of adjustments follows a **dyadic (binary) pattern** based on which bit position has the most significant '1' in a counter:

| Counter (3-bit) | Binary | MSB '1' Position | Index |
|-----------------|--------|------------------|-------|
| 0               | 000    | None             | -     |
| 1               | 001    | bit 0            | 2     |
| 2               | 010    | bit 1            | 1     |
| 3               | 011    | bit 0            | 2     |
| 4               | 100    | bit 2            | 0     |
| 5               | 101    | bit 0            | 2     |
| 6               | 110    | bit 1            | 1     |
| 7               | 111    | bit 0            | 2     |

The index then selects which bit of the LSB word to use as the "+1" addition to the MSB duty cycle.

### Example: 3-bit LSB Dyadic

If LSB word = `101` (binary) and we have a 3-bit counter:

| Cycle | Counter | Index | LSB bit at index | Add to duty |
|-------|---------|-------|------------------|-------------|
| 0     | 000     | -     | -                | +0          |
| 1     | 001     | 2     | LSB[0] = 1       | +1          |
| 2     | 010     | 1     | LSB[1] = 0       | +0          |
| 3     | 011     | 2     | LSB[0] = 1       | +1          |
| 4     | 100     | 0     | LSB[2] = 1       | +1          |
| 5     | 101     | 2     | LSB[0] = 1       | +1          |
| 6     | 110     | 1     | LSB[1] = 0       | +0          |
| 7     | 111     | 2     | LSB[0] = 1       | +1          |

Over 8 cycles: 5 additions of +1, average = 5/8 = 0.625 LSB
This matches the LSB value: 101 binary = 5

---

## Tiny Tapeout Interface

### Pin Mapping

```
                    ┌─────────────────────┐
                    │  tt_um_dyadic_pwm   │
                    │                     │
    ui_in[7:0] ────►│ Control MSB [11:4]  │
                    │                     │
   uio_in[3:0] ────►│ Control LSB [3:0]   │
   uio_in[6:4] ────►│ Dyadic Length       │────► uo_out[0]  PWM_HIGH
   uio_in[7]   ────►│ Mode Select         │────► uo_out[1]  PWM_LOW
                    │                     │────► uo_out[2]  SYNC_CLK
        clk    ────►│                     │────► uo_out[7:3] DUTY[7:3]
        rst_n  ────►│                     │
        ena    ────►│                     │
                    └─────────────────────┘
```

### Input Pins

| Pin | Name | Description |
|-----|------|-------------|
| `ui_in[7:0]` | Control MSB | Upper 8 bits of 12-bit control signal [11:4] |
| `uio_in[3:0]` | Control LSB | Lower 4 bits of 12-bit control signal [3:0] |
| `uio_in[6:4]` | Dyadic Length | Number of LSB bits for dyadic (0, 2-7) |
| `uio_in[7]` | Mode | 0 = Normal, 1 = Dyadic |
| `clk` | Clock | System clock (designed for 50MHz) |
| `rst_n` | Reset | Active-low synchronous reset |
| `ena` | Enable | Design enable (active high) |

### Output Pins

| Pin | Name | Description |
|-----|------|-------------|
| `uo_out[0]` | PWM_HIGH | High-side switch output |
| `uo_out[1]` | PWM_LOW | Low-side switch output (complementary) |
| `uo_out[2]` | SYNC_CLK | Switching sync clock (~97.5kHz) |
| `uo_out[7:3]` | DUTY[7:3] | Duty cycle MSBs for debug |

### Bidirectional Pin Configuration

All bidirectional pins (`uio`) are configured as **inputs** (`uio_oe = 8'b0000_0000`).

---

## Operating Modes

### Normal Mode (`uio_in[7] = 0`)

In normal mode, only the upper 8 bits of the control signal are used for PWM generation:

```
Duty Cycle = control_in[11:4]  (0-255)
```

This provides standard 8-bit PWM resolution.

### Dyadic Mode (`uio_in[7] = 1`)

In dyadic mode, the lower bits modulate the duty cycle over multiple switching periods:

```
Effective Duty = MSB + dyadic_sequence_bit
```

Where `dyadic_sequence_bit` is 0 or 1 based on:
- The current counter value
- The LSB word bits

#### Dyadic Length Settings

| `uio_in[6:4]` | LSB Bits Used | Effective Resolution | Counter Period |
|---------------|---------------|---------------------|----------------|
| 0 or 1        | 0 (Normal)    | 8-bit               | N/A            |
| 2             | 2             | ~10-bit             | 4 cycles       |
| 3             | 3             | ~11-bit             | 8 cycles       |
| 4             | 4             | ~12-bit             | 16 cycles      |
| 5             | 5             | ~13-bit             | 32 cycles      |
| 6             | 6             | ~14-bit             | 64 cycles      |
| 7             | 7             | ~15-bit             | 128 cycles     |

---

## Timing Parameters

| Parameter | Value | Notes |
|-----------|-------|-------|
| PWM Period | 513 clock cycles | ~97.5kHz at 50MHz |
| Dead-Time | 6 clock cycles | 120ns at 50MHz |
| Max Duty | 505 cycles | ~98.4% |
| Min Duty | 1 cycle | ~0.2% |

### PWM Waveform Timing

```
         ┌─────────────────────┐
PWM_HIGH │                     │
─────────┘                     └───────────────────────────
                               ◄──────►
                               Dead-time
                                       ┌─────────────────┐
PWM_LOW                                │                 │
───────────────────────────────────────┘                 └─
         ◄─────────────────────►◄──────►◄─────────────────►
              Duty Period       D.T.      Off Period
         
         ◄─────────────────────────────────────────────────►
                        PWM Period (513 cycles)
```

---

## Implementation Details

### Block Diagram

```
┌──────────────────────────────────────────────────────────────────┐
│                                                                  │
│  ┌─────────────┐                                                 │
│  │  PWM        │                                                 │
│  │  Counter    │──────────────────────────────────────┐          │
│  │  (0-512)    │                                      │          │
│  └──────┬──────┘                                      │          │
│         │                                             ▼          │
│         │ sw_cycle_start              ┌───────────────────────┐  │
│         │                             │  PWM Output Generator │  │
│         ▼                             │  with Dead-Time       │──┼──► PWM_HIGH
│  ┌─────────────┐                      │                       │──┼──► PWM_LOW
│  │  Dyadic     │                      └───────────┬───────────┘  │
│  │  Counters   │                                  │              │
│  │  (2-7 bit)  │                                  │              │
│  └──────┬──────┘                                  │              │
│         │                              duty_compare              │
│         ▼                                         ▲              │
│  ┌─────────────┐     ┌─────────────┐    ┌────────┴────────┐     │
│  │  MSB Index  │────►│  Dyadic Bit │───►│  Duty Cycle     │     │
│  │  Finder     │     │  Extractor  │    │  Calculator     │     │
│  └─────────────┘     └──────┬──────┘    └────────┬────────┘     │
│                             ▲                    ▲               │
│                             │                    │               │
│                        LSB Word            MSB (8-bit)           │
│                             │                    │               │
│  ┌──────────────────────────┴────────────────────┘               │
│  │                    control_in[11:0]                           │
│  └───────────────────────────────────────────────────────────────┤
│                             ▲                                    │
└─────────────────────────────┼────────────────────────────────────┘
                              │
               {ui_in[7:0], uio_in[3:0]}
```

### Key Components

1. **PWM Counter**: 10-bit counter cycling 0→512, creating 513-cycle periods

2. **Dyadic Counters**: Six separate counters (2-7 bits) incrementing each switching cycle

3. **MSB Index Finder**: Priority encoder finding the position of the most significant '1' in the appropriate counter

4. **Dyadic Bit Extractor**: Selects the bit from the LSB word at the dyadic index position

5. **Duty Cycle Calculator**: Adds the dyadic bit (0 or 1) to the 8-bit MSB value with saturation

6. **PWM Output Generator**: Creates complementary outputs with programmable dead-time

---

## Usage Examples

### Example 1: Normal Mode (50% Duty)

```
ui_in[7:0]    = 8'b1000_0000  (128)
uio_in[3:0]   = 4'b0000       (ignored in normal mode)
uio_in[6:4]   = 3'b000        (normal mode)
uio_in[7]     = 1'b0          (normal mode)

Result: 50% duty cycle (128/256)
```

### Example 2: Dyadic Mode with 4-bit LSB

```
ui_in[7:0]    = 8'b0111_1111  (127 = ~49.6%)
uio_in[3:0]   = 4'b1000       (LSB = 8)
uio_in[6:4]   = 3'b100        (4-bit dyadic)
uio_in[7]     = 1'b1          (dyadic mode)

Result: Over 16 cycles, duty alternates between 127 and 128
        Average = 127 + 8/16 = 127.5 → effective 12-bit resolution
```

### Example 3: Maximum Duty

```
ui_in[7:0]    = 8'b1111_1111  (255)
uio_in[7]     = 1'b1          (dyadic mode)

Result: Saturated at 255 (no overflow), ~99.6% duty
        Low-side switch disabled at high duty to maintain dead-time
```

---

## Design Constraints

### Adapted for Tiny Tapeout

The original VHDL design supported multiple features that were simplified for Tiny Tapeout's limited I/O:

| Feature | Original | Tiny Tapeout Version |
|---------|----------|---------------------|
| PWM Resolution | 5/6/7/8/9-bit selectable | Fixed 8-bit |
| Modes | Normal + Dyadic + 3 Dithering modes | Normal + Dyadic only |
| Dyadic Word | From control signal or constant input | Control signal only |
| Clock outputs | 5 phase-shifted outputs | 1 sync clock |
| Control signal | 12-bit direct | 8-bit + 4-bit split |

### Clock Requirements

- Designed for 50MHz clock
- At other frequencies, switching frequency scales proportionally:
  - 25MHz → ~48.7kHz
  - 100MHz → ~195kHz

---

## Applications

- **DC-DC Buck Converter Control**: Primary application for power electronics
- **Motor Control**: Complementary outputs with dead-time suitable for half-bridge
- **LED Dimming**: High-resolution dimming with dyadic modulation
- **Audio Class-D Amplifiers**: PWM audio output

---

## Files

| File | Description |
|------|-------------|
| `dyadic.v` | Main Verilog source file |
| `dyadic_doc.md` | This documentation |

---

## References

- Original VHDL implementation: `dpwm.vhd`, `pwm_97466hz.vhd`
- Tiny Tapeout Interface Specification: `tiny_tapeout_info.md`
