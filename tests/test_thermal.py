"""Tests for M3D thermal trap + microfluidics gpu.md:10,15"""
from sim.thermal.thermal3d import M3DStack, compare_stacks

def test_thermal_trapping():
    # Without cooling, inner tiers hotter than ambient
    s = M3DStack(has_microfluidics=False, p_per_cell=0.8)
    s.step(200)
    m = s.metrics()
    assert m["t_max"] > 50, f"Tmax {m['t_max']} should be hot without cooling"
    assert m["t_per_tier"][1] > m["t_per_tier"][-1] or m["t_per_tier"][0] > 25

def test_microfluidics_cools():
    cmp = compare_stacks(p_per_cell=0.8)
    assert cmp["with"]["t_max"] < cmp["without"]["t_max"]
    assert cmp["delta_tmax"] > 10, f"delta {cmp['delta_tmax']} should be >10C"

def test_ald_limit_respected_with_cooling():
    # With cooling, even at moderate power, stay <400C gpu.md:15
    s = M3DStack(has_microfluidics=True, p_per_cell=1.0)
    s.step(300)
    m = s.metrics()
    assert not m["ald_violation"]
    assert m["t_max"] < 400

def test_hotspot_without_cooling_grows_with_power():
    c_low = compare_stacks(p_per_cell=0.4)
    c_high = compare_stacks(p_per_cell=1.2)
    assert c_high["without"]["t_max"] > c_low["without"]["t_max"]

def test_deterministic_step():
    s1 = M3DStack(has_microfluidics=True, p_per_cell=0.8)
    s1.step(100)
    m1 = s1.metrics()["t_max"]
    s2 = M3DStack(has_microfluidics=True, p_per_cell=0.8)
    s2.step(100)
    m2 = s2.metrics()["t_max"]
    assert m1 == m2
