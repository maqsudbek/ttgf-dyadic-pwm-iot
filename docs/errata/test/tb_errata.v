`default_nettype none
`timescale 1ns / 1ps

/* Testbench for the errata tests.
 *
 * The clock comes from Verilog (cocotb Clock is 10x slower). A black-box
 * monitor counts the PWM_HIGH cycles of each switching period. The monitor
 * looks only at uo_out. cocotb reads last_high, last_index and started.
 *
 * Period index j = number of sync rising edges since reset, minus 1.
 * Period 0 starts at the first clock edge after reset release.
 */
module tb ();

  reg        clk = 1'b0;
  reg        rst_n = 1'b0;
  reg        ena = 1'b1;
  reg  [7:0] ui_in = 8'd0;
  reg  [7:0] uio_in = 8'd0;
  wire [7:0] uo_out;
  wire [7:0] uio_out;
  wire [7:0] uio_oe;

  always #10 clk = ~clk;   // 50 MHz; rising edges at 10 ns, 30 ns, ...

  tt_um_maqsudbek_dyadic_pwm user_project (
      .ui_in  (ui_in),
      .uo_out (uo_out),
      .uio_in (uio_in),
      .uio_out(uio_out),
      .uio_oe (uio_oe),
      .ena    (ena),
      .clk    (clk),
      .rst_n  (rst_n)
  );

  wire sync_w = uo_out[2];

  reg        prev_sync;
  integer    high_acc;
  integer    started;      // number of sync rising edges since reset
  integer    last_high;    // PWM_HIGH cycles of the last completed period
  integer    last_index;   // index of that period

  always @(posedge clk) begin
    if (!rst_n) begin
      prev_sync  <= 1'b0;
      high_acc   <= 0;
      started    <= 0;
      last_high  <= 0;
      last_index <= -1;
    end else begin
      prev_sync <= sync_w;
      if (sync_w && !prev_sync) begin
        if (started >= 1) begin
          last_high  <= high_acc;
          last_index <= started - 1;
        end
        started  <= started + 1;
        high_acc <= uo_out[0];
      end else begin
        high_acc <= high_acc + uo_out[0];
      end
    end
  end

endmodule
