"""Tests for 4D cache virtual addressing + determinism gpu.md:7,11,16"""
import numpy as np
from sim.cache4d.cache4d import Cache4D, LinearCache, Coord4D

def test_virtual_mapping_deterministic():
    c4 = Cache4D()
    coord = Coord4D(5,7,3,9)
    loc1 = c4.physical_location(coord)
    loc2 = c4.physical_location(coord)
    assert loc1 == loc2

def test_routing_scales():
    c4 = Cache4D(banks=16)
    w = c4.wire_count_model(n_per_dim=32)
    assert w["naive_wires"] == 32**4
    assert w["virtual_wires"] == 16*64
    assert w["reduction_factor"] > 1000
    assert w["complexity_naive"] == "O(n^4)"
    assert w["complexity_virtual"] == "O(n^2)"

def test_deterministic_latency_bounded():
    c4 = Cache4D()
    rng = np.random.default_rng(0)
    for _ in range(500):
        coord = Coord4D(int(rng.integers(0,64)), int(rng.integers(0,64)), int(rng.integers(0,32)), int(rng.integers(0,16)))
        c4.store(coord, np.ones(4))
    stats = c4.latency_stats()
    # Bounded between 4 and 10 (4 + 3*2)
    assert stats["min"] >= 4
    assert stats["max"] <= 10
    assert stats["deterministic"]
    # Variance should be limited (only 4 possible values)
    assert stats["variance"] < 10

def test_linear_cache_variable_latency():
    lin = LinearCache()
    c4 = Cache4D()
    rng = np.random.default_rng(1)
    for _ in range(500):
        coord = Coord4D(int(rng.integers(0,64)), int(rng.integers(0,64)), int(rng.integers(0,32)), int(rng.integers(0,16)))
        lin.store(coord, np.ones(4))
        c4.store(coord, np.ones(4))
    lin_stats = lin.latency_stats()
    c4_stats = c4.latency_stats()
    # Linear has higher variance / not deterministic
    assert lin_stats["variance"] > 0
    # But 4D is deterministic
    assert c4_stats["deterministic"]
    assert not lin_stats["deterministic"]

def test_hit_miss():
    c4 = Cache4D()
    coord = Coord4D(1,2,3,4)
    data = np.array([1,2,3,4,5,6,7,8])
    c4.store(coord, data)
    res = c4.load(coord)
    assert res["hit"]
    assert np.allclose(res["data"], data)

def test_nonexistent_is_miss():
    c4 = Cache4D()
    res = c4.load(Coord4D(99,99,99,99))
    assert not res["hit"]
    assert res["data"] is None

def test_bank_distribution():
    c4 = Cache4D(banks=16)
    counts = [0]*16
    for x in range(32):
        for y in range(32):
            loc = c4.physical_location(Coord4D(x,y,0,0))
            counts[loc["bank"]] += 1
    # Should be relatively uniform (hash)
    assert max(counts) - min(counts) < 100  # not skewed >100
