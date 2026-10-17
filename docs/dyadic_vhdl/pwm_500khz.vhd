-- counter increments every 20ns

-- 4 bit duty cyle
-- -- 0 + 6 * 16 + 4 = 100 clk


-- fsw = 500 kHz

-- Dead-time = 120ns (6 clock cylces)

-- clk_500khz = clock with 50% duty cycle

-- new value of duty cycle is loaded at the beginning of new period

-- toggles HIGH_SW complementary LOW_SW seperated by dead time


library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;


entity pwm_500khz is
	port( 
			RST: in std_logic;
			CLK_50: in std_logic;
			
			DUTY_IN: in std_logic_vector(3 downto 0) := (others=>'0'); -- 4bit value
			
			HIGH_SW_4: out std_logic;  -- 
			LOW_SW_4: out std_logic; -- 
			
			clk_500khz: out std_logic --500 khz clock
			
		 );
end pwm_500khz;


architecture behav1 of pwm_500khz is

	SIGNAL dty_4bit_sig: integer range 0 to 8191:= 0;
	
	SIGNAL unsigned_dty_4bit_sig: unsigned(3 downto 0);

begin

	----------------------------------------------
	---- COMBINATORIAL ---
	----------------------------------------------
	dty_4bit_sig <= to_integer(unsigned_dty_4bit_sig);
	
	unsigned_dty_4bit_sig <= unsigned(DUTY_IN(3 downto 0));


	-- Sequential part --
	---------------------
	p1: process(CLK_50,RST)
			
		variable cnt_clk: integer range 0 to 8191 := 0;
		
		variable dty_4bit_var: integer range 0 to 8191 := 0;
		
		variable HSW_4bit_var: std_logic := '0';
		variable LSW_4bit_var: std_logic := '0';
		
		
		variable clk_500_var: std_logic := '0'; --500 khz
		
	begin
	
		if (RST = '0') then
			cnt_clk := 0;
		
			HSW_4bit_var := '0';
			LSW_4bit_var := '0';
			
			clk_500_var := '0';
			
		else
			if rising_edge(CLK_50) then
			
				cnt_clk := cnt_clk + 1;
			
				-- at the start of the period load new duty cycle value
				if (cnt_clk = 1) then
					-- latch duty cycle value at the beginning of switching cycle
					
					dty_4bit_var := (dty_4bit_sig * 6) + 0;
					
					clk_500_var := '1'; --500 khz
				end if;
				
				-- 5bit
				if (cnt_clk <= dty_4bit_var) then
					HSW_4bit_var := '1';
					LSW_4bit_var := '0';
				else
					HSW_4bit_var := '0';
					if (cnt_clk > (dty_4bit_var + 6)) AND (dty_4bit_var <= 82) then
						if (cnt_clk <= 94) then
							LSW_4bit_var := '1';
						else
							LSW_4bit_var := '0';
						end if;
					end if;
				end if;
				
				------------------------------------
				-- Clocks
				if (cnt_clk >= 50) then
					clk_500_var := '0';
				end if;
	
				-- reset counter
				if (cnt_clk = 100) then
					cnt_clk := 0;
				end if;
				
						
				HIGH_SW_4 <= HSW_4bit_var;
				LOW_SW_4 <= LSW_4bit_var;
				
				clk_500khz <= clk_500_var;
				
			end if; --rising edge
		end if; --RST
		
	end process p1;

	
	-- Combinational section --
	---------------------------

end behav1;

