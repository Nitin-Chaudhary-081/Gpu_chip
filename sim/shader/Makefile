# Cocotb Makefile for shader — simd_alu + register_file
SIM ?= icarus
TOPLEVEL_LANG ?= verilog
COCOTB_MAKEFILES := $(shell /home/ubuntu/.local/bin/cocotb-config --makefiles)

VERILOG_SOURCES_simd := $(CURDIR)/simd_alu.sv
TOPLEVEL_simd := simd_alu
MODULE_simd := test_simd_alu_cocotb

simd:
	rm -rf $(CURDIR)/sim_build
	$(MAKE) -f $(COCOTB_MAKEFILES)/Makefile.sim \
		SIM=$(SIM) TOPLEVEL_LANG=$(TOPLEVEL_LANG) \
		VERILOG_SOURCES="$(VERILOG_SOURCES_simd)" \
		TOPLEVEL=$(TOPLEVEL_simd) MODULE=$(MODULE_simd) \
		PYTHONPATH=/home/ubuntu/gpu_chip:$(PYTHONPATH)

# register_file later
VERILOG_SOURCES_rf := $(CURDIR)/register_file.sv
TOPLEVEL_rf := register_file
MODULE_rf := test_register_file_cocotb

rf:
	rm -rf $(CURDIR)/sim_build
	$(MAKE) -f $(COCOTB_MAKEFILES)/Makefile.sim \
		SIM=$(SIM) TOPLEVEL_LANG=$(TOPLEVEL_LANG) \
		VERILOG_SOURCES="$(VERILOG_SOURCES_rf)" \
		TOPLEVEL=$(TOPLEVEL_rf) MODULE=$(MODULE_rf) \
		PYTHONPATH=/home/ubuntu/gpu_chip:$(PYTHONPATH)

systolic:
	rm -rf $(CURDIR)/sim_build
	$(MAKE) -f $(COCOTB_MAKEFILES)/Makefile.sim \
		SIM=$(SIM) TOPLEVEL_LANG=$(TOPLEVEL_LANG) \
		VERILOG_SOURCES="$(CURDIR)/systolic_4x4.sv" \
		TOPLEVEL=systolic_4x4 MODULE=test_systolic_cocotb \
		PYTHONPATH=/home/ubuntu/gpu_chip:$(PYTHONPATH)

# simple drop-in
systolic-simple:
	rm -rf $(CURDIR)/sim_build
	$(MAKE) -f $(COCOTB_MAKEFILES)/Makefile.sim \
		SIM=$(SIM) TOPLEVEL_LANG=$(TOPLEVEL_LANG) \
		VERILOG_SOURCES="$(CURDIR)/systolic_4x4.sv" \
		TOPLEVEL=systolic_4x4_simple MODULE=test_systolic_simple_cocotb \
		PYTHONPATH=/home/ubuntu/gpu_chip:$(PYTHONPATH)

lint:
	verilator --lint-only --top-module simd_alu $(CURDIR)/simd_alu.sv && echo "LINT simd_alu PASS"
	verilator --lint-only --top-module register_file $(CURDIR)/register_file.sv && echo "LINT rf PASS"
	verilator --lint-only --top-module systolic_4x4 $(CURDIR)/systolic_4x4.sv && echo "LINT systolic_4x4 PASS"

clean::
	rm -rf sim_build __pycache__ results.xml .pytest_cache
	rm -f *.vcd
