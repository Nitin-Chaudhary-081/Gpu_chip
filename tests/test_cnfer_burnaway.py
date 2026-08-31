"""Tests for CNFET chirality trap + DGU + burn-away gpu.md:9,14"""
import pytest
from sim.cnfet.cnfet_model import CNFETArray, P_METAL_RAW

def test_raw_yield_is_low():
    arr = CNFETArray(n_transistors=20000, tubes_per_device=8, seed=42)
    y = arr.raw_yield()
    # With 33% metallic per tube, 8 tubes -> P(fail)=1-(0.67)^8 ≈ 0.96 -> yield ~4%
    # But after? Raw should be < 20% for 8 tubes
    assert y < 0.20, f"raw yield {y} unexpectedly high"
    assert y > 0.01

def test_dgu_improves_yield():
    arr = CNFETArray(n_transistors=20000, tubes_per_device=8, seed=1)
    y_raw = arr.raw_yield()
    arr.apply_dgu()
    y_dgu = arr.effective_yield()
    assert y_dgu > y_raw
    assert y_dgu > 0.85, f"DGU yield {y_dgu} should be >85%"

def test_burn_away_achieves_high_yield():
    arr = CNFETArray(n_transistors=20000, tubes_per_device=8, seed=2)
    arr.apply_dgu()
    arr.apply_burn_away(pulses=2)
    y = arr.effective_yield()
    assert y > 0.99, f"burn yield {y} should be >99%"

def test_power_saving():
    arr = CNFETArray(n_transistors=50000, tubes_per_device=8, seed=0)
    p = arr.power_saving_vs_si()
    assert p["p_cnfet_W"] < p["p_si_W"]
    assert p["saving_factor"] > 2.5
    assert p["vdd_cnfet"] == 0.45
    assert p["vdd_si"] == 0.9

def test_chirality_physics_sanity():
    # 1 tube/device -> yield = 1 - 0.33 = 0.67 theoretical
    arr = CNFETArray(n_transistors=50000, tubes_per_device=1, seed=0)
    y = arr.raw_yield()
    assert 0.60 < y < 0.74
