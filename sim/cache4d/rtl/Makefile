# Cocotb Makefile for Phase B RTL proof
# Uses Icarus Verilog (fits 1.9GB VM) — also works with Verilator via SIM=verilator
# gpu.md:7,11,16

SIM ?= icarus
TOPLEVEL_LANG ?= verilog
COCOTB_MAKEFILES := $(shell /home/ubuntu/.local/bin/cocotb-config --makefiles)

# Controller tests
VERILOG_SOURCES_cache := $(CURDIR)/cache_4d_controller.sv
TOPLEVEL_cache := cache_4d_controller
MODULE_cache := test_cache4d_cocotb

# Arbiter tests
VERILOG_SOURCES_wdm := $(CURDIR)/wdm_tdm_arbiter.sv
TOPLEVEL_wdm := wdm_tdm_arbiter
MODULE_wdm := test_wdm_cocotb

# Default: run cache controller
all: cache

cache:
	rm -rf $(CURDIR)/sim_build
	$(MAKE) -f $(COCOTB_MAKEFILES)/Makefile.sim \
		SIM=$(SIM) TOPLEVEL_LANG=$(TOPLEVEL_LANG) \
		VERILOG_SOURCES="$(VERILOG_SOURCES_cache)" \
		TOPLEVEL=$(TOPLEVEL_cache) MODULE=$(MODULE_cache) \
		PYTHONPATH=/home/ubuntu/gpu_chip:$(PYTHONPATH)

wdm:
	rm -rf $(CURDIR)/sim_build
	$(MAKE) -f $(COCOTB_MAKEFILES)/Makefile.sim \
		SIM=$(SIM) TOPLEVEL_LANG=$(TOPLEVEL_LANG) \
		VERILOG_SOURCES="$(VERILOG_SOURCES_wdm)" \
		TOPLEVEL=$(TOPLEVEL_wdm) MODULE=$(MODULE_wdm) \
		PYTHONPATH=/home/ubuntu/gpu_chip:$(PYTHONPATH)

# Track 3 co-sim  gpu_2.md:8  compiler_pass -> RTL
VERILOG_SOURCES_cosim := $(CURDIR)/cache_4d_controller.sv
TOPLEVEL_cosim := cache_4d_controller
MODULE_cosim := test_cosim_matmul

cosim:
	rm -rf $(CURDIR)/sim_build
	$(MAKE) -f $(COCOTB_MAKEFILES)/Makefile.sim \
		SIM=$(SIM) TOPLEVEL_LANG=$(TOPLEVEL_LANG) \
		VERILOG_SOURCES="$(VERILOG_SOURCES_cosim)" \
		TOPLEVEL=$(TOPLEVEL_cosim) MODULE=$(MODULE_cosim) \
		PYTHONPATH=/home/ubuntu/gpu_chip:$(PYTHONPATH)

# Verilator lint (no sim)
lint:
	verilator --lint-only --top-module cache_4d_controller $(CURDIR)/cache_4d_controller.sv && echo "LINT cache PASS"
	verilator --lint-only --top-module wdm_tdm_arbiter $(CURDIR)/wdm_tdm_arbiter.sv && echo "LINT wdm PASS"

clean::
	rm -rf sim_build __pycache__ results.xml .pytest_cache
	rm -f *.vcd

# VCD waveform target via plain iverilog (no cocotb overhead)
vcd:
	iverilog -g2012 -o /tmp/tb.vvp $(CURDIR)/cache_4d_controller.sv $(CURDIR)/wdm_tdm_arbiter.sv $(CURDIR)/tb_cache4d.sv
	vvp /tmp/tb.vvp
	iverilog -g2012 -o /tmp/tb_vcd.vvp $(CURDIR)/cache_4d_controller.sv $(CURDIR)/tb_vcd.sv && vvp /tmp/tb_vcd.vvp && echo "VCD at /tmp/wave.vcd - open with gtkwave /tmp/wave.vcd"
