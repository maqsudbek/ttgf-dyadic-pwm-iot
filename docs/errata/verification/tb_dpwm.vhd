-- Testbench for dpwm.vhd. Prints one line per clock after reset release:
--   <cycle> <HIGH_SW> <LOW_SW> <pwm_clk> <pre_pwm_clk> <DUTY_VAL_OUT>
-- Generics select the case. G_RAMP = 1 adds 1 to U_IN at each pwm_clk rising edge.

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use std.textio.all;

entity tb_dpwm is
  generic (
    G_UIN    : integer := 2048;
    G_BITS   : integer := 8;
    G_LEN    : integer := 4;
    G_MODE   : integer := 1;
    G_CONST  : integer := 0;
    G_WORD   : integer := 0;
    G_NPER   : integer := 40;
    G_RAMP   : integer := 0
  );
end tb_dpwm;

architecture sim of tb_dpwm is
  signal clk, rst : std_logic := '0';
  signal uin : std_logic_vector(11 downto 0) := std_logic_vector(to_unsigned(G_UIN, 12));
  signal hs, ls, pclk, p1, p2, p3, p4, p2x : std_logic;
  signal duty : std_logic_vector(11 downto 0);
  signal done : boolean := false;
  signal cflag : std_logic;
begin
  cflag <= '1' when G_CONST = 1 else '0';

  dut: entity work.dpwm
    port map (
      CLK_50 => clk, RST => rst, U_IN => uin,
      PWM_BITS => std_logic_vector(to_unsigned(G_BITS, 4)),
      DYADIC_LEN => std_logic_vector(to_unsigned(G_LEN, 3)),
      dpwm_mode => std_logic_vector(to_unsigned(G_MODE, 3)),
      const_dyadic_flag => cflag,
      dyadic_word => std_logic_vector(to_unsigned(G_WORD, 7)),
      HIGH_SW => hs, LOW_SW => ls, DUTY_VAL_OUT => duty,
      pwm_clk => pclk, pre_pwm_clk => p1, pre_pre_pwm_clk => p2,
      triple_pre_pwm_clk => p3, quadruple_pre_pwm_clk => p4, pwm_clk_x2 => p2x);

  clk <= not clk after 10 ns when not done else clk;

  stim: process
  begin
    rst <= '0';
    wait for 100 ns;
    rst <= '1';
    wait;
  end process;

  mon: process(clk)
    variable n : integer := 0;
    variable l : line;
    variable prev_pclk : std_logic := '0';
  begin
    if rising_edge(clk) and rst = '1' then
      write(l, n); write(l, string'(" "));
      write(l, std_logic'image(hs)(2)); write(l, string'(" "));
      write(l, std_logic'image(ls)(2)); write(l, string'(" "));
      write(l, std_logic'image(pclk)(2)); write(l, string'(" "));
      write(l, std_logic'image(p1)(2)); write(l, string'(" "));
      write(l, to_integer(unsigned(duty)));
      writeline(output, l);
      n := n + 1;
      if pclk = '1' and prev_pclk = '0' and G_RAMP = 1 then
        uin <= std_logic_vector(unsigned(uin) + 1);
      end if;
      prev_pclk := pclk;
      if n >= G_NPER * 513 then
        done <= true;
      end if;
    end if;
  end process;
end sim;
