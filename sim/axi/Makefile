SIM ?= icarus
TOPLEVEL_LANG ?= verilog
COCOTB_MAKEFILES := $(shell /home/ubuntu/.local/bin/cocotb-config --makefiles)
VERILOG_SOURCES_axi := $(CURDIR)/axi_slave.sv
TOPLEVEL_axi := axi_slave
MODULE_axi := test_axi_cocotb
axi:
	rm -rf $(CURDIR)/sim_build
	$(MAKE) -f $(COCOTB_MAKEFILES)/Makefile.sim SIM=$(SIM) TOPLEVEL_LANG=$(TOPLEVEL_LANG) VERILOG_SOURCES="$(VERILOG_SOURCES_axi)" TOPLEVEL=$(TOPLEVEL_axi) MODULE=$(MODULE_axi) PYTHONPATH=/home/ubuntu/gpu_chip:$(PYTHONPATH)
lint:
	verilator --lint-only --top-module axi_slave $(CURDIR)/axi_slave.sv && echo "LINT axi_slave PASS"
clean::
	rm -rf sim_build __pycache__ results.xml .pytest_cache
	rm -f *.vcd
