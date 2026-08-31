"""Tests for photonic interconnect WDM/TDM gpu.md:6,16"""
from sim.photonics.interconnect import PhotonicLink, WDM_TDM_Arbiter, E_PHOTONIC_PJ_PER_BIT, E_ELEC_PJ_PER_BIT

def test_energy_saving():
    link = PhotonicLink()
    cmp = link.compare_vs_copper(bits=1_000_000_000)
    assert cmp["saving_factor"] > 3.0
    assert cmp["photonic_pj"] < cmp["copper_pj"]
    assert E_PHOTONIC_PJ_PER_BIT < E_ELEC_PJ_PER_BIT

def test_bandwidth():
    link = PhotonicLink(n_waveguides=8, wdm=8)
    bw = link.bandwidth_GBps()
    # 8*8*25Gbps /8 = 200 GB/s
    assert 190 < bw < 210

def test_deterministic_latency():
    link = PhotonicLink()
    # latency depends only on slot, not contention
    for slot in range(4):
        l1 = link.latency_ns(wavelength_id=2, tdm_slot=slot)
        l2 = link.latency_ns(wavelength_id=5, tdm_slot=slot)
        assert l1 == l2
        # bounded
        assert 2.0 <= l1 <= 2.0 + 3*1.0

def test_wdm_arbiter_determinism():
    arb = WDM_TDM_Arbiter(wdm=8, tdm=4)
    a1 = arb.allocate(42)
    a2 = arb.allocate(42)
    assert a1 == a2
    # lambda in range
    assert 0 <= a1["lambda"] < 8
    assert 0 <= a1["slot"] < 4
    assert a1["latency_ns"] == 2.0 + a1["slot"]*1.0

def test_power_under_120W():
    # System power at high BW should stay <120W gpu.md:3 combined? photonic alone <40W
    link = PhotonicLink(n_waveguides=8)
    pw = link.power_at_BW(utilization=0.7)
    assert pw < 50, f"photonic power {pw} too high"

def test_parallelism():
    arb = WDM_TDM_Arbiter()
    assert arb.max_parallel_transfers(n_waveguides=8) == 64  # 8*8
