.DEFAULT_GOAL := test-all

SIM ?= icarus
CORE ?= lfsr64

# Ovaj Makefile se nalazi u test/cocotb_tests/.
THIS_DIR := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))
MODEL_DIR := $(abspath $(THIS_DIR)/..)
SRC_DIR := $(abspath $(THIS_DIR)/../../src)

ifeq ($(CORE),lfsr64)
RTL_BASENAME := lfsr64_core
TEST_MODULE := test_lfsr64_rtl
else ifeq ($(CORE),xoroshiro64ss)
RTL_BASENAME := xoroshiro64ss_core
TEST_MODULE := test_xoroshiro64ss_rtl
else ifeq ($(CORE),pcg32_oneseq)
RTL_BASENAME := pcg32_oneseq_core
TEST_MODULE := test_pcg32_oneseq_rtl
else
$(error Unknown CORE='$(CORE)'; use lfsr64, xoroshiro64ss, or pcg32_oneseq)
endif

TOPLEVEL_LANG := verilog
VERILOG_SOURCES := $(SRC_DIR)/$(RTL_BASENAME).v

# Canonical cocotb 2.x names plus legacy aliases used by older TT templates.
COCOTB_TOPLEVEL := $(RTL_BASENAME)
COCOTB_TEST_MODULES := $(TEST_MODULE)
TOPLEVEL := $(COCOTB_TOPLEVEL)
MODULE := $(COCOTB_TEST_MODULES)

export PYTHONPATH := $(THIS_DIR):$(MODEL_DIR):$(PYTHONPATH)

SIM_BUILD := $(THIS_DIR)/sim_build/$(CORE)
COCOTB_RESULTS_FILE := $(SIM_BUILD)/results.xml

.PHONY: test-all test-lfsr64 test-xoroshiro64ss test-pcg32 prng-help

test-all: test-lfsr64 test-xoroshiro64ss test-pcg32

test-lfsr64:
	$(MAKE) --no-print-directory sim CORE=lfsr64

test-xoroshiro64ss:
	$(MAKE) --no-print-directory sim CORE=xoroshiro64ss

test-pcg32:
	$(MAKE) --no-print-directory sim CORE=pcg32_oneseq

prng-help:
	@printf '%s\n' \
	  'make test-all              Run all three cocotb regressions' \
	  'make test-lfsr64           Run only lfsr64_core' \
	  'make test-xoroshiro64ss    Run only xoroshiro64ss_core' \
	  'make test-pcg32            Run only pcg32_oneseq_core' \
	  'Add SIM=icarus or SIM=verilator to select a simulator.'

COCOTB_CONFIG := $(shell command -v cocotb-config 2>/dev/null)

ifeq ($(COCOTB_CONFIG),)
.PHONY: sim
sim:
	@printf '%s\n' \
	  'cocotb-config was not found.' \
	  'Install cocotb and a supported simulator, then run make again.'
	@exit 1
else
include $(shell cocotb-config --makefiles)/Makefile.sim
endif
