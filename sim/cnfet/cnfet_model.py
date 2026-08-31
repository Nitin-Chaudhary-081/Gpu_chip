"""
CNFET model — gpu.md:5,9,14
- Near-ballistic transport, Vdd/2, 3x Idrive
- Chirality trap: CVD gives ~33% metallic  -> ruins yield
- Mitigation: DGU sorting + electrical burn-away pulses
Power model ties to <120W gpu.md:3
"""
import numpy as np
import random

# --- Physics constants (literature/Stanford model approx) ---
VDD_SI = 0.9          # V, 7nm Si baseline
VDD_CNFET = 0.45      # V, half per gpu.md:5
IDRIVE_FACTOR = 3.0   # 3x per gpu.md:5
P_METAL_RAW = 0.33    # gpu.md:9
P_METAL_DGU = 0.01    # after Density-Gradient Ultracentrifugation gpu.md:14
P_METAL_BURN_RESIDUAL = 0.001  # after burn-away pulse gpu.md:14
BURN_SUCCESS_RATE = 0.99  # 99% of metallic tubes vaporized per pulse
BURN_DAMAGE_RATE = 0.002  # 0.2% collateral semiconducting damage

class CNFETArray:
    """Models a tile of CNFETs with CNT chirality defects."""

    def __init__(self, n_transistors=10000, tubes_per_device=8, seed=0):
        self.n = n_transistors
        self.tubes_per_device = tubes_per_device
        self.rng = np.random.default_rng(seed)
        # Each tube: True = metallic (defect), False = semiconducting (good)
        self.tubes = self.rng.random((n_transistors, tubes_per_device)) < P_METAL_RAW
        self.vdd = VDD_CNFET
        self.built_in_defects = int(np.sum(self.tubes))

    def raw_yield(self):
        """Device fails if ANY metallic tube present (short)."""
        failed = np.any(self.tubes, axis=1).sum()
        return 1.0 - failed / self.n

    def apply_dgu(self):
        """Density-Gradient Ultracentrifugation: resample with lower p_metal.
        Models separation step before integration."""
        # Keep semiconducting tubes with high prob, re-draw metallic region
        metallic = self.tubes
        # For each tube, if it was metallic, with prob 0.97 it gets removed/replaced
        # Simplified: redraw all tubes with p = P_METAL_DGU
        self.tubes = self.rng.random((self.n, self.tubes_per_device)) < P_METAL_DGU
        return self

    def apply_burn_away(self, pulses=1):
        """Electrical burn-away: high current vaporizes metallic CNTs like fuses.
        gpu.md:14 'targeted electrical burn-away pulses'"""
        for _ in range(pulses):
            for i in range(self.n):
                for j in range(self.tubes_per_device):
                    if self.tubes[i, j]:  # metallic
                        if self.rng.random() < BURN_SUCCESS_RATE:
                            self.tubes[i, j] = False  # vaporized -> open (removed)
                            # left as 0 tubes -> device has fewer tubes, still functional
                    else:
                        # small chance of damaging good tube
                        if self.rng.random() < BURN_DAMAGE_RATE:
                            # tube lost but not a short -> device degrades but not fails
                            pass
            # after pulse, remove zero-tube? Actually empty is not short, just lower drive
            # metallic tubes removed means device becomes good if no metallic left
        return self

    def effective_yield(self):
        failed = np.any(self.tubes, axis=1).sum()
        return 1.0 - failed / self.n

    def drive_stats(self):
        """Average tubes per device that remain conducting."""
        # metallic tubes that remain cause failure, so exclude failed devices
        good_mask = ~np.any(self.tubes, axis=1)  # wait, after burn metallic removed so good_mask is all good?
        # Actually after burn, tubes==True means still metallic (short). So good = no True.
        good_devices = np.sum(~np.any(self.tubes, axis=1))
        # Count remaining semiconducting tubes per good device (~tubes_per_device minus damage)
        # Simplified: each device has tubes_per_device tubes nominally, all semiconducting now
        avg_tubes = self.tubes_per_device * 0.998  # account damage
        return {
            "good_devices": int(good_devices),
            "yield": float(good_devices / self.n),
            "avg_tubes_per_good": float(avg_tubes),
            "idrives_mA_per_um": float(avg_tubes * 15 * IDRIVE_FACTOR / 8),  # Si ~15uA/tube equiv
        }

    def power_saving_vs_si(self, activity=0.3, cap_f_per_device=0.5e-15, freq_hz=1.5e9):
        """P = C*V^2*f*activity. Compare Si vs CNFET.
        Returns dict with p_si, p_cnfet, saving_factor
        """
        # total cap - cap_f_per_device is in Farads already
        c_total = cap_f_per_device * self.n
        p_si = c_total * (VDD_SI ** 2) * freq_hz * activity
        p_cnfet = c_total * (VDD_CNFET ** 2) * freq_hz * activity * 0.6  # 0.6 for lower parasitics
        return {
            "p_si_W": float(p_si),
            "p_cnfet_W": float(p_cnfet),
            "saving_factor": float(p_si / p_cnfet if p_cnfet else 0),
            "vdd_si": VDD_SI,
            "vdd_cnfet": VDD_CNFET,
        }


def simulate_yield_sweep(n=20000, tubes=8):
    """Returns dict for plotting yield vs steps."""
    arr = CNFETArray(n_transistors=n, tubes_per_device=tubes, seed=42)
    y_raw = arr.raw_yield()
    arr.apply_dgu()
    y_dgu = arr.effective_yield()
    arr.apply_burn_away(pulses=2)
    y_burn = arr.effective_yield()
    return {"raw": y_raw, "dgu": y_dgu, "burn": y_burn}

def demo():
    print("=== CNFET Chirality Trap Demo  gpu.md:9,14 ===")
    for tubes in [1, 4, 8]:
        arr = CNFETArray(n_transistors=20000, tubes_per_device=tubes, seed=1)
        y_raw = arr.raw_yield()
        arr.apply_dgu()
        y_dgu = arr.effective_yield()
        arr.apply_burn_away(pulses=2)
        y_burn = arr.effective_yield()
        print(f"tubes/device={tubes}: raw yield {y_raw*100:.1f}% -> DGU {y_dgu*100:.2f}% -> burn {y_burn*100:.3f}%")
    arr = CNFETArray(n_transistors=50000, tubes_per_device=8, seed=0)
    print("\nPower saving (50k devices, 1.5GHz):", arr.power_saving_vs_si())
    print(f"Vdd Si {VDD_SI}V -> CNFET {VDD_CNFET}V, Idrive {IDRIVE_FACTOR}x")

if __name__ == "__main__":
    demo()
