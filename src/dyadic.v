/*
 * Copyright (c) 2024 Maksudjon Usmonov
 * SPDX-License-Identifier: Apache-2.0
 */

`default_nettype none

/*
 * Dyadic PWM Generator for Tiny Tapeout (GF26a / GF180MCU)
 * =======================================================
 *
 * Digital PWM generator with selectable bit-width, dyadic modulation and
 * three dithering modes. A 12-bit control word drives the duty cycle; static
 * configuration is loaded through a small register file over the pins.
 *
 * Run vs. config is selected by uio_in[7]:
 *
 *   RUN MODE  (uio_in[7] = 0):
 *     ui_in[7:0]   = control_word[11:4]  (MSB)
 *     uio_in[3:0]  = control_word[3:0]   (LSB)
 *
 *   CONFIG WRITE (uio_in[7] = 1), latched on clk while ena:
 *     uio_in[6:4]  = register address
 *     ui_in[7:0]   = write data
 *       addr 0: data[2:0]=dyadic_len(0-7) data[5:3]=dpwm_mode(0-4) data[6]=const_dyadic_flag
 *       addr 1: data[2:0]=pwm_bits_sel    (0->5b,1->6b,2->7b,3->8b,4->9b)
 *       addr 2: data[6:0]=dyadic_word[6:0]
 *
 * Modes (dpwm_mode; forced Normal when dyadic_len = 0):
 *   0 Normal     - base duty only
 *   1 Dyadic     - +bit from src_word[hsb(counter)]; src = control LSBs or constant word
 *   2 Dither v1  - +bit = (lsb_value >= counter)
 *   3 Dither v2  - as v1 but lsb sampled once per 2^m window (at counter==1)
 *   4 Dither v3  - as v2 but base duty (MSB) also sampled at counter==1
 *
 * All widths share a 513-cycle period (~97.466 kHz @ 50 MHz). The chosen
 * B-bit duty is scaled by factor=2^(9-B), offset=max(1,factor/2) to the
 * common period. Complementary outputs carry a 6-cycle (120 ns @ 50 MHz)
 * dead-time. uio pins are all inputs.
 *
 * Outputs:
 *   uo_out[0]   = PWM high-side
 *   uo_out[1]   = PWM low-side (complementary, dead-time)
 *   uo_out[2]   = sync clock (~97.5 kHz)
 *   uo_out[7:3] = duty debug (top bits, normalised to 9-bit domain)
 */

module dyadic_pwm (
    input  wire [7:0] ui_in,    // Dedicated inputs
    output wire [7:0] uo_out,   // Dedicated outputs
    input  wire [7:0] uio_in,   // IOs: Input path
    output wire [7:0] uio_out,  // IOs: Output path
    output wire [7:0] uio_oe,   // IOs: Enable path (1=output)
    input  wire       ena,      // Always 1 when powered
    input  wire       clk,      // Clock
    input  wire       rst_n     // Active-low reset
);

    // =========================================================================
    // Parameters
    // =========================================================================
    localparam PWM_PERIOD     = 513;   // clock cycles per switching period
    localparam DEAD_TIME      = 6;     // dead-time in clock cycles
    localparam LOW_MAX_SCALED = 495;   // low-side enabled only when scaled <= this
    localparam LOW_OFF_CNT    = 507;   // low-side region ends at this count

    // =========================================================================
    // Configuration register file (+ control-word capture)
    // =========================================================================
    wire       cfg_we   = uio_in[7];
    wire [2:0] cfg_addr = uio_in[6:4];
    wire [7:0] cfg_data = ui_in;

    reg  [2:0] dyadic_len;         // m: dyadic/dither word length (0..7)
    reg  [2:0] dpwm_mode;          // 0..4
    reg        const_dyadic_flag;  // 1 = use constant dyadic_word
    reg  [2:0] pwm_bits_sel;       // 0->5b .. 4->9b
    reg  [6:0] dyadic_word;        // constant dyadic word
    reg [11:0] control_word;       // captured 12-bit control word

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            dyadic_len        <= 3'd0;
            dpwm_mode         <= 3'd0;
            const_dyadic_flag <= 1'b0;
            pwm_bits_sel      <= 3'd3;   // default 8-bit
            dyadic_word       <= 7'd0;
            control_word      <= 12'd0;
        end else if (ena) begin
            if (cfg_we) begin
                case (cfg_addr)
                    3'd0: begin
                        dyadic_len        <= cfg_data[2:0];
                        dpwm_mode         <= cfg_data[5:3];
                        const_dyadic_flag <= cfg_data[6];
                    end
                    3'd1: pwm_bits_sel <= cfg_data[2:0];
                    3'd2: dyadic_word  <= cfg_data[6:0];
                    default: ; // no-op
                endcase
            end else begin
                // Run mode: capture the live control word (held during config writes)
                control_word <= {ui_in[7:0], uio_in[3:0]};
            end
        end
    end

    // PWM bit-width as integer 5..9 (clamped)
    reg [3:0] pwm_bits;
    always @(*) begin
        case (pwm_bits_sel)
            3'd0: pwm_bits = 4'd5;
            3'd1: pwm_bits = 4'd6;
            3'd2: pwm_bits = 4'd7;
            3'd3: pwm_bits = 4'd8;
            3'd4: pwm_bits = 4'd9;
            default: pwm_bits = 4'd8;
        endcase
    end

    // =========================================================================
    // Timing counters
    // =========================================================================
    reg  [9:0] pwm_counter;                       // 0..512
    wire       sw_cycle_start = (pwm_counter == PWM_PERIOD - 1);

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            pwm_counter <= 10'd0;
        else if (ena)
            pwm_counter <= sw_cycle_start ? 10'd0 : (pwm_counter + 1'b1);
    end

    // Single shared dyadic counter; per-length counter is its low m bits.
    reg [6:0] dyadic_counter;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            dyadic_counter <= 7'd0;
        else if (ena && sw_cycle_start)
            dyadic_counter <= dyadic_counter + 1'b1;
    end

    wire [6:0] len_mask    = (8'd1 << dyadic_len) - 8'd1;   // low m bits set
    wire [6:0] sel_counter = dyadic_counter & len_mask;     // m-bit counter value

    // Highest set bit position of sel_counter (0 when counter == 0)
    function [2:0] hsb7;
        input [6:0] v;
        begin
            if      (v[6]) hsb7 = 3'd6;
            else if (v[5]) hsb7 = 3'd5;
            else if (v[4]) hsb7 = 3'd4;
            else if (v[3]) hsb7 = 3'd3;
            else if (v[2]) hsb7 = 3'd2;
            else if (v[1]) hsb7 = 3'd1;
            else           hsb7 = 3'd0;
        end
    endfunction

    // =========================================================================
    // Control word decomposition
    // =========================================================================
    // Base duty = top B bits of the control word.
    wire [3:0] shift_amt = 4'd12 - pwm_bits;            // 3..7
    wire [8:0] base_duty = control_word >> shift_amt;   // up to 9 bits

    // LSB word = low m bits of the control word (used for dyadic/dither).
    wire [6:0] lsb_value  = control_word[6:0] & len_mask;
    wire [6:0] word_value = dyadic_word        & len_mask;
    wire [6:0] src_word   = const_dyadic_flag ? word_value : lsb_value;

    // =========================================================================
    // Dither sample-and-hold (modes 3 and 4)
    // =========================================================================
    reg [6:0] lsb_latch;   // LSB held across a 2^m window
    reg [8:0] msb_latch;   // base duty held across a 2^m window

    wire [6:0] eff_lsb = (sel_counter == 7'd1) ? lsb_value : lsb_latch;
    wire [8:0] eff_msb = (sel_counter == 7'd1) ? base_duty : msb_latch;

    // =========================================================================
    // Added-bit / effective-base selection per mode
    // =========================================================================
    reg       add_bit;
    reg [8:0] base_eff;

    always @(*) begin
        add_bit  = 1'b0;
        base_eff = base_duty;
        if (dyadic_len != 3'd0) begin
            case (dpwm_mode)
                3'd1: // Dyadic
                    add_bit = (sel_counter == 7'd0) ? 1'b0 : src_word[hsb7(sel_counter)];
                3'd2: // Dither v1
                    add_bit = (lsb_value >= sel_counter);
                3'd3: // Dither v2
                    add_bit = (eff_lsb >= sel_counter);
                3'd4: begin // Dither v3
                    add_bit  = (eff_lsb >= sel_counter);
                    base_eff = eff_msb;
                end
                default: // Normal
                    add_bit = 1'b0;
            endcase
        end
    end

    // =========================================================================
    // Duty scaling to the common 513-cycle period
    // =========================================================================
    wire [4:0] factor  = 5'd1 << (4'd9 - pwm_bits);             // 1..16
    wire [3:0] offset  = (factor == 5'd1) ? 4'd1 : factor[4:1]; // max(1, factor/2)
    wire [9:0] duty_cap = (10'd1 << pwm_bits) - 10'd1;          // 2^B - 1

    wire [9:0] base_plus = base_eff + add_bit;
    wire [9:0] duty_b    = (base_plus > duty_cap) ? duty_cap : base_plus;
    wire [13:0] scaled_w = (duty_b * factor) + offset;
    wire [9:0] scaled    = scaled_w[9:0];

    // Debug duty normalised to a 9-bit domain (top bits onto uo_out[7:3])
    wire [8:0] duty9 = duty_b << (4'd9 - pwm_bits);

    // =========================================================================
    // Latched compare value + dither/debug registers (at period start)
    // =========================================================================
    reg [9:0] duty_compare;
    reg [4:0] duty_dbg;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            duty_compare <= 10'd0;
            duty_dbg     <= 5'd0;
            lsb_latch    <= 7'd0;
            msb_latch    <= 9'd0;
        end else if (ena && pwm_counter == 10'd0) begin
            duty_compare <= scaled;
            duty_dbg     <= duty9[8:4];
            if (sel_counter == 7'd1) begin
                lsb_latch <= lsb_value;
                msb_latch <= base_duty;
            end
        end
    end

    // =========================================================================
    // PWM output generation with dead-time
    // =========================================================================
    reg pwm_high, pwm_low;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            pwm_high <= 1'b0;
            pwm_low  <= 1'b0;
        end else if (ena) begin
            pwm_high <= (pwm_counter >= 10'd1) && (pwm_counter <= duty_compare);
            if (duty_compare <= LOW_MAX_SCALED)
                pwm_low <= (pwm_counter > (duty_compare + DEAD_TIME)) &&
                           (pwm_counter <= LOW_OFF_CNT);
            else
                pwm_low <= 1'b0;
        end
    end

    // =========================================================================
    // Sync clock (~97.5 kHz square wave)
    // =========================================================================
    reg pwm_sync_clk;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            pwm_sync_clk <= 1'b0;
        else if (ena) begin
            if (pwm_counter == 10'd0)
                pwm_sync_clk <= 1'b1;
            else if (pwm_counter == (PWM_PERIOD / 2))
                pwm_sync_clk <= 1'b0;
        end
    end

    // =========================================================================
    // Output assignments
    // =========================================================================
    assign uio_oe  = 8'b0000_0000;   // all bidirectional pins are inputs
    assign uio_out = 8'b0000_0000;

    assign uo_out[0]   = pwm_high;
    assign uo_out[1]   = pwm_low;
    assign uo_out[2]   = pwm_sync_clk;
    assign uo_out[7:3] = duty_dbg;

endmodule
