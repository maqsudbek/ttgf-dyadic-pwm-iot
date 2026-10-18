`default_nettype none

/*
 * Dyadic PWM Generator for Tiny Tapeout
 * ======================================
 * 
 * A digital PWM generator with dyadic modulation support.
 * Converts a 12-bit control signal to PWM output with optional dyadic
 * sequence modulation for improved effective resolution.
 *
 * Pin Mapping:
 * ------------
 * INPUTS (directly accessible):
 *   ui_in[7:0]  = Control signal MSB [11:4]
 *   
 * BIDIRECTIONAL (directly accessible, directly accessible as inputs):
 *   uio_in[3:0] = Control signal LSB [3:0]  
 *   uio_in[6:4] = Dyadic length (0=Normal, 2-7=Dyadic LSB bits)
 *   uio_in[7]   = Mode: 0=Normal, 1=Dyadic
 *
 * OUTPUTS:
 *   uo_out[0]  = PWM High-side switch
 *   uo_out[1]  = PWM Low-side switch (complementary with dead-time)
 *   uo_out[2]  = PWM sync clock (~97.5kHz at 50MHz input)
 *   uo_out[7:3]= Duty cycle MSBs [7:3] for debug/monitoring
 *
 * Features:
 * ---------
 * - 8-bit PWM resolution (256 levels)
 * - Dyadic modulation for ~12-bit effective resolution
 * - Complementary outputs with dead-time protection
 * - ~97.5kHz switching frequency at 50MHz clock
 * - 120ns dead-time (6 clock cycles at 50MHz)
 */

module dyadic_pwm (
    input  wire [7:0] ui_in,    // Dedicated inputs - Control MSB [11:4]
    output wire [7:0] uo_out,   // Dedicated outputs
    input  wire [7:0] uio_in,   // IOs: Input path
    output wire [7:0] uio_out,  // IOs: Output path
    output wire [7:0] uio_oe,   // IOs: Enable path (active high: 0=input, 1=output)
    input  wire       ena,      // Always 1 when design is powered
    input  wire       clk,      // Clock
    input  wire       rst_n     // Active-low reset
);

    // =========================================================================
    // Parameters
    // =========================================================================
    
    // PWM period: 513 clock cycles @ 50MHz = ~97.5kHz switching frequency
    // Dead-time: 6 clock cycles = 120ns @ 50MHz
    localparam PWM_PERIOD    = 513;
    localparam DEAD_TIME     = 6;
    localparam MAX_DUTY      = PWM_PERIOD - DEAD_TIME - 2; // ~505

    // =========================================================================
    // Input Signal Mapping
    // =========================================================================
    
    // 12-bit control signal: ui_in[7:0] = MSB, uio_in[3:0] = LSB
    wire [11:0] control_in = {ui_in[7:0], uio_in[3:0]};
    
    // Dyadic length: 0 = Normal mode, 2-7 = LSB bits for dyadic
    wire [2:0] dyadic_len = uio_in[6:4];
    
    // Mode selection: 0 = Normal, 1 = Dyadic
    wire mode_dyadic = uio_in[7];

    // =========================================================================
    // Internal Registers
    // =========================================================================
    
    // PWM timing counter (0 to 512)
    reg [9:0] pwm_counter;
    
    // Dyadic sequence counters for different LSB lengths
    reg [6:0] dyadic_counter_7;
    reg [5:0] dyadic_counter_6;
    reg [4:0] dyadic_counter_5;
    reg [3:0] dyadic_counter_4;
    reg [2:0] dyadic_counter_3;
    reg [1:0] dyadic_counter_2;
    
    // Current duty cycle value (8-bit for PWM comparison)
    reg [8:0] duty_cycle;
    
    // PWM output registers
    reg pwm_high, pwm_low;
    
    // Sync clock register
    reg pwm_sync_clk;
    
    // Switching cycle start pulse
    wire sw_cycle_start = (pwm_counter == PWM_PERIOD - 1);

    // =========================================================================
    // Output Assignments
    // =========================================================================
    
    // All uio pins are inputs
    assign uio_oe  = 8'b0000_0000;
    assign uio_out = 8'b0000_0000;
    
    // PWM outputs
    assign uo_out[0] = pwm_high;
    assign uo_out[1] = pwm_low;
    assign uo_out[2] = pwm_sync_clk;
    assign uo_out[7:3] = duty_cycle[7:3];  // Debug: show duty cycle MSBs
    
    // =========================================================================
    // PWM Counter - Main timing generator
    // =========================================================================
    
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            pwm_counter <= 10'd0;
        end else if (ena) begin
            if (pwm_counter >= PWM_PERIOD - 1) begin
                pwm_counter <= 10'd0;
            end else begin
                pwm_counter <= pwm_counter + 1'b1;
            end
        end
    end

    // =========================================================================
    // Dyadic Sequence Counters - Increment at each switching cycle
    // =========================================================================
    
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            dyadic_counter_7 <= 7'd0;
            dyadic_counter_6 <= 6'd0;
            dyadic_counter_5 <= 5'd0;
            dyadic_counter_4 <= 4'd0;
            dyadic_counter_3 <= 3'd0;
            dyadic_counter_2 <= 2'd0;
        end else if (ena && sw_cycle_start) begin
            dyadic_counter_7 <= dyadic_counter_7 + 1'b1;
            dyadic_counter_6 <= dyadic_counter_6 + 1'b1;
            dyadic_counter_5 <= dyadic_counter_5 + 1'b1;
            dyadic_counter_4 <= dyadic_counter_4 + 1'b1;
            dyadic_counter_3 <= dyadic_counter_3 + 1'b1;
            dyadic_counter_2 <= dyadic_counter_2 + 1'b1;
        end
    end

    // =========================================================================
    // Dyadic Index Calculation
    // Find the position of the most significant '1' in the counter
    // This creates the dyadic sequence pattern
    // =========================================================================
    
    function [2:0] find_msb_index_7;
        input [6:0] counter;
        begin
            if      (counter[6]) find_msb_index_7 = 3'd0;
            else if (counter[5]) find_msb_index_7 = 3'd1;
            else if (counter[4]) find_msb_index_7 = 3'd2;
            else if (counter[3]) find_msb_index_7 = 3'd3;
            else if (counter[2]) find_msb_index_7 = 3'd4;
            else if (counter[1]) find_msb_index_7 = 3'd5;
            else if (counter[0]) find_msb_index_7 = 3'd6;
            else                 find_msb_index_7 = 3'd6;
        end
    endfunction
    
    function [2:0] find_msb_index_6;
        input [5:0] counter;
        begin
            if      (counter[5]) find_msb_index_6 = 3'd0;
            else if (counter[4]) find_msb_index_6 = 3'd1;
            else if (counter[3]) find_msb_index_6 = 3'd2;
            else if (counter[2]) find_msb_index_6 = 3'd3;
            else if (counter[1]) find_msb_index_6 = 3'd4;
            else if (counter[0]) find_msb_index_6 = 3'd5;
            else                 find_msb_index_6 = 3'd5;
        end
    endfunction
    
    function [2:0] find_msb_index_5;
        input [4:0] counter;
        begin
            if      (counter[4]) find_msb_index_5 = 3'd0;
            else if (counter[3]) find_msb_index_5 = 3'd1;
            else if (counter[2]) find_msb_index_5 = 3'd2;
            else if (counter[1]) find_msb_index_5 = 3'd3;
            else if (counter[0]) find_msb_index_5 = 3'd4;
            else                 find_msb_index_5 = 3'd4;
        end
    endfunction
    
    function [2:0] find_msb_index_4;
        input [3:0] counter;
        begin
            if      (counter[3]) find_msb_index_4 = 3'd0;
            else if (counter[2]) find_msb_index_4 = 3'd1;
            else if (counter[1]) find_msb_index_4 = 3'd2;
            else if (counter[0]) find_msb_index_4 = 3'd3;
            else                 find_msb_index_4 = 3'd3;
        end
    endfunction
    
    function [1:0] find_msb_index_3;
        input [2:0] counter;
        begin
            if      (counter[2]) find_msb_index_3 = 2'd0;
            else if (counter[1]) find_msb_index_3 = 2'd1;
            else if (counter[0]) find_msb_index_3 = 2'd2;
            else                 find_msb_index_3 = 2'd2;
        end
    endfunction
    
    function [0:0] find_msb_index_2;
        input [1:0] counter;
        begin
            if      (counter[1]) find_msb_index_2 = 1'd0;
            else if (counter[0]) find_msb_index_2 = 1'd1;
            else                 find_msb_index_2 = 1'd1;
        end
    endfunction

    // =========================================================================
    // Dyadic Bit Extraction
    // Extract the appropriate bit from the LSB portion based on dyadic index
    // =========================================================================
    
    reg dyadic_add_bit;
    reg [6:0] lsb_word;
    reg [2:0] dyadic_index;
    
    always @(*) begin
        dyadic_add_bit = 1'b0;
        lsb_word = 7'd0;
        dyadic_index = 3'd0;
        
        if (mode_dyadic && dyadic_len >= 3'd2) begin
            case (dyadic_len)
                3'd7: begin
                    // 7-bit LSB (only valid with <= 5-bit MSB, but we use 8-bit PWM)
                    // LSB comes from control_in[6:0]
                    lsb_word = control_in[6:0];
                    dyadic_index = find_msb_index_7(dyadic_counter_7);
                    if (dyadic_counter_7 != 7'd0) begin
                        dyadic_add_bit = lsb_word[6 - dyadic_index];
                    end
                end
                3'd6: begin
                    // 6-bit LSB
                    lsb_word = {1'b0, control_in[5:0]};
                    dyadic_index = find_msb_index_6(dyadic_counter_6);
                    if (dyadic_counter_6 != 6'd0) begin
                        dyadic_add_bit = lsb_word[5 - dyadic_index[2:0]];
                    end
                end
                3'd5: begin
                    // 5-bit LSB
                    lsb_word = {2'b0, control_in[4:0]};
                    dyadic_index = find_msb_index_5(dyadic_counter_5);
                    if (dyadic_counter_5 != 5'd0) begin
                        dyadic_add_bit = lsb_word[4 - dyadic_index[2:0]];
                    end
                end
                3'd4: begin
                    // 4-bit LSB  
                    lsb_word = {3'b0, control_in[3:0]};
                    dyadic_index = find_msb_index_4(dyadic_counter_4);
                    if (dyadic_counter_4 != 4'd0) begin
                        dyadic_add_bit = lsb_word[3 - dyadic_index[1:0]];
                    end
                end
                3'd3: begin
                    // 3-bit LSB
                    lsb_word = {4'b0, control_in[2:0]};
                    dyadic_index = {1'b0, find_msb_index_3(dyadic_counter_3)};
                    if (dyadic_counter_3 != 3'd0) begin
                        dyadic_add_bit = lsb_word[2 - dyadic_index[1:0]];
                    end
                end
                3'd2: begin
                    // 2-bit LSB
                    lsb_word = {5'b0, control_in[1:0]};
                    dyadic_index = {2'b0, find_msb_index_2(dyadic_counter_2)};
                    if (dyadic_counter_2 != 2'd0) begin
                        dyadic_add_bit = lsb_word[1 - dyadic_index[0]];
                    end
                end
                default: begin
                    dyadic_add_bit = 1'b0;
                end
            endcase
        end
    end

    // =========================================================================
    // Duty Cycle Calculation
    // 8-bit PWM: Use MSB of control signal + dyadic add bit
    // =========================================================================
    
    wire [7:0] msb_8bit = control_in[11:4];  // Top 8 bits for 8-bit PWM
    wire [8:0] duty_raw = {1'b0, msb_8bit} + {8'b0, dyadic_add_bit};
    
    // Saturate at 255 to prevent overflow
    wire [8:0] duty_saturated = (duty_raw > 9'd255) ? 9'd255 : duty_raw;
    
    // Scale for PWM counter comparison: duty * 2 + 1
    // This maps 0-255 to the 513 cycle period
    wire [9:0] duty_scaled = (duty_saturated[7:0] * 2) + 1;

    // =========================================================================
    // Duty Cycle Register - Latch at start of PWM period
    // =========================================================================
    
    reg [9:0] duty_compare;
    
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            duty_cycle <= 9'd0;
            duty_compare <= 10'd0;
        end else if (ena && pwm_counter == 10'd0) begin
            duty_cycle <= duty_saturated;
            duty_compare <= duty_scaled;
        end
    end

    // =========================================================================
    // PWM Output Generation with Dead-Time
    // =========================================================================
    
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            pwm_high <= 1'b0;
            pwm_low  <= 1'b0;
        end else if (ena) begin
            // High-side switch: ON from cycle 1 to duty_compare
            if (pwm_counter >= 10'd1 && pwm_counter <= duty_compare) begin
                pwm_high <= 1'b1;
            end else begin
                pwm_high <= 1'b0;
            end
            
            // Low-side switch: ON after duty + dead-time, until end - dead-time
            // Only turn on if duty isn't too high (leave room for dead-time)
            if (duty_compare <= MAX_DUTY) begin
                if (pwm_counter > (duty_compare + DEAD_TIME) && 
                    pwm_counter <= (PWM_PERIOD - DEAD_TIME)) begin
                    pwm_low <= 1'b1;
                end else begin
                    pwm_low <= 1'b0;
                end
            end else begin
                pwm_low <= 1'b0;
            end
        end
    end

    // =========================================================================
    // Sync Clock Generation (~97.5kHz square wave)
    // =========================================================================
    
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            pwm_sync_clk <= 1'b0;
        end else if (ena) begin
            if (pwm_counter == 10'd0) begin
                pwm_sync_clk <= 1'b1;
            end else if (pwm_counter == (PWM_PERIOD / 2)) begin
                pwm_sync_clk <= 1'b0;
            end
        end
    end

endmodule
