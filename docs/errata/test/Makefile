# Errata tests (cocotb 2.x + Icarus Verilog).
#
#   make VARIANT=fixed       corrected RTL        vs dpwm.vhd model   (test_fixed.py)
#   make VARIANT=unbiased    corrected RTL + E3   dither average      (test_fixed_unbiased.py)
#   make VARIANT=submitted   SUBMITTED RTL        errata + workarounds (test_submitted.py)
#   make VARIANT=regression  corrected RTL        original test/test.py (10 tests)
#
# ./run_checks.sh runs all four variants and the host-library tests.

VARIANT ?= submitted

SIM ?= icarus
TOPLEVEL_LANG ?= verilog
TOPLEVEL = tb

SRC_DIR  = $(PWD)/../../../src
TEST_DIR = $(PWD)/../../../test
RTL_DIR  = $(PWD)/../rtl

export PYTHONPATH := $(PWD):$(PWD)/../host:$(TEST_DIR):$(PYTHONPATH)

ifeq ($(VARIANT),fixed)
VERILOG_SOURCES = $(RTL_DIR)/dyadic_fixed.v $(SRC_DIR)/project.v $(PWD)/tb_errata.v
COCOTB_TEST_MODULES = test_fixed
else ifeq ($(VARIANT),unbiased)
VERILOG_SOURCES = $(RTL_DIR)/dyadic_fixed.v $(SRC_DIR)/project.v $(PWD)/tb_errata.v
COMPILE_ARGS += -DDYADIC_UNBIASED_DITHER
COCOTB_TEST_MODULES = test_fixed_unbiased
else ifeq ($(VARIANT),submitted)
VERILOG_SOURCES = $(SRC_DIR)/dyadic.v $(SRC_DIR)/project.v $(PWD)/tb_errata.v
COCOTB_TEST_MODULES = test_submitted
else ifeq ($(VARIANT),regression)
VERILOG_SOURCES = $(RTL_DIR)/dyadic_fixed.v $(SRC_DIR)/project.v $(TEST_DIR)/tb.v
COCOTB_TEST_MODULES = test
else
$(error VARIANT must be fixed, unbiased, submitted or regression)
endif

SIM_BUILD = sim_build/$(VARIANT)
COCOTB_RESULTS_FILE = results_$(VARIANT).xml
COMPILE_ARGS += -I$(SRC_DIR)

include $(shell cocotb-config --makefiles)/Makefile.sim
