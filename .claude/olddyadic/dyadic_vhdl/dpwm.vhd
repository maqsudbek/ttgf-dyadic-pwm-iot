-----------------------------------------------------------------------------------
-- DIGITAL PWM generator entity
-- 12 bit control signal

-- This module determines the duty cycle value at each cycle depending on:
--  -- number of bits
--  -- chosen mode (normal/dyadic)
--  -- chosen dyadic word length
-- from the given 12bit control signal

-- number of bits used for duty cycle: 5/6/7/8/9
-- 2 different modes: NORMAL or DYADIC
-- switching frequencies: ~100kHz (97466 Hz)
-- number of bits of dyadic word length can be chosen: 2/3/4/5/6/7

-- USES external complementary pwm generation for a given duty cycle, number of bits

-- Gives out duty cycle value (12bit vector) at each switching sync

library IEEE;
use IEEE.STD_LOGIC_1164.ALL;
use IEEE.NUMERIC_STD.ALL;
	--------------------------------------------------------------------------------------
ENTITY dpwm is
	port(
		CLK_50 : IN STD_LOGIC;
		RST : IN STD_LOGIC;
		
		U_IN: IN std_logic_vector(11 downto 0); --12 bit control signal
		
		PWM_BITS: IN std_logic_vector(3 downto 0):= "0101"; --4bits (5/6/7/8/9 bit pwm)
		
		DYADIC_LEN: IN std_logic_vector(2 downto 0); --3bit [0,2-7] (also serves as LSB length - m)
	
		dpwm_mode: IN std_logic_vector(2 downto 0); --3bit Mode of DPWM:
																	-- 0: Normal (also when dyadic_len = 0, regardless of  dpwm_mode)
																	-- 1: Dyadic
																	-- 2: Dithering_v1 (MSB and LSB are sampled at every sw cycle)
																	-- 3: Dithering_v2 (MSB at every sw cycle, LSB at every 2^m cycle)
																	-- 4: Dithering_v3 (MSB and LSB at every 2^m cycle)
																	-- other: Normal
		
		const_dyadic_flag: IN   std_logic; -- 1:constant dyadic word;  0:not constant
		dyadic_word: IN   std_logic_vector(6 downto 0); --7bit dyadic word
		
		HIGH_SW: out std_logic;  -- GPIO-00
		LOW_SW: out std_logic; -- GPIO-01
		
		DUTY_VAL_OUT: OUT std_logic_vector(11 downto 0); -- (MSBs are zero; 5/6/7/8/9bit depending on chosen pwm bits)
		
		pwm_clk: out std_logic; -- pwm clock (50% duty)
		pre_pwm_clk: out std_logic;  -- early rise by (1clk)
		pre_pre_pwm_clk: out std_logic;  -- early rise by (2clk)
		triple_pre_pwm_clk: out std_logic;  -- early rise by (3clk)
		quadruple_pre_pwm_clk: out std_logic;  -- early rise by (4clk)
		
		pwm_clk_x2: out std_logic -- twice as fast as pwm_clk
		 );
END dpwm; 

ARCHITECTURE behav1 of dpwm is

	------------------------COMPONENT DECLARATIONS -------------------------------
		--============================================
	-- -- PWM generator
	COMPONENT pwm_97466hz is
		PORT( 
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
			
			clk_194932: out std_logic --clk_97466 x 2
		 );
	END COMPONENT;
	
	--------------------------------------------------------------------------------------
	----------------- SIGNALS ----------------------------------------------------------
	
	-- PWM signals
	SIGNAL duty_cycle_sig: std_logic_vector(11 downto 0) := (others=>'0'); -- 12bit value
	SIGNAL duty_in_sig: std_logic_vector(11 downto 0) := (others=>'0'); -- 12bit value
	
	SIGNAL LSB_len_sig: integer:= 0; -- 3bit value
	
	SIGNAL dpwm_mode_sig: integer:= 0; -- 3bit value
	
	SIGNAL pwm_bits_sig: integer:= 0; -- 4bit value
	
	SIGNAL high_pwm5_sig: std_logic := '0'; -- 5bit pwm
	SIGNAL low_pwm5_sig: std_logic := '0';
	SIGNAL high_pwm6_sig: std_logic := '0'; -- 6bit pwm
	SIGNAL low_pwm6_sig: std_logic := '0';		
	SIGNAL high_pwm7_sig: std_logic := '0'; -- 7bit pwm
	SIGNAL low_pwm7_sig: std_logic := '0';	
	SIGNAL high_pwm8_sig: std_logic := '0'; -- 8bit pwm
	SIGNAL low_pwm8_sig: std_logic := '0';		
	SIGNAL high_pwm9_sig: std_logic := '0'; -- 9bit pwm
	SIGNAL low_pwm9_sig: std_logic := '0';		
	
	SIGNAL clk_97466_sig: std_logic := '0';
	SIGNAL pre_clk_97466_sig: std_logic := '0'; -- early clock rise by (1clk = 20ns)
	SIGNAL pre_pre_clk_97466_sig: std_logic := '0'; -- early clock rise by (2clk = 40ns)
	SIGNAL triple_pre_clk_97_sig: std_logic := '0'; -- early clock rise by (3clk = 60ns)
	SIGNAL quadruple_pre_clk_97_sig: std_logic := '0'; -- early clock rise by (4clk = 80ns)
	
	SIGNAL clk_194932_sig: std_logic := '0'; --clk_97466 x 2
	
BEGIN
	------------------------------------------------------------------------------------
	----------- COMPONENT INSTANTIATION ----------------------
			-- -- PWM generator
	pwm0: pwm_97466hz PORT MAP( 
		RST => RST,
		CLK_50 => CLK_50,
		
		DUTY_IN => duty_in_sig,
		
		HIGH_SW_5 => high_pwm5_sig,
		LOW_SW_5 => low_pwm5_sig,
		
		HIGH_SW_6 => high_pwm6_sig,
		LOW_SW_6 => low_pwm6_sig,		
		
		HIGH_SW_7 => high_pwm7_sig,
		LOW_SW_7 => low_pwm7_sig,	
		
		HIGH_SW_8 => high_pwm8_sig,
		LOW_SW_8 => low_pwm8_sig,	
		
		HIGH_SW_9 => high_pwm9_sig,
		LOW_SW_9 => low_pwm9_sig,
		
		clk_97466 => clk_97466_sig,
		pre_clk_97466 => pre_clk_97466_sig,
		pre_pre_clk_97466 => pre_pre_clk_97466_sig,
		triple_pre_clk_97 => triple_pre_clk_97_sig,
		quadruple_pre_clk_97 => quadruple_pre_clk_97_sig,
		
		clk_194932 => clk_194932_sig
	);
	
	------------------------------------------------------------------------------------------	
		---------------- CONCURRENT STATEMENTS ---------------
	-- DUTY cycle current value given depending on the bits and mode being used
	DUTY_VAL_OUT <= duty_cycle_sig;
	
	pwm_bits_sig <= to_integer(unsigned(PWM_BITS));
	
	LSB_len_sig <= to_integer(unsigned(DYADIC_LEN));
	
	dpwm_mode_sig <= to_integer(unsigned(dpwm_mode));
	
	-- PWM outputs depending on frequency and number of bits used--
	HIGH_SW <= high_pwm5_sig when (pwm_bits_sig = 5) else
				  high_pwm6_sig when (pwm_bits_sig = 6) else
				  high_pwm7_sig when (pwm_bits_sig = 7) else
				  high_pwm8_sig when (pwm_bits_sig = 8) else
				  high_pwm9_sig when (pwm_bits_sig = 9) else
				  high_pwm5_sig;
	
	LOW_SW <=  low_pwm5_sig when (pwm_bits_sig = 5) else
				  low_pwm6_sig when (pwm_bits_sig = 6) else
				  low_pwm7_sig when (pwm_bits_sig = 7) else
				  low_pwm8_sig when (pwm_bits_sig = 8) else
				  low_pwm9_sig when (pwm_bits_sig = 9) else
				  low_pwm5_sig;
				  
	-- Clock signal
	pwm_clk <= clk_97466_sig;
	pre_pwm_clk <= pre_clk_97466_sig; -- early clock rise by (1clk)
	pre_pre_pwm_clk <= pre_pre_clk_97466_sig;-- early clock rise by (2clk)
	triple_pre_pwm_clk <= triple_pre_clk_97_sig;-- early clock rise by (3clk)
	quadruple_pre_pwm_clk <= quadruple_pre_clk_97_sig;-- early clock rise by (4clk)
	pwm_clk_x2 <= clk_194932_sig; --clk_97466 x 2
	
	------------------------------------------------------------------------------------------
	--------------- STATEMENTS -------------------------------------
	
	p1: process(RST, pre_clk_97466_sig) is
	
		variable curr_dty_int_var: integer range 0 to 4095;
		
		variable duty_in_var: std_logic_vector(11 downto 0);
		
		variable data_IN: unsigned(11 downto 0);
		variable dyadic_word_var: unsigned(6 downto 0);
		
		variable tmp_data: unsigned(1 downto 0); -- 2bit variable
		
		variable added_bit_val: std_logic; -- 1bit variable
				
		variable counter_7bit: unsigned (6 downto 0); --for only 5bit
		variable counter_6bit: unsigned (5 downto 0); --for only 5-6 bit
		variable counter_5bit: unsigned (4 downto 0); --for only 5-7 bit
		variable counter_4bit: unsigned (3 downto 0); --for only 5-8 bit
		variable counter_3bit: unsigned (2 downto 0); --for only 5-9 bit
		variable counter_2bit: unsigned (1 downto 0); --for only 5-10 bit
		
		variable counter_val: integer; --for only 5bit
		variable counter_7bit_val: integer; --for only 5bit
		variable counter_6bit_val: integer; --for only 5-6 bit
		variable counter_5bit_val: integer; --for only 5-7 bit
		variable counter_4bit_val: integer; --for only 5-8 bit
		variable counter_3bit_val: integer; --for only 5-9 bit
		variable counter_2bit_val: integer; --for only 5-10 bit
		
		variable index: integer range 0 to 15;
		variable i:	integer range 0 to 15;	
		variable k:	integer range 0 to 15;	
		
		variable max_allowed_bits:	integer range 5 to 12;
		
		variable LSB_len_var:	integer range 0 to 12;
		
		variable LSB_unsigned_var:	unsigned(6 downto 0); -- max 7bit LSB
		variable MSB_unsigned_var:	unsigned(8 downto 0); -- max 9bit MSB
		
		variable LSB_value_var:	integer range 0 to 128;
		
		variable dpwm_mode_var:	integer range 0 to 12;
		
		variable pwm_bits_var:	integer range 0 to 12;
		
	begin
	
		if (RST = '0') then
		
			tmp_data := "00";
			
			added_bit_val := '0';
			
			counter_7bit := "0000000";
			counter_6bit := "000000";
			counter_5bit := "00000";
			counter_4bit := "0000";
			counter_3bit := "000";
			counter_2bit := "00";
			
			index := 0;
			i := 0;
			
			LSB_len_var := 0;
			
			LSB_value_var := 0;
			
			max_allowed_bits := 5;
			
			curr_dty_int_var := 0;
			duty_in_var := (others => '0');
		else
			if rising_edge(pre_clk_97466_sig) then
			
				data_IN := unsigned(U_IN);
				dyadic_word_var := unsigned(dyadic_word);
				
				LSB_len_var := LSB_len_sig;
				
				dpwm_mode_var := dpwm_mode_sig; --3bit Mode of DPWM:
																	-- 0: Normal (also when dyadic_len = 0, regardless of  dpwm_mode)
																	-- 1: Dyadic
																	-- 2: Dithering_v1 (MSB and LSB are sampled at every sw cycle)
																	-- 3: Dithering_v2 (MSB at every sw cycle, LSB at every 2^m cycle)
																	-- 4: Dithering_v3 (MSB and LSB at every 2^m cycle)
																	-- other: Normal
				
				pwm_bits_var := pwm_bits_sig;
				
				
				counter_7bit_val := to_integer(counter_7bit);	
				counter_6bit_val := to_integer(counter_6bit);
				counter_5bit_val := to_integer(counter_5bit);
				counter_4bit_val := to_integer(counter_4bit);
				counter_3bit_val := to_integer(counter_3bit);
				counter_2bit_val := to_integer(counter_2bit);
				
				tmp_data(1) := '0';
				----------------------------------------------------------------------------------
				-- DYADIC or DITHERING	
				if (LSB_len_var = 7) then
					-- 7bit LSB
					
					-- for DYADIC
					max_allowed_bits := 5;
					
					index := 6;
					for i in 6 downto 0 loop
						if (counter_7bit(i) = '1') then
							index := i;
						end if;
					end loop;

					index:= 6-index;
					
--					index := index + (12 - max_allowed_bits - LSB_len_var);
					
					-- take last 7bit LSB from u-control
					LSB_unsigned_var(6 downto 0) := data_IN(6 downto 0);
					
					counter_val := counter_7bit_val;
					
				elsif (LSB_len_var = 6) then
					-- 6bit LSB
					
					-- for DYADIC
					if (pwm_bits_var > 6) then
						max_allowed_bits := 6;
					else
						max_allowed_bits := pwm_bits_var;
					end if;
					
					index := 5;
					for i in 5 downto 0 loop
						if (counter_6bit(i) = '1') then
							index := i;
						end if;
					end loop;

					index:= 5-index;
					
--					index := index + (12 - max_allowed_bits - LSB_len_var);
					
					-- take 6bit LSB from the end of PWM bits, 6 bit to the right side
					LSB_unsigned_var(6) := '0';
					LSB_unsigned_var(5 downto 0) := data_IN((11-max_allowed_bits) downto (6-max_allowed_bits));
					
					counter_val := counter_6bit_val;

										
				elsif (LSB_len_var = 5) then
					-- 5bit LSB
					
					-- for DYADIC
					if (pwm_bits_var > 7) then
						max_allowed_bits := 7;
					else
						max_allowed_bits := pwm_bits_var;
					end if;
					
					index := 4;
					for i in 4 downto 0 loop
						if (counter_5bit(i) = '1') then
							index := i;
						end if;
					end loop;

					index:= 4-index;
					
--					index := index + (12 - max_allowed_bits - LSB_len_var);
					
					-- take 5 bit LSB from the end of PWM bits, 5 bit to the right side
					LSB_unsigned_var(6 downto 5) := (others => '0');
					LSB_unsigned_var(4 downto 0) := data_IN((11-max_allowed_bits) downto (7-max_allowed_bits));
					
					counter_val := counter_5bit_val;
	
				elsif (LSB_len_var = 4) then
					-- 4bit LSB
					
					-- for DYADIC
					if (pwm_bits_var > 8) then
						max_allowed_bits := 8;
					else
						max_allowed_bits := pwm_bits_var;
					end if;
					
					index := 3;
					for i in 3 downto 0 loop
						if (counter_4bit(i) = '1') then
							index := i;
						end if;
					end loop;

					index:= 3-index;
					
--					index := index + (12 - max_allowed_bits - LSB_len_var);
					
					-- take 4 bit LSB from the end of PWM bits, 4 bit to the right side
					LSB_unsigned_var(6 downto 4) := (others => '0');
					LSB_unsigned_var(3 downto 0) := data_IN((11-max_allowed_bits) downto (8-max_allowed_bits));
					
					counter_val := counter_4bit_val;
	
				elsif (LSB_len_var = 3) then
					-- 3 BIT LSB
					
					-- for DYADIC
					if (pwm_bits_var > 9) then
						max_allowed_bits := 9;
					else
						max_allowed_bits := pwm_bits_var;
					end if;
					
					index := 2;
					for i in 2 downto 0 loop
						if (counter_3bit(i) = '1') then
							index := i;
						end if;
					end loop;

					index:= 2-index;
					
--					index := index + (12 - max_allowed_bits - LSB_len_var);
					
					-- take 3 bit LSB from the end of PWM bits, 3 bit to the right side
					LSB_unsigned_var(6 downto 3) := (others => '0');
					LSB_unsigned_var(2 downto 0) := data_IN((11-max_allowed_bits) downto (9-max_allowed_bits));
					
					counter_val := counter_3bit_val;
			
				elsif (LSB_len_var = 2) then
					-- 2 BIT LSB
					
					-- for DYADIC
					if (pwm_bits_var > 10) then
						max_allowed_bits := 10;
					else
						max_allowed_bits := pwm_bits_var;
					end if;
											
					index := 1;
					for i in 1 downto 0 loop
						if (counter_2bit(i) = '1') then
							index := i;
						end if;
					end loop;

					index:= 1-index;
					
--					index := index + (12 - max_allowed_bits - LSB_len_var);
					
					-- take 2 bit LSB from the end of PWM bits, 2 bit to the right side
					LSB_unsigned_var(6 downto 2) := (others => '0');
					LSB_unsigned_var(1 downto 0) := data_IN((11-max_allowed_bits) downto (10-max_allowed_bits));
					
					counter_val := counter_2bit_val;
		
				elsif (LSB_len_var = 1) then
					-- 1 BIT LSB
					
					-- for DYADIC						
					if (pwm_bits_var > 11) then
						max_allowed_bits := 11;
					else
						max_allowed_bits := pwm_bits_var;
					end if;
					
					index := 0;
					
--					index := index + (12 - max_allowed_bits - LSB_len_var);
					
					-- take 1 bit LSB from the end of PWM bits, 1 bit to the right side
					LSB_unsigned_var(6 downto 1) := (others => '0');
					LSB_unsigned_var(0) := data_IN(11-max_allowed_bits);
					
					if (counter_val = 0) then
						counter_val := 1;
					else
						counter_val := 0;
					end if;
					
				else
					-- 0 bit LSB
					-- Normal Mode
					
					if (pwm_bits_var > 12) then
						max_allowed_bits := 12;
					else
						max_allowed_bits := pwm_bits_var;
					end if;
					
					LSB_unsigned_var(6 downto 0) := (others => '0');
					
					counter_val := 0;
					
					dpwm_mode_var := 0;
					
				end if; -- LSB length
				
				-- increment counters
				counter_7bit := counter_7bit + 1;	
				counter_6bit := counter_6bit + 1;
				counter_5bit := counter_5bit + 1;
				counter_4bit := counter_4bit + 1;
				counter_3bit := counter_3bit + 1;
				counter_2bit := counter_2bit + 1;
				
				
				if (index > 6) then
					index := 6;
				end if;
							
				
				-----------------------------------------------------------------------------------------------
				
				
				-----------------------------------------------------------------------------------------------
				-- evaluate last bit value to be added to MSB
				-- -- depending on PWM mode
				
				if (dpwm_mode_var = 1) then
					-- DYADIC mode
					
					-- 9bit MSB of u-control signal  (at every sw cycle)
					MSB_unsigned_var(8 downto 0) := data_IN(11 downto 3); 
					
					-- identify dyadic sequence bit
					if (LSB_len_var > 0) then
						-- if dyadic_len_var is positive
						if (const_dyadic_flag = '0') then
							-- if const_dyadic_flag is FALSE
							-- dyadic word is taken from control signal LSBs
							if (counter_val > 0) then
								tmp_data(0) := LSB_unsigned_var(index);
							else
								tmp_data(0) := '0';
							end if;
							
						else
							-- constant dyadic word is used for sequence
							if (LSB_len_var >= 2) then
							
								if (counter_val > 0) then
									tmp_data(0) := dyadic_word_var(index);
								else
									tmp_data(0) := '0';
								end if;
								
							else
								-- if constant dyadic word and dyadic length < 2 (0 or 1)
								-- it is also considered as NORMAL mode
								tmp_data(0) := '0';
							end if;
							 
						end if; -- const_dyadic_flag = 0
						
					else
						-- if LSB_len_var = 0
						--  DYADIC mode was chosen, but LSB length = 0
						--  so, it is in NORMAL mode
						tmp_data(0) := '0';
						
					end if; -- LSB_len_var > 0
					
					
				------------------------------------------------------------------------------------------------------	
				elsif (dpwm_mode_var = 2) then
					-- 2: Dithering_v1 (MSB and LSB are sampled at every sw cycle)
					
					-- 9bit MSB of u-control signal  (at every sw cycle)
					MSB_unsigned_var(8 downto 0) := data_IN(11 downto 3);
					
					-- LSB sampled (at every sw cycle)
					LSB_value_var := to_integer(LSB_unsigned_var);

					if (LSB_value_var >= counter_val) then
						tmp_data(0) := '1';
					else
						tmp_data(0) := '0';
					end if;
						
				------------------------------------------------------------------------------------------------------	
				elsif (dpwm_mode_var = 3) then
					-- 3: Dithering_v2 (MSB at every sw cycle, LSB at every 2^m cycle)
					
					-- 9bit MSB of u-control signal  (at every sw cycle)
					MSB_unsigned_var(8 downto 0) := data_IN(11 downto 3);
					
					-- LSB sampled (at every 2^m cycle)
					if (counter_val = 1) then
						LSB_value_var := to_integer(LSB_unsigned_var);
					end if;
					
					if (LSB_value_var >= counter_val) then
						tmp_data(0) := '1';
					else
						tmp_data(0) := '0';
					end if;
					
				------------------------------------------------------------------------------------------------------	
				elsif (dpwm_mode_var = 4) then
					-- 4: Dithering_v3 (MSB and LSB at every 2^m cycle)
					
					
					if (counter_val = 1) then
					
						-- 9bit MSB of u-control signal  (at every sw cycle)
						MSB_unsigned_var(8 downto 0) := data_IN(11 downto 3);
						
						-- LSB sampled (at every 2^m cycle)
						LSB_value_var := to_integer(LSB_unsigned_var);
						
					end if;
					
					if (LSB_value_var >= counter_val) then
						tmp_data(0) := '1';
					else
						tmp_data(0) := '0';
					end if;
					
				------------------------------------------------------------------------------------------------------
				else
					-- NORMAL mode (dpwm_mode_var = 0)
					
					-- 9bit MSB of u-control signal
					MSB_unsigned_var(8 downto 0) := data_IN(11 downto 3);
					
					tmp_data(0) := '0';
					
				end if; -- dpwm_mode_var
				-----------------------------------------------------------------------------------------------

				
				--------------------------------------------------------------------------------
				-- Duty cycle based on PWM number of bits
				if (pwm_bits_var = 6) then
					curr_dty_int_var := to_integer(MSB_unsigned_var(8 downto 3)) + to_integer(tmp_data);
					if (curr_dty_int_var > 63) then
						curr_dty_int_var := 63;
					end if;
					duty_in_var(11 downto 6) := std_logic_vector(to_unsigned(curr_dty_int_var, 6));
					duty_in_var(5 downto 0) := (others => '0');
					
				elsif (pwm_bits_var = 7) then
					curr_dty_int_var := to_integer(MSB_unsigned_var(8 downto 2)) + to_integer(tmp_data);
					if (curr_dty_int_var > 127) then
						curr_dty_int_var := 127;
					end if;
					duty_in_var(11 downto 5) := std_logic_vector(to_unsigned(curr_dty_int_var, 7));
					duty_in_var(4 downto 0) := (others => '0');
					
				elsif (pwm_bits_var = 8) then
					curr_dty_int_var := to_integer(MSB_unsigned_var(8 downto 1)) + to_integer(tmp_data);
					if (curr_dty_int_var > 255) then
						curr_dty_int_var := 255;
					end if;
					duty_in_var(11 downto 4) := std_logic_vector(to_unsigned(curr_dty_int_var, 8));
					duty_in_var(3 downto 0) := (others => '0');
					
				elsif (pwm_bits_var = 9) then
					curr_dty_int_var := to_integer(MSB_unsigned_var(8 downto 0)) + to_integer(tmp_data);
					if (curr_dty_int_var > 511) then
						curr_dty_int_var := 511;
					end if;
					duty_in_var(11 downto 3) := std_logic_vector(to_unsigned(curr_dty_int_var, 9));
					duty_in_var(2 downto 0) := (others => '0');
					
				else
					-- 5bit by default
					curr_dty_int_var := to_integer(MSB_unsigned_var(8 downto 4)) + to_integer(tmp_data);
					if (curr_dty_int_var > 31) then
						curr_dty_int_var := 31;
					end if;
					duty_in_var(11 downto 7) := std_logic_vector(to_unsigned(curr_dty_int_var, 5));
					duty_in_var(6 downto 0) := (others => '0');
					
				end if; -- PWM bits
				
				-- duty_cycle_sig goes OUT to outside
				duty_cycle_sig <= std_logic_vector(to_unsigned(curr_dty_int_var, 12));
				
				-- duty_in_sig is send into PWM generator
				duty_in_sig <= duty_in_var;
				
				
			end if; --rising edge
		end if;-- RST
		
				
	end process p1;
	

END behav1;

	
