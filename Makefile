.PHONY: install test sim matmul thermal cnfet cache clean verilate lint synth synth-wrapper synth-top synth-shader bringup gds drc cocotb cocotb-cosim gls viewer shader sta

PYTHON=python3
PIP=pip3

install:
	$(PIP) install -r requirements.txt

test:
	$(PYTHON) -m pytest tests/ -v

sim: test
	@echo "All sims passed"

matmul:
	$(PYTHON) tests/workloads/matmul.py --compare

thermal:
	$(PYTHON) -c "from sim.thermal.thermal3d import demo; demo()"

cnfet:
	$(PYTHON) -c "from sim.cnfet.cnfet_model import demo; demo()"

cache:
	$(PYTHON) -c "from sim.cache4d.cache4d import demo; demo()"

verilate:
	@echo "Checking Verilator..."
	@which verilator && verilator --version || echo "Verilator not installed. Run: sudo apt install verilator"
	@echo "Checking Icarus..."
	@which iverilog && iverilog -V | head -1 || echo "Icarus not installed"
	@echo "Lint 4D controller..."
	@verilator --lint-only --top-module cache_4d_controller sim/cache4d/rtl/cache_4d_controller.sv && echo "LINT cache4d PASS"
	@verilator --lint-only --top-module wdm_tdm_arbiter sim/cache4d/rtl/wdm_tdm_arbiter.sv && echo "LINT wdm PASS"
	@verilator --lint-only --top-module simd_alu sim/shader/simd_alu.sv && echo "LINT simd_alu PASS"
	@verilator --lint-only --top-module register_file sim/shader/register_file.sv && echo "LINT regfile PASS"
	@verilator --lint-only --top-module systolic_4x4 sim/shader/systolic_4x4.sv && echo "LINT systolic_4x4 PASS"
	@echo "Running RTL testbench via Icarus..."
	@iverilog -g2012 -o /tmp/tb.vvp sim/cache4d/rtl/cache_4d_controller.sv sim/cache4d/rtl/wdm_tdm_arbiter.sv sim/cache4d/rtl/tb_cache4d.sv && vvp /tmp/tb.vvp

cocotb:
	@echo "=== Cocotb Phase B: cache_4d_controller vs Python golden gpu.md:16 ==="
	$(MAKE) -C sim/cache4d/rtl cache SIM=icarus
	@echo "=== Cocotb: wdm_tdm_arbiter gpu.md:6 ==="
	$(MAKE) -C sim/cache4d/rtl wdm SIM=icarus
	@echo "=== Cocotb: simd_alu 8-lane FP32 gpu_A.md:94 ==="
	$(MAKE) -C sim/shader simd SIM=icarus
	@echo "=== Cocotb: register_file 256x32 gpu_A.md:96 ==="
	$(MAKE) -C sim/shader rf SIM=icarus
	@echo "=== Cocotb: systolic_4x4 4x4 GEMM gpu_A.md:39 ==="
	$(MAKE) -C sim/shader systolic SIM=icarus

cocotb-cosim:
	@echo "=== Track 3 Co-Sim  gpu_2.md:8  compiler_pass -> RTL  gpu.md:17->gpu.md:16 ==="
	$(MAKE) -C sim/cache4d/rtl cosim SIM=icarus

vcd:
	@echo "=== VCD waveform for GTKWave ==="
	iverilog -g2012 -o /tmp/tb_vcd.vvp sim/cache4d/rtl/cache_4d_controller.sv sim/cache4d/rtl/tb_vcd.sv && vvp /tmp/tb_vcd.vvp && ls -lh /tmp/wave.vcd && echo "Open: gtkwave /tmp/wave.vcd"

gls:
	@echo "=== Post-layout SDF sim  tb_cache_4d_top.v  (SDF back-annotated) ==="
	@echo "Functional (no SDF):"
	@iverilog -g2012 -o /tmp/tb_top.vvp sim/cache4d/rtl/cache_4d_controller.sv sim/cache4d/rtl/wdm_tdm_arbiter.sv sim/cache4d/rtl/gpu_top.v sim/cache4d/rtl/tb_cache_4d_top.v && vvp /tmp/tb_top.vvp 2>&1 | tail -20
	@echo "SDF-annotated (if openlane/gpu_top/runs/**/sdf/*.sdf exists):"
	@iverilog -g2012 -DSDF -o /tmp/tb_top_sdf.vvp sim/cache4d/rtl/cache_4d_controller.sv sim/cache4d/rtl/wdm_tdm_arbiter.sv sim/cache4d/rtl/gpu_top.v sim/cache4d/rtl/tb_cache_4d_top.v 2>&1 | head -5; vvp /tmp/tb_top_sdf.vvp +sdf_verbose 2>&1 | tail -20 || echo "SDF file not yet generated — run GH Action gds or 'make gds' on 8GB host, then re-run 'make gls'"

vcd-top:
	iverilog -g2012 -o /tmp/tb_top_vcd.vvp sim/cache4d/rtl/cache_4d_controller.sv sim/cache4d/rtl/wdm_tdm_arbiter.sv sim/cache4d/rtl/gpu_top.v sim/cache4d/rtl/tb_cache_4d_top.v && vvp /tmp/tb_top_vcd.vvp && ls -lh /tmp/wave_top.vcd && echo "Open: gtkwave /tmp/wave_top.vcd"

synth:
	@echo "=== Yosys synth  gpu_1.md:2  (Si-proxy, sky130) ==="
	@yosys -s openlane/synth_cache.ys 2>&1 | grep -E "Number of cells|Number of wires|stat|ERROR" | tail -20
	@yosys -s openlane/synth_wdm.ys 2>&1 | grep -E "Number of cells|Number of wires|stat|ERROR" | tail -10
	@echo "JSON: /tmp/synth_cache4d.json /tmp/synth_wdm.json  — proxy for sky130 area  gpu_1.md:3 GDSII"

synth-wrapper:
	@echo "=== Yosys synth wrapper  tt_um_4d_cache  gpu_1.md:6 ==="
	@yosys -p "read_verilog -sv sim/cache4d/rtl/cache_4d_controller.sv tapeout/tt_wrapper.sv; hierarchy -check -top tt_um_4d_cache; proc; opt; synth -top tt_um_4d_cache; stat" 2>&1 | grep -E "Number of cells|ERROR" | tail -10

synth-top:
	@echo "=== Yosys synth top  gpu_top + tt_um_4d_cache  approve spec: macro hardening, 8x8 BRAM ==="
	@yosys -p "read_verilog -sv sim/cache4d/rtl/cache_4d_controller.sv sim/cache4d/rtl/wdm_tdm_arbiter.sv sim/cache4d/rtl/gpu_top.v; hierarchy -check -top gpu_top; proc; opt; synth -top gpu_top; stat" 2>&1 | grep -E "Number of cells|ERROR" | tail -10
	@yosys -p "read_verilog -sv sim/cache4d/rtl/cache_4d_controller.sv sim/cache4d/rtl/wdm_tdm_arbiter.sv sim/cache4d/rtl/gpu_top.v; hierarchy -check -top tt_um_4d_cache; proc; opt; synth -top tt_um_4d_cache; stat" 2>&1 | grep -E "Number of cells|ERROR" | tail -10
	@echo "Top DIE 160x100 tt_um_4d_cache openlane/gpu_top/config.json:12 — macro hardening cache_4d"

synth-shader:
	@echo "=== Yosys synth shader  simd_alu + regfile + systolic  gpu_A.md:37,49 ==="
	@yosys -p "read_verilog -sv sim/shader/simd_alu.sv; hierarchy -check -top simd_alu; proc; opt; synth -top simd_alu; stat" 2>&1 | grep -E "Number of cells|ERROR" | tail -10
	@yosys -p "read_verilog -sv sim/shader/register_file.sv; hierarchy -check -top register_file; proc; opt; synth -top register_file; stat" 2>&1 | grep -E "Number of cells|ERROR" | tail -10
	@yosys -p "read_verilog -sv sim/shader/systolic_4x4.sv; hierarchy -check -top systolic_4x4; proc; opt; synth -top systolic_4x4; stat" 2>&1 | grep -E "Number of cells|ERROR" | tail -10
	@yosys -p "read_verilog -sv sim/shader/systolic_4x4.sv; hierarchy -check -top systolic_4x4_simple; proc; opt; synth -top systolic_4x4_simple; stat" 2>&1 | grep -E "Number of cells|ERROR" | tail -10
	@echo "Shader DIE 200x200 simd_alu openlane/shader/config.json — FP32 TDM4/WDM8, systolic 300x300"

shader:
	@echo "=== Shader Phase D: simd_alu + regfile + systolic + cnfet bridge gpu_A.md:94-98,39 ==="
	@$(MAKE) -C sim/shader simd SIM=icarus 2>&1 | grep -E "PASS|FAIL|test_"
	@$(MAKE) -C sim/shader rf SIM=icarus 2>&1 | grep -E "PASS|FAIL|test_"
	@$(MAKE) -C sim/shader systolic SIM=icarus 2>&1 | grep -E "PASS|FAIL|test_"
	@$(PYTHON) sim/cnfet/cnfet_spice_bridge.py --synthetic 2>&1 | tail -20
	@echo "CNFET bridge synthetic plot /tmp/cnfet_spice_vs_python.png"

sta:
	@echo "=== STA estimate  gpu_A.md:54  10ns +0.25 ==="
	@$(PYTHON) scripts/sta_estimate.py

bringup:
	@echo "=== Bring-up check  gpu_1.md:8  (logic_analyzer.py mocked) ==="
	@$(PYTHON) bringup/testboard/logic_analyzer.py

gds:
	@echo "=== OpenLane GDS  gpu_1.md:2 + gpu_top 160x100 tt_um_4d_cache ==="
	@echo "Run locally with 8GB+: docker run --rm -v \$$PWD:/project -w /project efabless/openlane:latest --design openlane/gpu_top --tag gpu_top  (macro hardening cache_4d)"
	@echo "Or: docker run ... --design openlane/cache4d --tag cache4d  (flat cache only)"
	@echo "Or use TinyTapeout GH Action .github/workflows/gds.yaml  (see tapeout/submission.md)"
	@echo "Outputs: openlane/gpu_top/runs/*/results/final/gds/*.gds  + sdf/*.sdf for 'make gls'  gpu_1.md:3"
	@cat openlane/gpu_top/config.json | grep -E "DESIGN_NAME|PDK|CLOCK|DIE_AREA|FP_PDN|FP_TAP"

drc:
	@echo "=== DRC/LVS waivers  gpu_1.md:4 ==="
	@cat drc_lvs/waivers.md | head -30
	@echo "--- For real DRC: docker run ... && klayout checks openlane/cache4d/runs/*/reports/  ---"

viewer:
	@echo "=== Browser Layout Viewers  docs/gds_viewers.md:1 ==="
	@echo "TinyTapeout GDS Viewer: https://gds-viewer.tinytapeout.com  (drop Actions gds.zip *.gds, inspect met1-5 + 3D)"
	@echo "GDSJam:                https://gdsjam.com  (drag same *.gds, local WebGL, no upload, layer + measure)"
	@echo "GH Action:             .github/workflows/gds.yaml → Actions → gds → Artifacts gds.zip/renders.zip/reports.zip"
	@echo "Get GDS:  gh run list --workflow gds.yaml  |  gh run download  |  or local docker: make gds"
	@cat docs/gds_viewers.md | head -30

lint:
	$(PYTHON) -m py_compile sim/**/*.py

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -name "*.pyc" -delete
	rm -rf .pytest_cache sim_build sim/cache4d/rtl/sim_build /tmp/wave.vcd /tmp/tb.vvp /tmp/tb_vcd.vvp /tmp/synth_*.json
