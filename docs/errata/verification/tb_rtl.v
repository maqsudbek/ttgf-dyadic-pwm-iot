`timescale 1ns/1ps
// Plusarg testbench for the Verilog core (submitted or corrected).
// Config registers are loaded by hierarchical assignment at reset release.
// Writes one line per clock to the file given by +OUT=:
//   <cycle> <PWM_HIGH> <PWM_LOW> <sync> <duty_dbg>
// +RAMP=1 adds 1 to the control word at each sync rising edge.
module tb_rtl;
  integer UIN, BITS, LEN, MODE, CONST, WORD, NPER, RAMP;
  reg clk = 0;
  reg rst_n = 0;
  reg [7:0] ui_in = 0;
  reg [7:0] uio_in = 0;
  wire [7:0] uo_out, uio_out, uio_oe;
  reg [11:0] ctrl;
  integer n, f;
  reg [1023:0] outname;
  reg prev_sync;

  tt_um_maqsudbek_dyadic_pwm dut (
    .ui_in(ui_in), .uo_out(uo_out), .uio_in(uio_in), .uio_out(uio_out),
    .uio_oe(uio_oe), .ena(1'b1), .clk(clk), .rst_n(rst_n));

  always #10 clk = ~clk;

  initial begin
    if (!$value$plusargs("UIN=%d", UIN)) UIN = 2048;
    if (!$value$plusargs("BITS=%d", BITS)) BITS = 8;
    if (!$value$plusargs("LEN=%d", LEN)) LEN = 4;
    if (!$value$plusargs("MODE=%d", MODE)) MODE = 1;
    if (!$value$plusargs("CONST=%d", CONST)) CONST = 0;
    if (!$value$plusargs("WORD=%d", WORD)) WORD = 0;
    if (!$value$plusargs("NPER=%d", NPER)) NPER = 40;
    if (!$value$plusargs("RAMP=%d", RAMP)) RAMP = 0;
    if (!$value$plusargs("OUT=%s", outname)) outname = "rtl_out.txt";
    ctrl = UIN;
    ui_in = ctrl[11:4];
    uio_in = {4'b0, ctrl[3:0]};
    f = $fopen(outname, "w");
    #100;
    rst_n = 1;
    dut.u_dyadic_pwm.dyadic_len = LEN;
    dut.u_dyadic_pwm.dpwm_mode = MODE;
    dut.u_dyadic_pwm.const_dyadic_flag = CONST;
    dut.u_dyadic_pwm.pwm_bits_sel = BITS - 5;
    dut.u_dyadic_pwm.dyadic_word = WORD;
    n = 0; prev_sync = 0;
  end

  always @(posedge clk) begin
    if (rst_n) begin
      $fdisplay(f, "%0d %0d %0d %0d %0d", n, uo_out[0], uo_out[1], uo_out[2], uo_out[7:3]);
      if (uo_out[2] && !prev_sync && RAMP) begin
        ctrl = ctrl + 1;
        ui_in <= ctrl[11:4];
        uio_in <= {4'b0, ctrl[3:0]};
      end
      prev_sync = uo_out[2];
      n = n + 1;
      if (n >= NPER*513) begin
        $fclose(f);
        $finish;
      end
    end
  end
endmodule
