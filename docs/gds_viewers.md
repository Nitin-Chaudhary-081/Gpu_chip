# Browser Layout Viewers — `gpu_1.md:3` GDSII

View the **Si-proxy** GDS (`sky130A`) for `cache_4d_controller.sv:1` (`42 cells`) + `wdm_tdm_arbiter.sv:1` + `tapeout/tt_wrapper.sv:1` without installing `KLayout/OpenROAD`. CNFET/photonics/M3D are waived (`drc_lvs/waivers.md:1`, `docs/tapeout.md:10`) — viewers show `sky130_fd_sc_hd` proxy only.

> GDS source: `openlane/cache4d/runs/cache4d_run/results/final/gds/cache_4d_controller.gds` (`gpu_2.md:4`). On this `1.9GB VM` generate via cloud (`make gds` needs `8GB Docker` — see below); viewers consume that `*.gds` file.

## 1) TinyTapeout GDS Viewer — `gds-viewer.tinytapeout.com`

SkyWater 130nm-tailored. Drop `*.gds` → 2D canvas + 3D metal stack (`met1`–`met5`), via/substrate, routing.

**Steps:**
1. Get GDS: `Actions → gds → Artifacts → gds.zip` (from `.github/workflows/gds.yaml:1`) or local `openlane/cache4d/runs/**/gds/*.gds` after `docker` run.
2. Open `https://gds-viewer.tinytapeout.com` → drag-drop `*.gds`.
3. Toggle layers `met1`–`met5`, `via1`–`via4`, `diff/poly`; use 3D button for tier stack; verify die `200×200um` (`openlane/cache4d/config.json:12`).

**Good for:** TT tile fit check, standard-cell density, `DIE_AREA` vs `160×100um` TT tile (`tapeout/info.yaml:24`).

## 2) GDSJam — `gdsjam.com` (local, no upload)

Client-side WebGL. Drag-drop → instant layer toggles, cross-section measurement, pan/zoom. No server upload.

**Steps:**
1. Same GDS as above.
2. Open `https://gdsjam.com` → drag-drop `*.gds` (file stays in browser).
3. Use layer panel to isolate `sky130` libs, measure cell width, verify `CLOCK 10ns` routing not congested.

**Good for:** Offline review, `1.9GB VM` local check, sharing without TinyTapeout account.

## 3) Automated GH Action Render — `gpu_2.md:4`

Zero-local-RAM path. Push to `main` (or `Run workflow` button) triggers `.github/workflows/gds.yaml:1`:

```bash
git push origin main                # triggers gds job
# or: gh workflow run gds.yaml
```

**What it does:** `efabless/openlane:latest` (`openlane/README.md:16`) runs `Yosys+OpenROAD+Magic+KLayout` in cloud (`ubuntu-latest 8–16GB`), uploads:
- `gds.zip` — `*.gds` for viewers 1 & 2
- `reports.zip` — `DRC/LVS` (`gpu_1.md:4`)
- `renders.zip` — `*.png` 2D/3D top-down renders (also downloadable, not committed — lean)

**Find it:** `GitHub → Actions → gds → <run> → Artifacts`. Download → feed to viewer 1 or 2. Badge in `README.md:1` turns green when GDS is fresh.

## Local fallback (no GH)

```bash
# Needs 8GB+ host — not this VM per Makefile:78
docker run --rm -v $PWD:/project -w /project efabless/openlane:latest \
  --design openlane/cache4d --tag cache4d_run
# then viewers as above
make synth          # still runs here — Yosys gate count proof gpu_1.md:2
make synth-wrapper  # tt_um_4d_cache 131 cells
```

## Lean note

`*.gds` stays in `.gitignore:26` (large). Only this markdown + workflow are committed — no `docs/renders/` bloat. If you later want homepage renders, uncomment commitment in workflow + add `!docs/renders/*.png` to `.gitignore`.
