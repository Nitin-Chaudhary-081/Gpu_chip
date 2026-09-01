SIM ?= icarus
TOPLEVEL_LANG ?= verilog
COCOTB_MAKEFILES := $(shell /home/ubuntu/.local/bin/cocotb-config --makefiles)

VERILOG_SOURCES_sram := $(CURDIR)/sram_4k.sv
TOPLEVEL_sram := sram_4k
MODULE_sram := test_sram_cocotb

sram:
	rm -rf $(CURDIR)/sim_build
	$(MAKE) -f $(COCOTB_MAKEFILES)/Makefile.sim \
		SIM=$(SIM) TOPLEVEL_LANG=$(TOPLEVEL_LANG) \
		VERILOG_SOURCES="$(VERILOG_SOURCES_sram)" \
		TOPLEVEL=$(TOPLEVEL_sram) MODULE=$(MODULE_sram) \
		PYTHONPATH=/home/ubuntu/gpu_chip:$(PYTHONPATH)

lint:
	verilator --lint-only --top-module sram_4k $(CURDIR)/sram_4k.sv && echo "LINT sram_4k PASS"

clean::
	rm -rf sim_build __pycache__ results.xml .pytest_cache
	rm -f *.vcd
