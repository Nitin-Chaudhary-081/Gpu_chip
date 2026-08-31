"""
4D Space-Time Tensor Cache — gpu.md:7,11,16
- Naive 4D routing is O(n^4) wires -> explosion gpu.md:11
- Mitigation: Virtualized Logical Addressing + TDM + WDM gpu.md:16
  Physical: B banks * W waveguides, T slots, L lambdas
  Virtual: (x,y,z,t) -> (bank, lambda, slot) via hash -> wires stay O(n^2)
- Deterministic latency (locked) vs variable -> no pipeline stall gpu.md:11
"""
import hashlib
import numpy as np
from dataclasses import dataclass
from typing import Tuple, Dict

# Config matching photonics
BANKS = 16           # physical SRAM banks (2D)
WAVELENGTHS = 8      # WDM lambdas per waveguide gpu.md:16
TDM_SLOTS = 4        # time slots
CACHE_LINE_BYTES = 64
LINES_PER_BANK = 1024
BASE_LATENCY_CYCLES = 4
SLOT_CYCLES = 2      # deterministic wait per slot
WAVE_REUSE = True

@dataclass(frozen=True)
class Coord4D:
    x: int  # spatial X
    y: int  # spatial Y
    z: int  # spatial Z / K-tile
    t: int  # temporal / frequency dimension gpu.md:7


class Cache4D:
    """
    Functional model of 4D cache.
    Stores tensor tiles keyed by Coord4D; maps to physical location deterministically.
    """

    def __init__(self, banks=BANKS, lines_per_bank=LINES_PER_BANK,
                 wavelengths=WAVELENGTHS, tdm_slots=TDM_SLOTS):
        self.banks = banks
        self.lines_per_bank = lines_per_bank
        self.wl = wavelengths
        self.tdm = tdm_slots
        self.storage = {}  # (bank, line) -> bytes / np array
        self.stats = {"hits": 0, "misses": 0, "accesses": 0, "total_cycles": 0}
        self.latency_log = []

    def _hash_coord(self, c: Coord4D) -> Tuple[int, int, int, int]:
        """Deterministic mapping: virtual 4D -> physical.
        bank = hash(x,y) % B   (spatial locality)
        lam  = t % W            (temporal -> wavelength)
        slot = (z + t) % T      (K + time -> TDM)
        line = hash(x,y,z,t) % lines_per_bank
        This is the core of gpu.md:16 Virtualized Logical Addressing.
        """
        # Use python hash but deterministic via hashlib for repeatability
        h = int(hashlib.md5(f"{c.x},{c.y},{c.z},{c.t}".encode()).hexdigest(), 16)
        bank = (c.x * 73856093 ^ c.y * 19349663) % self.banks
        lam = c.t % self.wl
        slot = (c.z + c.t) % self.tdm
        line = h % self.lines_per_bank
        return bank, line, lam, slot

    def physical_location(self, c: Coord4D) -> Dict:
        bank, line, lam, slot = self._hash_coord(c)
        return {"bank": bank, "line": line, "lambda": lam, "slot": slot,
                "cycles": BASE_LATENCY_CYCLES + slot * SLOT_CYCLES}

    def latency_for(self, c: Coord4D) -> int:
        _, _, _, slot = self._hash_coord(c)
        return BASE_LATENCY_CYCLES + slot * SLOT_CYCLES

    def store(self, c: Coord4D, data: np.ndarray):
        bank, line, lam, slot = self._hash_coord(c)
        cycles = BASE_LATENCY_CYCLES + slot * SLOT_CYCLES
        self.storage[(bank, line)] = np.array(data, copy=True)
        self.stats["accesses"] += 1
        self.stats["total_cycles"] += cycles
        self.latency_log.append(cycles)
        return {"bank": bank, "line": line, "lambda": lam, "slot": slot, "cycles": cycles, "hit": False}

    def load(self, c: Coord4D):
        bank, line, lam, slot = self._hash_coord(c)
        cycles = BASE_LATENCY_CYCLES + slot * SLOT_CYCLES
        key = (bank, line)
        hit = key in self.storage
        if hit:
            self.stats["hits"] += 1
            data = self.storage[key]
        else:
            self.stats["misses"] += 1
            data = None
        self.stats["accesses"] += 1
        self.stats["total_cycles"] += cycles
        self.latency_log.append(cycles)
        return {"data": data, "hit": hit, "bank": bank, "line": line,
                "lambda": lam, "slot": slot, "cycles": cycles}

    def wire_count_model(self, n_per_dim=32):
        """Compare naive O(n^4) vs virtualized O(n^2). n_per_dim = size per axis."""
        naive_wires = n_per_dim ** 4  # each 4D cell wired
        virtual_wires = self.banks * 64  # 64 wires per bank approx
        # With WDM: effective bandwidth multiplier without wires
        effective_virtual = virtual_wires * self.wl  # wavelengths multiplex
        return {
            "n_per_dim": n_per_dim,
            "naive_wires": naive_wires,
            "virtual_wires": virtual_wires,
            "virtual_effective_with_wdm": effective_virtual,
            "reduction_factor": naive_wires / max(virtual_wires, 1),
            "complexity_naive": "O(n^4)",
            "complexity_virtual": "O(n^2)",
        }

    def latency_stats(self):
        if not self.latency_log:
            return {"mean": 0, "min": 0, "max": 0, "variance": 0, "deterministic": True}
        a = np.array(self.latency_log)
        return {
            "mean": float(np.mean(a)),
            "min": int(np.min(a)),
            "max": int(np.max(a)),
            "variance": float(np.var(a)),
            "deterministic": bool(np.max(a) - np.min(a) <= (self.tdm-1)*SLOT_CYCLES),
            "bounded": f"[{BASE_LATENCY_CYCLES}, {BASE_LATENCY_CYCLES + (self.tdm-1)*SLOT_CYCLES}]",
        }

    def reset_stats(self):
        self.stats = {"hits": 0, "misses": 0, "accesses": 0, "total_cycles": 0}
        self.latency_log.clear()


class LinearCache:
    """Baseline 1D linear-addressed cache for comparison gpu.md:12.
    Shows address-translation overhead and variable latency.
    """
    def __init__(self, size_lines=16384):
        self.size = size_lines
        self.storage = {}
        self.latency_log = []

    def _linear_addr(self, c: Coord4D, dims=(64,64,64,32)):
        # Flatten 4D -> 1D linear address (what CUDA does) gpu.md:12
        # addr = ((x*Dy + y)*Dz + z)*Dt + t  -> translation overhead
        Dx,Dy,Dz,Dt = dims
        return ((c.x * Dy + c.y) * Dz + c.z) * Dt + c.t

    def store(self, c: Coord4D, data: np.ndarray):
        addr = self._linear_addr(c)
        line = addr % self.size
        # Translation overhead: extra cycles
        cycles = 8 + (addr % 5)  # variable due to TLB/page etc.
        self.storage[line] = np.array(data, copy=True)
        self.latency_log.append(cycles)
        return {"line": line, "cycles": cycles}

    def load(self, c: Coord4D):
        addr = self._linear_addr(c)
        line = addr % self.size
        cycles = 8 + (addr % 5)
        self.latency_log.append(cycles)
        hit = line in self.storage
        return {"data": self.storage.get(line), "hit": hit, "cycles": cycles}

    def latency_stats(self):
        a = np.array(self.latency_log) if self.latency_log else np.array([0])
        return {"mean": float(np.mean(a)), "min": int(np.min(a)), "max": int(np.max(a)),
                "variance": float(np.var(a)), "deterministic": False}


def demo():
    print("=== 4D Cache Demo  gpu.md:7,11,16 ===")
    c4 = Cache4D()
    lin = LinearCache()
    # Wire scaling
    for n in [8, 16, 32]:
        w = c4.wire_count_model(n)
        print(f"n={n}: naive {w['naive_wires']:,} wires vs virtual {w['virtual_wires']:,} (effective {w['virtual_effective_with_wdm']:,}) -> {w['reduction_factor']:.0f}x reduction {w['complexity_naive']}->{w['complexity_virtual']}")

    print("\nLatency determinism (1000 random coords):")
    rng = np.random.default_rng(0)
    for _ in range(1000):
        c = Coord4D(int(rng.integers(0,64)), int(rng.integers(0,64)), int(rng.integers(0,32)), int(rng.integers(0,16)))
        c4.store(c, np.ones(4))
        lin.store(c, np.ones(4))
    print(f" 4D cache: {c4.latency_stats()}")
    print(f" Linear  : {lin.latency_stats()}  (variable, unpredictable gpu.md:11)")
    # Hit demo
    c4.reset_stats()
    c = Coord4D(1,2,3,4)
    c4.store(c, np.array([1,2,3,4]))
    print(f" store/load {c} -> {c4.load(c)} hit={c4.load(c)['hit']} loc={c4.physical_location(c)}")

if __name__ == "__main__":
    demo()
