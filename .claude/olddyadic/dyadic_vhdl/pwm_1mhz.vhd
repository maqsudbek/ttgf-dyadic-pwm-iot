-- counter increments every 20ns

-- 3 bit duty cyle
-- -- 0 + 6 * 7 + 8 = 50 clk


-- fsw = 1 MHz (1000000 hz)

-- Dead-time = 120ns (6 clock cylces)

-- clk_1mhz = clock with 50% duty cycle

-- new value of duty cycle is loaded at the beginning of new period

-- toggles HIGH_SW complementary LOW_SW seperated by dead time


library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;


entity pwm_1mhz is
	port( 
			RST: in std_logic;
			CLK_50: in std_logic;
			
			DUTY_IN: in std_logic_vector(2 downto 0) := (others=>'0'); -- 3bit value
			
			HIGH_SW_3: out std_logic;  -- 
			LOW_SW_3: out std_logic; -- 
			
			clk_1mhz: out std_logic --1 Mhz clock
			
		 );
end pwm_1mhz;


architecture behav1 of pwm_1mhz is

	SIGNAL dty_3bit_sig: integer range 0 to 8191:= 0;
	
	SIGNAL unsigned_dty_3bit_sig: unsigned(2 downto 0);

begin

	----------------------------------------------
	---- COMBINATORIAL ---
	----------------------------------------------
	
	unsigned_dty_3bit_sig <= unsigned(DUTY_IN(2 downto 0));
	
	dty_3bit_sig <= to_integer(unsigned_dty_3bit_sig);


	-- Sequential part --
	---------------------
	p1: process(CLK_50,RST)
			
		variable cnt_clk: integer range 0 to 8191 := 0;
		
		variable dty_3bit_var: integer range 0 to 8191 := 0;
		
		variable HSW_3bit_var: std_logic := '0';
		variable LSW_3bit_var: std_logic := '0';
		
		
		variable clk_1mhz_var: std_logic := '0'; --1 Mhz
		
	begin
	
		if (RST = '0') then
			cnt_clk := 0;
		
			HSW_3bit_var := '0';
			LSW_3bit_var := '0';
			
			clk_1mhz_var := '0';
			
		else
			if rising_edge(CLK_50) then
			
				cnt_clk := cnt_clk + 1;
			
				-- at the start of the period load new duty cycle value
				if (cnt_clk = 1) then
					-- latch duty cycle value at the beginning of switching cycle
					
					dty_3bit_var := (dty_3bit_sig * 6) + 0;
					
					clk_1mhz_var := '1'; --1 Mhz
				end if;
				
				-- 3bit
				if (cnt_clk <= dty_3bit_var) then
					HSW_3bit_var := '1';
					LSW_3bit_var := '0';
				else
					HSW_3bit_var := '0';
					if (cnt_clk > (dty_3bit_var + 6)) AND (dty_3bit_var <= 32) then
						if (cnt_clk <= 44) then
							LSW_3bit_var := '1';
						else
							LSW_3bit_var := '0';
						end if;
					end if;
				end if;
				
				------------------------------------
				-- Clocks
				if (cnt_clk >= 25) then
					clk_1mhz_var := '0';
				end if;
	
				-- reset counter
				if (cnt_clk = 50) then
					cnt_clk := 0;
				end if;
				
						
				HIGH_SW_3 <= HSW_3bit_var;
				LOW_SW_3 <= LSW_3bit_var;
				
				clk_1mhz <= clk_1mhz_var;
				
			end if; --rising edge
		end if; --RST
		
	end process p1;

	
	-- Combinational section --
	---------------------------

end behav1;

