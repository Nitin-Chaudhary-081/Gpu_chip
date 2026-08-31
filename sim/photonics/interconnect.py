"""
Silicon Photonics interconnect — gpu.md:6,16
- On-chip optical waveguides replace Cu
- fJ/bit energy, WDM (wavelength division) + TDM
"""
import math
from dataclasses import dataclass

# Literature numbers gpu.md:6 "femtojoules-per-bit"
E_ELEC_PJ_PER_BIT = 0.20      # 200 fJ/bit for Cu at 7nm long haul (baseline)
E_PHOTONIC_PJ_PER_BIT = 0.03  # 30 fJ/bit optical gpu.md:6
E_PHOTONIC_LASER_OVERHEAD_PJ = 0.01  # wall-plug + ring tuning

WDM_WAVELENGTHS = 8    # 8 λ per waveguide gpu.md:16
TDM_SLOTS = 4          # 4 time slots
WAVEGUIDE_BW_GBPS_PER_LAMBDA = 25  # 25 Gbps per λ
BASE_LATENCY_NS = 2.0  # optical flight + E/O
TDM_SLOT_NS = 1.0      # per slot wait

@dataclass
class PhotonicLink:
    n_waveguides: int = 8
    wdm: int = WDM_WAVELENGTHS
    tdm: int = TDM_SLOTS
    e_per_bit_pj: float = E_PHOTONIC_PJ_PER_BIT

    def bandwidth_GBps(self):
        # total = waveguides * wavelengths * bw_per_lambda
        total_gbps = self.n_waveguides * self.wdm * WAVEGUIDE_BW_GBPS_PER_LAMBDA
        return total_gbps / 8  # GB/s

    def bandwidth_elec_GBps(self):
        # equivalent Cu for comparison (more wires, higher energy)
        return self.bandwidth_GBps() * 0.6  # Cu would be lower effective due to RC

    def energy_for(self, bits: int, n_hops: int = 1):
        """Energy in pJ (or nJ) for transfer."""
        pj = bits * (self.e_per_bit_pj + E_PHOTONIC_LASER_OVERHEAD_PJ) * n_hops
        return {
            "pj": pj,
            "nj": pj / 1000,
            "uj": pj / 1e6,
            "fJ_per_bit": self.e_per_bit_pj * 1000,
        }

    def latency_ns(self, wavelength_id: int, tdm_slot: int, n_hops: int = 1):
        """Deterministic latency gpu.md:16 — locked via TDM.
        No unpredictable stall; wait is slot-dependent."""
        return BASE_LATENCY_NS * n_hops + tdm_slot * TDM_SLOT_NS

    def power_at_BW(self, utilization=0.7):
        """Power in W at given BW utilization."""
        gbps = self.n_waveguides * self.wdm * WAVEGUIDE_BW_GBPS_PER_LAMBDA * utilization
        bits_per_s = gbps * 1e9
        pj_per_s = bits_per_s * (self.e_per_bit_pj + E_PHOTONIC_LASER_OVERHEAD_PJ)
        watts = pj_per_s * 1e-12  # pJ = 1e-12 J
        # add fixed laser + ring tuning
        watts += self.n_waveguides * 0.15  # 150mW per waveguide laser
        return watts

    def compare_vs_copper(self, bits=1_000_000_000):
        e_ph = self.energy_for(bits)
        e_cu_pj = bits * E_ELEC_PJ_PER_BIT
        return {
            "photonic_pj": e_ph["pj"],
            "copper_pj": e_cu_pj,
            "saving_factor": e_cu_pj / e_ph["pj"] if e_ph["pj"] else 0,
            "photonic_W_at_70pct": self.power_at_BW(0.7),
            "copper_W_equiv": bits * E_ELEC_PJ_PER_BIT * 1e-12 * (self.bandwidth_GBps()*8e9 / bits) if bits else 0,
        }

class WDM_TDM_Arbiter:
    """Models wavelength + time-slot allocation.
    Guarantees deterministic grant time = slot.
    """
    def __init__(self, wdm=WDM_WAVELENGTHS, tdm=TDM_SLOTS):
        self.wdm = wdm
        self.tdm = tdm
        self.cycle = 0

    def allocate(self, req_id: int):
        """Hash req to (λ, slot) — deterministic, no contention beyond wait."""
        lam = req_id % self.wdm
        slot = (req_id // self.wdm) % self.tdm
        latency = BASE_LATENCY_NS + slot * TDM_SLOT_NS
        # wavelength reuse possible in parallel
        return {"lambda": lam, "slot": slot, "latency_ns": latency}

    def max_parallel_transfers(self, n_waveguides=8):
        return n_waveguides * self.wdm  # all wavelengths parallel

def demo():
    print("=== Photonic Interconnect Demo  gpu.md:6,16 ===")
    link = PhotonicLink(n_waveguides=8)
    print(f"BW: {link.bandwidth_GBps():.0f} GB/s ({link.n_waveguides}wg × {link.wdm}λ × {WAVEGUIDE_BW_GBPS_PER_LAMBDA}Gbps)")
    print(f"E/bit: photonic {link.e_per_bit_pj*1000:.0f} fJ vs Cu {E_ELEC_PJ_PER_BIT*1000:.0f} fJ")
    bits = 1_000_000_000  # 1 Gbit
    cmp = link.compare_vs_copper(bits)
    print(f"Energy for 1Gbit: photonic {cmp['photonic_pj']/1e6:.2f} mJ vs Cu {cmp['copper_pj']/1e6:.2f} mJ  (saving {cmp['saving_factor']:.1f}x)")
    print(f"Power at 70% BW: {link.power_at_BW(0.7):.1f}W")
    print("Latency determinism (TDM):")
    arb = WDM_TDM_Arbiter()
    for req in [0,1,7,8,15,31]:
        a = arb.allocate(req)
        print(f"  req {req:2d} -> λ={a['lambda']} slot={a['slot']} latency={a['latency_ns']}ns")

if __name__ == "__main__":
    demo()
