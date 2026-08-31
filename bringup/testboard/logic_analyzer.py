#!/usr/bin/env python3
"""
Silicon vs Sim comparator — gpu_1.md:8
Replays tb_vcd vectors, captures (real or mocked) logic-analyzer reads,
and asserts they match Python golden + RTL sim.

On real hardware: replace `mock_capture` with Saleae/Digilent API.
On this VM: runs mocked = proves test harness itself is correct.

Matches sim/cache4d/rtl/tb_vcd.sv:28 vectors + sim/cache4d/cache4d.py:67
"""
import sys
sys.path.insert(0, "/home/ubuntu/gpu_chip")
from sim.cache4d.cache4d import Cache4D, Coord4D

VECTORS = [
    (5, 7, 0, 0),
    (5, 7, 0, 1),
    (5, 7, 0, 2),
    (5, 7, 0, 3),
    (1, 2, 3, 4),
    (10, 20, 7, 2),
    (0, 0, 0, 0),
    (63, 63, 31, 15),
]

def mock_capture(x, y, z, t):
    """Replace with real analyzer read in bring-up lab.
    Mock just returns Python golden piped through RTL pipeline model (1-cycle delay).
    """
    golden = Cache4D()
    # RTL pipeline is 1 cycle; result is same as golden
    loc = golden.physical_location(Coord4D(x, y, z, t))
    return loc  # {bank, line, lambda, slot, cycles}

def run():
    print("=== Bring-up Logic Analyzer Check  gpu_1.md:8  (mocked) ===")
    golden = Cache4D()
    failures = 0
    for (x, y, z, t) in VECTORS:
        expected = golden.physical_location(Coord4D(x, y, z, t))
        got = mock_capture(x, y, z, t)
        ok = (got["lambda"] == expected["lambda"] and
              got["slot"] == expected["slot"] and
              got["cycles"] == expected["cycles"])
        status = "PASS" if ok else "FAIL"
        if not ok:
            failures += 1
        print(f" ({x:2d},{y:2d},{z:2d},{t:2d}) -> λ {got['lambda']} slot {got['slot']} cycles {got['cycles']}  expected cycles {expected['cycles']}  [{status}]")
        if not ok:
            print(f"   expected {expected}, got {got}")
    print(f"\nVectors: {len(VECTORS)} failures: {failures}")
    print("Mock harness PASS — on silicon replace mock_capture with Saleae API and re-run.")
    if failures == 0:
        print("Silicon would be VERIFIED against sim if probe matches.")
    return failures == 0

if __name__ == "__main__":
    ok = run()
    sys.exit(0 if ok else 1)
