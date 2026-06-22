-- counter increments every 20ns

-- 5/6/7/8/9 BIT duty cycle
-- -- 9bit: 1 + 511 + 1 = 513
-- -- 8bit: 1 + (255*2) + 2 = 1+510+2 = 513
-- -- 7bit: 2 + (127*4) + 3 = 2+508+3 = 513
-- -- 6bit: 4 + (63*8) + 5 = 4+504+5 = 513
-- -- 5bit: 8 + (31*16) + 9 = 8+496+9 = 513

-- fsw = 97466 Hz (513 clock cycles)

-- Dead-time = 120ns (6 clock cylces)

-- clk_97466 clock signal with fsw and 50% duty
-- -- pre_clk_97466: early rise by 20ns
-- -- pre_pre_clk_97466: early rise by 40ns
-- -- triple_pre_clk_97_var: early rise by 60ns

-- new value of duty cycle is loaded at the beginning of new period

-- toggles HIGH_SW complementary LOW_SW seperated by dead time


library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

entity pwm_97466hz is
	port( 
			RST: in std_logic;
			CLK_50: in std_logic;
			
			DUTY_IN: in std_logic_vector(11 downto 0) := (others=>'0'); -- 12bit value
			
			HIGH_SW_5: out std_logic;  -- 
			LOW_SW_5: out std_logic; -- 
			
			HIGH_SW_6: out std_logic;
			LOW_SW_6: out std_logic; 		
			
			HIGH_SW_7: out std_logic;
			LOW_SW_7: out std_logic; 		
			
			HIGH_SW_8: out std_logic;
			LOW_SW_8: out std_logic; 	
			
			HIGH_SW_9: out std_logic;
			LOW_SW_9: out std_logic; 
			
			clk_97466: out std_logic;
			
			pre_clk_97466: out std_logic; -- early clock rise by (1clk = 20ns)
			pre_pre_clk_97466: out std_logic; -- early clock rise by (2clk = 40ns)
			triple_pre_clk_97: out std_logic; -- early clock rise by (3clk = 60ns)
			quadruple_pre_clk_97: out std_logic; -- early clock rise by (4clk = 80ns)
			
			clk_194932: out std_logic --clk_97466_sig x 2
			
		 );
end pwm_97466hz;


architecture behav1 of pwm_97466hz is

	SIGNAL dty_5bit_sig: integer range 0 to 8191:= 0;
	SIGNAL dty_6bit_sig: integer range 0 to 8191:= 0;
	SIGNAL dty_7bit_sig: integer range 0 to 8191:= 0;
	SIGNAL dty_8bit_sig: integer range 0 to 8191:= 0;
	SIGNAL dty_9bit_sig: integer range 0 to 8191:= 0;
	
	SIGNAL unsigned_dty_5bit_sig: unsigned(4 downto 0);
	SIGNAL unsigned_dty_6bit_sig: unsigned(5 downto 0);
	SIGNAL unsigned_dty_7bit_sig: unsigned(6 downto 0);
	SIGNAL unsigned_dty_8bit_sig: unsigned(7 downto 0);
	SIGNAL unsigned_dty_9bit_sig: unsigned(8 downto 0);

begin

	----------------------------------------------
	---- COMBINATORIAL ---
	----------------------------------------------
	dty_5bit_sig <= to_integer(unsigned_dty_5bit_sig);
	dty_6bit_sig <= to_integer(unsigned_dty_6bit_sig);
	dty_7bit_sig <= to_integer(unsigned_dty_7bit_sig);
	dty_8bit_sig <= to_integer(unsigned_dty_8bit_sig);
	dty_9bit_sig <= to_integer(unsigned_dty_9bit_sig);
	
	unsigned_dty_5bit_sig <= unsigned(DUTY_IN(11 downto 7));
	unsigned_dty_6bit_sig <= unsigned(DUTY_IN(11 downto 6));
	unsigned_dty_7bit_sig <= unsigned(DUTY_IN(11 downto 5));
	unsigned_dty_8bit_sig <= unsigned(DUTY_IN(11 downto 4));
	unsigned_dty_9bit_sig <= unsigned(DUTY_IN(11 downto 3));


	-- Sequential part --
	---------------------
	p1: process(CLK_50,RST)
			
		variable cnt_clk: integer range 0 to 8191 := 0;
		
		variable duty_in_var: unsigned(11 downto 0) := (others=>'0');
		
		variable dty_5bit_var: integer range 0 to 8191 := 0;
		variable dty_6bit_var: integer range 0 to 8191 := 0;
		variable dty_7bit_var: integer range 0 to 8191 := 0;
		variable dty_8bit_var: integer range 0 to 8191 := 0;
		variable dty_9bit_var: integer range 0 to 8191 := 0;
		
		variable HSW_5bit_var: std_logic := '0';
		variable LSW_5bit_var: std_logic := '0';
		
		variable HSW_6bit_var: std_logic := '0';
		variable LSW_6bit_var: std_logic := '0';
		
		variable HSW_7bit_var: std_logic := '0';
		variable LSW_7bit_var: std_logic := '0';
		
		variable HSW_8bit_var: std_logic := '0';
		variable LSW_8bit_var: std_logic := '0';
		
		variable HSW_9bit_var: std_logic := '0';
		variable LSW_9bit_var: std_logic := '0';
		
		variable clk_97_var: std_logic := '0';
		variable pre_clk_97_var: std_logic := '0';
		variable pre_pre_clk_97_var: std_logic := '0';
		variable triple_pre_clk_97_var: std_logic := '0';
		variable quadruple_pre_clk_97_var: std_logic := '0';
		
		variable clk_194_var: std_logic := '0'; --clk_97466_sig x 2
		
	begin
	
		if (RST = '0') then
			cnt_clk := 0;
			
			duty_in_var := (others=>'0');
		
			HSW_5bit_var := '0';
			LSW_5bit_var := '0';

			HSW_6bit_var := '0';
			LSW_6bit_var := '0';

			HSW_7bit_var := '0';
			LSW_7bit_var := '0';

			HSW_8bit_var := '0';
			LSW_8bit_var := '0';

			HSW_9bit_var := '0';
			LSW_9bit_var := '0';
			
			clk_97_var := '0';
			pre_clk_97_var := '0';
			pre_pre_clk_97_var := '0';
			triple_pre_clk_97_var := '0';
			quadruple_pre_clk_97_var := '0';
			
			clk_194_var := '0';
			
		else
			if rising_edge(CLK_50) then
			
				cnt_clk := cnt_clk + 1;
			
				-- at the start of the period load new duty cycle value
				if (cnt_clk = 1) then
					-- latch duty cycle value at the beginning of switching cycle
--					duty_in_var := unsigned(DUTY_IN);
					
					dty_5bit_var := (dty_5bit_sig * 16) + 8;
--					dty_5bit_var := (19 * 16) + 8;
--					dty_5bit_var := 248;
					dty_6bit_var := (dty_6bit_sig * 8) + 4;
--					dty_6bit_var := 248;
					dty_7bit_var := (dty_7bit_sig * 4) + 2;
--					dty_7bit_var := 248;
					dty_8bit_var := (dty_8bit_sig * 2) + 1;
--					dty_8bit_var := 248;
					dty_9bit_var := (dty_9bit_sig) + 1;
--					dty_9bit_var := 248;
					
					clk_97_var := '1'; -- CLOCKS
					
					clk_194_var := '1';
				end if;
				
				-- 5bit
				if (cnt_clk <= dty_5bit_var) then
					HSW_5bit_var := '1';
					LSW_5bit_var := '0';
				else
					HSW_5bit_var := '0';
					if (cnt_clk > (dty_5bit_var + 6)) AND (dty_5bit_var <= 495) then
						if (cnt_clk <= 507) then
							LSW_5bit_var := '1';
						else
							LSW_5bit_var := '0';
						end if;
					end if;
				end if;
				
				-- 6bit
				if (cnt_clk <= dty_6bit_var) then
					HSW_6bit_var := '1';
					LSW_6bit_var := '0';
				else
					HSW_6bit_var := '0';
					if (cnt_clk > (dty_6bit_var + 6)) AND (dty_6bit_var <= 495) then
						if (cnt_clk <= 507) then
							LSW_6bit_var := '1';
						else
							LSW_6bit_var := '0';
						end if;
					end if;
				end if;
				
				-- 7bit
				if (cnt_clk <= dty_7bit_var) then
					HSW_7bit_var := '1';
					LSW_7bit_var := '0';
				else
					HSW_7bit_var := '0';
					if (cnt_clk > (dty_7bit_var + 6)) AND (dty_7bit_var <= 495) then
						if (cnt_clk <= 507) then
							LSW_7bit_var := '1';
						else
							LSW_7bit_var := '0';
						end if;
					end if;
				end if;
				
				-- 8bit
				if (cnt_clk <= dty_8bit_var) then
					HSW_8bit_var := '1';
					LSW_8bit_var := '0';
				else
					HSW_8bit_var := '0';
					if (cnt_clk > (dty_8bit_var + 6)) AND (dty_8bit_var <= 495) then
						if (cnt_clk <= 507) then
							LSW_8bit_var := '1';
						else
							LSW_8bit_var := '0';
						end if;
					end if;
				end if;
				
				-- 9bit
				if (cnt_clk <= dty_9bit_var) then
					HSW_9bit_var := '1';
					LSW_9bit_var := '0';
				else
					HSW_9bit_var := '0';
					if (cnt_clk > (dty_9bit_var + 6)) AND (dty_9bit_var <= 495) then
						if (cnt_clk <= 507) then
							LSW_9bit_var := '1';
						else
							LSW_9bit_var := '0';
						end if;
					end if;
				end if;
				
				------------------------------------
				-- Clocks
				if (cnt_clk = 127) then
					clk_194_var := '0';
				end if;
				
				if (cnt_clk = 257) then
					clk_97_var := '0';
					pre_clk_97_var := '0';
					pre_pre_clk_97_var := '0';
					triple_pre_clk_97_var := '0';
					quadruple_pre_clk_97_var := '0';
					clk_194_var := '1';
				end if;
				
				if (cnt_clk = 385) then
					clk_194_var := '0';
				end if;
				
				
				-- 80ns earlier
				if (cnt_clk = 497) then
					quadruple_pre_clk_97_var := '1';
				end if;
				
				-- 60ns earlier
				if (cnt_clk = 501) then
					triple_pre_clk_97_var := '1';
				end if;
				
				-- 40ns earlier
				if (cnt_clk = 505) then
					pre_pre_clk_97_var := '1';
				end if;
				
				-- 20ns earlier
				if (cnt_clk = 509) then
					pre_clk_97_var := '1';
				end if;
				
				if (cnt_clk = 513) then
					cnt_clk := 0;
				end if;
				
						
				HIGH_SW_5 <= HSW_5bit_var;
				LOW_SW_5 <= LSW_5bit_var;
						
				HIGH_SW_6 <= HSW_6bit_var;
				LOW_SW_6 <= LSW_6bit_var;
						
				HIGH_SW_7 <= HSW_7bit_var;
				LOW_SW_7 <= LSW_7bit_var;
						
				HIGH_SW_8 <= HSW_8bit_var;
				LOW_SW_8 <= LSW_8bit_var;
						
				HIGH_SW_9 <= HSW_9bit_var;
				LOW_SW_9 <= LSW_9bit_var;
				
				clk_97466 <= clk_97_var;
				pre_clk_97466 <= pre_clk_97_var;
				pre_pre_clk_97466 <= pre_pre_clk_97_var;
				triple_pre_clk_97 <= triple_pre_clk_97_var;
				quadruple_pre_clk_97 <= quadruple_pre_clk_97_var;
				
				clk_194932 <= clk_194_var;
				
			end if; --rising edge
		end if; --RST
		
	end process p1;

	
	-- Combinational section --
	---------------------------

end behav1;

