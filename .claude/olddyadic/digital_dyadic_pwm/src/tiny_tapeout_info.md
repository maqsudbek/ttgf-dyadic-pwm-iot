Here is a high-level breakdown of the two distinct interfaces you need to know for a Tiny Tapeout project: the internal Verilog top module interface, and the physical PCB (demoboard) hardware you receive at the end.

1. The Top Module (Verilog Interface)
When you write your Verilog code, you are constrained to a very specific interface because all submitted projects on the shuttle share the exact same physical pins on the final ASIC chip.
​

Your top module must include exactly these 34 pins:

Inputs (8 pins): ui_in[7:0] – Dedicated 8-bit input bus.

Outputs (8 pins): uo_out[7:0] – Dedicated 8-bit output bus.

Bidirectional IOs (8 pins): uio_in[7:0] (Input path), uio_out[7:0] (Output path), and uio_oe[7:0] (Output Enable). These allow you to configure 8 additional pins as either inputs or outputs.

Clock (1 pin): clk – The master clock signal for your sequential logic.

Reset (1 pin): rst_n – An active-low reset signal.

Enable (1 pin): ena – Goes high when your specific design is selected on the multiplexed chip.
​

Note: You must map your internal project signals (like UART TX/RX, custom buttons, or sensors) into these specific 8-bit arrays.

2. The Physical PCB (Demoboard Interface)
When the manufactured chip ships to you, it comes mounted on a Carrier/Breakout Board plugged into the Tiny Tapeout Demoboard (also called the Commander board). This board provides the physical hardware to interact with your design's inputs and outputs.
​

The physical demoboard features:

8 DIP Switches: Physically mapped to your 8 dedicated inputs (ui_in). You can toggle these switches by hand to send high/low signals into your design.

7-Segment Display & Dot: Physically hardwired to your 8 dedicated outputs (uo_out). If your design outputs raw binary, you will see the individual LED segments light up.
​

RP2040 Microcontroller: The board has a built-in Raspberry Pi RP2040 (running MicroPython). It acts as the "Commander" and is responsible for selecting which project on the ASIC is active. It also generates the physical clk signal for you (configurable up to 50 MHz) and can provide simulated RAM over SPI.
​

PMOD Connectors: The board has several standard PMOD headers (2x6 pin blocks) broken out along the bottom. This is how you connect external peripherals (like VGA adapters, sensors, or external microcontrollers) to your 8 bidirectional pins (uio) or tap into the main inputs/outputs.
​

USB-C Port: Used to power the board and to connect to your computer, allowing you to interface with the RP2040 via a web-browser terminal to select your project or send automated test patterns.
​

