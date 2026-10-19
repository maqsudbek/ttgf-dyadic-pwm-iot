# Dyadic order: what the papers say, what the chip does, and how to run the chip correctly

**Who this is for.** The author of the design, and anyone who runs the GF26a chip.

**Status.**
- The chip that went to GF26a contains `src/dyadic.v` of commit `750f492`. The `src/` folder of `57c557c` is identical (`git diff 57c557c 750f492 -- src` is empty).
- That file has three errors against the original VHDL and the papers (ECCE 2019; TPEL 2020, eq. 11 and Fig. 2).
- Branch `fix/dyadic-order` has the corrected RTL. It cannot change the fabricated chip.
- This page explains the errors with tables, and shows how to get the correct waveform from the chip that exists.

All tables in this page come from the scripts in [`silicon-workaround/`](silicon-workaround/). The simulations use the RTL of `750f492`. Nobody has measured the real chip yet.

---

## 1. Terms

| Term | Meaning |
|---|---|
| Period | One PWM period: 513 clocks. |
| Frame | 2^M periods in a row. The pattern repeats every frame. |
| N | Number of main bits of the duty (5 to 9). They set the duty in coarse steps. |
| M | Number of dyadic bits. They set how often a period gets one extra step (+1). |
| Dyadic value | The M bits D(M-1) ... D0. D(M-1) is the MSB. The average extra duty is value / 2^M of a step. |
| +1 | A period where the duty is one step higher than the main value. |
| Period number c | 0, 1, 2 ... 2^M - 1. It counts the periods in the frame. |
| Owner of a period | The data bit that decides if this period gets a +1. |

The idea of dyadic PWM: the bit with the larger weight is used in more periods. D3 is used in 8 periods, D2 in 4, D1 in 2, D0 in 1 (for M = 4). The sum is 15 periods. Period 0 has no owner.

---

## 2. The rule of the papers, and the rule of the chip

For M = 4, the frame has 16 periods.

| | Rule | In words |
|---|---|---|
| **Papers** (and the VHDL) | Owner of period c = D(M-1-k), with k = position of the **lowest** set bit of c | The bits of c, from the right: the first "1" counts. |
| **Chip** (`750f492`) | Owner of period c = D(h), with h = position of the **highest** set bit of c | The bits of c, from the left: the first "1" counts. |

### 2.1 Owner of every period (M = 4)

| period | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 | 14 | 15 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| binary | 0000 | 0001 | 0010 | 0011 | 0100 | 0101 | 0110 | 0111 | 1000 | 1001 | 1010 | 1011 | 1100 | 1101 | 1110 | 1111 |
| **papers** | - | D3 | D2 | D3 | D1 | D3 | D2 | D3 | D0 | D3 | D2 | D3 | D1 | D3 | D2 | D3 |
| **chip** | - | D0 | D1 | D1 | D2 | D2 | D2 | D2 | D3 | D3 | D3 | D3 | D3 | D3 | D3 | D3 |

What you see:
- **Papers:** each bit has periods that are spread over the whole frame. D3 takes every second period. D2 takes every fourth period. D1 and D0 take the rest.
- **Chip:** each bit has **one block** of periods. D0 has period 1. D1 has 2 and 3. D2 has 4 to 7. D3 has 8 to 15.
- Both rules give each bit the same **number** of periods (D3: 8, D2: 4, D1: 2, D0: 1). So the **average** duty is correct on the chip. Only the **place** of the +1 periods is wrong.

### 2.2 Examples

The row "thermo" is the thermometric rule of the papers (+1 in the first `value` periods), for comparison. A dot means no +1.

**Value 0101 (D3=0, D2=1, D1=0, D0=1) = 5 of 16**

| period | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 | 14 | 15 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| papers | . | . | +1 | . | . | . | +1 | . | +1 | . | +1 | . | . | . | +1 | . |
| chip | . | +1 | . | . | +1 | +1 | +1 | +1 | . | . | . | . | . | . | . | . |
| thermo | +1 | +1 | +1 | +1 | +1 | . | . | . | . | . | . | . | . | . | . | . |

**Value 1000 = 8 of 16 (half a step)**

| period | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 | 14 | 15 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| papers | . | +1 | . | +1 | . | +1 | . | +1 | . | +1 | . | +1 | . | +1 | . | +1 |
| chip | . | . | . | . | . | . | . | . | +1 | +1 | +1 | +1 | +1 | +1 | +1 | +1 |
| thermo | +1 | +1 | +1 | +1 | +1 | +1 | +1 | +1 | . | . | . | . | . | . | . | . |

The papers alternate every period. The chip gives one long block, the same as thermometric, only moved to the end of the frame.

**Value 0011 = 3 of 16**

| period | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 | 14 | 15 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| papers | . | . | . | . | +1 | . | . | . | +1 | . | . | . | +1 | . | . | . |
| chip | . | +1 | +1 | +1 | . | . | . | . | . | . | . | . | . | . | . | . |
| thermo | +1 | +1 | +1 | . | . | . | . | . | . | . | . | . | . | . | . | . |

Values 0000 and 1111 are the same on the chip and in the papers.

---

## 3. Why the order of the bits in the value does not fix it

It looks like the bits are read "in reverse". They are not.
- On the chip D3 still has the weight of 8 periods. The chip only puts those 8 periods in one block.
- If you reverse the bits of the value, each bit gets the wrong number of periods. The average duty is then wrong.

Can another value give the papers' pattern on the chip? **No.** Look at the chip row of the table in 2.1:
- Periods 8 to 15 have the same owner (D3). They are all +1 or all not +1.
- The papers' pattern for 0101 needs period 8 on and period 9 off.
- The same is true for periods 2 and 3 (both D1) and for 4 to 7 (all D2).

The value is the only word that gives the right average, and it gives the chip's block pattern. A brute-force check agrees (`python3 -I silicon-workaround/dyadic_patterns.py static 4`): only **2 of 16** values (0000 and 1111) can be made as in the papers with a static word. For M = 5 it is 2 of 32.

---

## 4. Is the chip's "dyadic" then the same as thermometric?

Nearly. Both make blocks of +1 periods, so both have a strong tone at the frame rate (clock / 513 / 16 for M = 4). The papers' pattern moves that energy to high frequencies, where a filter removes it. That is the benefit of dyadic PWM, and the chip does not have it.

Strongest tone at the frame rate or at twice the frame rate, for M = 4. Unit: one step of the high-resolution duty (computed from the pattern of 16 periods).

| value | papers | chip | thermometric |
|---|---|---|---|
| 0 | 0.000 | 0.000 | 0.000 |
| 1 | 0.062 | 0.062 | 0.062 |
| 2 | 0.125 | 0.123 | 0.123 |
| 3 | 0.062 | 0.178 | 0.178 |
| 4 | 0.000 | 0.227 | 0.227 |
| 5 | 0.062 | 0.223 | 0.266 |
| 6 | 0.125 | 0.296 | 0.296 |
| 7 | 0.063 | 0.314 | 0.314 |
| 8 | 0.000 | 0.320 | 0.320 |
| 9 | 0.063 | 0.290 | 0.314 |
| 10 | 0.125 | 0.212 | 0.296 |
| 11 | 0.062 | 0.199 | 0.266 |
| 12 | 0.000 | 0.227 | 0.227 |
| 13 | 0.062 | 0.166 | 0.178 |
| 14 | 0.125 | 0.123 | 0.123 |
| 15 | 0.062 | 0.062 | 0.063 |
| mean | 0.062 | 0.189 | 0.203 |

Mean over all 16 values: papers 0.062, chip 0.189, thermometric 0.203. The chip removes about 7 % of the thermometric tone. The papers' pattern removes about 70 %.

---

## 5. Error 2: the chip reads the wrong bits when N + M < 12

The control word has 12 bits. The interface table says: the N main bits are the top bits, and the M dyadic bits are the bits **directly below** them.

Example N = 5, M = 4:

| Word bit | 11 | 10 | 9 | 8 | 7 | 6 | 5 | 4 | 3 | 2 | 1 | 0 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Meaning in the papers and the VHDL | main | main | main | main | main | D3 | D2 | D1 | D0 | free | free | free |
| What the chip reads | main | main | main | main | main | ignored | ignored | ignored | D3 | D2 | D1 | D0 |

The chip takes the **lowest M bits**. So bits 6 to 4 have no effect, and bits 2 to 0 are used as data.

**Workaround (a static word, no controller).** Write the dyadic bits in the lowest M bits: bits 11 to 7 = main value, bits 6 to 4 = anything, bits 3 to 0 = dyadic value. With N + M = 12 there is no problem, because the lowest M bits are then the right bits.

---

## 6. Error 3: thermometric mode gives one period too many

The papers' rule: +1 in the first `value` periods. The chip's rule: +1 when `value >= period number`. That is `value + 1` periods. For value 0 it still gives one period.

Example M = 4, value 5:

| period | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 | 14 | 15 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| papers (5 periods) | +1 | +1 | +1 | +1 | +1 | . | . | . | . | . | . | . | . | . | . | . |
| chip, word = 5 | +1 | +1 | +1 | +1 | +1 | +1 | . | . | . | . | . | . | . | . | . | . |
| chip, word = **4** | +1 | +1 | +1 | +1 | +1 | . | . | . | . | . | . | . | . | . | . | . |

**Workaround (a static word, no controller).** Send **D - 1** as the 12-bit word, with N + M = 12. The chip then gives exactly the papers' pattern.
- For a dyadic value 0 the word D - 1 borrows from the main part. The main value is then one less, and all periods get +1. The result is the same.
- Only the word 0 (main value 0 and dyadic value 0) cannot be sent as -1. The chip then adds one extra +1 in period 0. Use Normal mode (mode 0) for that case.

---

## 7. The dyadic mode needs an outside controller

The errors in sections 5 and 6 can be fixed with the value in a static word. The wrong period order (section 2) cannot. The way out is to use the chip in **Normal mode** (mode 0), which has no fault, and to write the 12-bit word again **in every period**. The word of each period is the main value plus the +1 bit of the papers.

### 7.1 What the controller does

1. Reset the chip. Leave it in Normal mode (the default). Set the width with config register 1 (5 bits = 0, ..., 9 bits = 4). Keep `uio_in[7]` = 0 afterwards.
2. Wait for the rising edge of the sync output `uo_out[2]`. It marks the start of a period.
3. Count the periods. For the next period number c = p + 1 (modulo 2^M) compute the +1 bit by the rule of the papers:
   - c = 0: bit = 0;
   - otherwise k = the lowest set bit of c, and bit = D(M-1-k).
4. Write the 12-bit word `(main + bit) << (12 - N)` to `ui_in[7:0]` (word bits 11 to 4) and `uio_in[3:0]` (word bits 3 to 0). It must be stable before the period ends. It takes effect in the **next** period (one period of delay).

With a main value of the maximum (all ones), `main + bit` saturates, so the +1 is lost. Keep the main value below the maximum.

### 7.2 Sketch for the demo-board RP2040 (not run on hardware: INFERRED)

It uses the calls from [usage.md](usage.md). Use a slow clock so MicroPython is fast enough. At 100 kHz one period is 5.13 ms.

```python
N, M = 5, 4                  # 5 main bits, 4 dyadic bits
main, value = 11, 0b0101     # duty = main + value/16 steps

def plus1(c):                # the rule of the papers
    if c == 0:
        return 0
    k = (c & -c).bit_length() - 1
    return (value >> (M - 1 - k)) & 1

def write_word(w):           # 12-bit word; uio_in[7] stays 0 (run mode)
    tt.ui_in.value = w >> 4
    tt.uio_in.value = w & 0x0F

# (after reset and the width setting: 5 bits -> config register 1 = 0)
p, last = 0, 0
while True:
    sync = (tt.uo_out.value >> 2) & 1
    if sync and not last:                       # a new period starts
        p = (p + 1) % (1 << M)                  # number of the NEXT period
        write_word((main + plus1(p)) << (12 - N))
    last = sync
```

An FPGA (for example the DE1-SoC) can do the same at the full 50 MHz clock.

### 7.3 What this means
The chip then makes the PWM, the dead time and the timing. The controller makes the dithering. The waveform is the same as that of a correct DDPWM. Here N and M are not limited by N + M = 12, because the chip only sees the main bits.

---

## 8. Operating the chip: clock

The chip of `750f492` did not meet the 50 MHz timing at the slow corner (125 C, 3.0 V) in the CI of that time (see the README). Use a clock of 30 MHz or less if you need a guaranteed result. The switching frequency is clock / 513.

---

## 9. Checks

Run from the repository root. It needs `iverilog`, `vvp` and `git`.

```
python3 -I docs/silicon-workaround/check_workarounds.py
```

It reads `src/dyadic.v` of `750f492` from git, simulates it, and checks (all 23 pass):

| Check | Result |
|---|---|
| The chip's dyadic mode follows the "highest set bit" rule (4 cases) and differs from the papers | pass |
| N = 5, M = 4: dyadic bits in word bits 6 to 4 are not read; bits 3 to 0 are read | pass |
| Thermometric with D - 1 gives the papers' pattern (B = 5 to 9, all values, including the borrow case) | pass |
| Outside controller in Normal mode gives the papers' pattern (8 cases, B = 5 to 9, M = 3 to 7) | pass |

Other scripts:
- `python3 -I docs/silicon-workaround/dyadic_patterns.py owners 4` : the owner table of section 2.1.
- `python3 -I docs/silicon-workaround/dyadic_patterns.py example 4 0b0101` : the example tables of section 2.2.
- `python3 -I docs/silicon-workaround/dyadic_patterns.py tones 4` : the tone table of section 4.
- `python3 -I docs/silicon-workaround/dyadic_patterns.py static 4` : how many values a static word can fix.

**Not checked:** the real chip, dither v2 and v3, and the MicroPython sketch.
