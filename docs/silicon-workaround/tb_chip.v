// Test bench for the chip as it was taped out (src/dyadic.v of commit 750f492).
// It records the high time of uo_out[0] in each 513-clock period of one frame.
//   +CASE=0  static word:  +MODE (0..4) +LEN (m) +B (5..9) +WORD (12 bit)
//   +CASE=1  outside controller in Normal mode (mode 0): +B +N (base) +F (dyadic value) +LEN (M)
//            The controller counts the sync pulses (uo_out[2]) and writes the word of the next
//            period: (N + plus1 bit of the papers) << (12 - B).
`timescale 1ns/1ps
module tb;
  reg clk = 0, rst_n = 0; always #10 clk = ~clk;
  reg [7:0] ui_in = 0, uio_in = 0;
  wire [7:0] uo_out, uio_out, uio_oe;
  dyadic_pwm dut(.ui_in(ui_in), .uo_out(uo_out), .uio_in(uio_in), .uio_out(uio_out),
                 .uio_oe(uio_oe), .ena(1'b1), .clk(clk), .rst_n(rst_n));
  integer case_, mode, len, B, n, f, word, p, c, high, k;
  reg sync_d;

  task cfg(input [2:0] a, input [7:0] d);
    begin @(negedge clk); uio_in = 8'h80 | (a << 4); ui_in = d; @(negedge clk); uio_in = 0; end
  endtask
  task setword(input integer w);
    begin ui_in = w >> 4; uio_in = w & 15; end
  endtask
  // The papers' rule: lowest set bit kk of the period number pp selects data bit M-1-kk.
  function integer pbit(input integer pp, input integer MM, input integer ff);
    integer kk;
    begin
      if (pp == 0) pbit = 0;
      else begin kk = 0; while (((pp >> kk) & 1) == 0) kk = kk + 1; pbit = (ff >> (MM-1-kk)) & 1; end
    end
  endfunction

  initial begin
    if (!$value$plusargs("CASE=%d", case_)) case_ = 0;
    if (!$value$plusargs("MODE=%d", mode)) mode = 1;
    if (!$value$plusargs("LEN=%d", len)) len = 4;
    if (!$value$plusargs("B=%d", B)) B = 8;
    if (!$value$plusargs("WORD=%d", word)) word = 0;
    if (!$value$plusargs("N=%d", n)) n = 100;
    if (!$value$plusargs("F=%d", f)) f = 5;
    repeat (5) @(negedge clk); rst_n = 1;
    if (case_ == 0) begin
      cfg(0, (mode << 3) | len); cfg(1, B - 5);
      @(negedge clk); setword(word);
    end else begin
      cfg(0, 0); cfg(1, B - 5);
      @(negedge clk); setword(n << (12 - B));
    end
    wait (dut.pwm_counter == 0 && dut.sel_counter == 0); repeat (2*513) @(posedge clk);
    $write("TT");
    if (case_ == 0) begin
      wait (dut.pwm_counter == 1 && dut.sel_counter == 0);
      for (p = 0; p < (1 << len); p = p + 1) begin
        high = 0; for (c = 0; c < 513; c = c + 1) begin @(posedge clk); #1 high = high + uo_out[0]; end
        $write(" %0d", high);
      end
    end else begin
      sync_d = uo_out[2]; k = -1; high = 0;
      repeat (513 * ((1 << len) + 3)) begin
        @(posedge clk); #1;
        if (uo_out[2] && !sync_d) begin
          if (k >= 0) $write(" %0d", high);
          k = k + 1; high = 0;
          @(negedge clk); setword((n + pbit((k + 1) % (1 << len), len, f)) << (12 - B));
        end
        sync_d = uo_out[2];
        high = high + uo_out[0];
      end
    end
    $write("\n");
    $finish;
  end
endmodule
