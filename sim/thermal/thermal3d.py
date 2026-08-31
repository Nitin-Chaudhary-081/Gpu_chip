"""
M3D Thermal model — gpu.md:10,15
- 4 active tiers stacked vertically trap heat
- Low-Temp ALD <400C budget, microfluidic cooling channels etched in substrate
Finite-difference 3D grid, explicit steady-state solver
"""
import numpy as np

# Material / geometry (approx, scaled to chip)
K_SI = 148.0      # W/mK
K_OXIDE = 1.4     # W/mK (inter-layer dielectric)
T_AMBIENT = 25.0  # C
T_ALD_LIMIT = 400.0  # C gpu.md:15 upper-layer budget
GRID_X, GRID_Y = 16, 16  # per tier lateral cells
N_TIERS = 4       # M3D layers gpu.md:6
CELL_SIZE_UM = 625  # 10mm chip /16 = 625um per cell
TIER_THICK_UM = 10  # per tier

# Power densities (W per cell) — tuned so naive stack overheats
P_PER_CELL_W = 0.8  # high perf tile

class M3DStack:
    def __init__(self, grid_x=GRID_X, grid_y=GRID_Y, n_tiers=N_TIERS,
                 p_per_cell=P_PER_CELL_W, has_microfluidics=False,
                 coolant_temp=25.0, h_conv=5000.0):
        self.gx, self.gy, self.nz = grid_x, grid_y, n_tiers
        self.p = p_per_cell
        self.has_microfluidics = has_microfluidics
        self.coolant_temp = coolant_temp
        self.h_conv = h_conv  # W/m2K convective coeff for microfluidics
        # Temperature grid [z,y,x]
        self.T = np.full((n_tiers, grid_y, grid_x), T_AMBIENT, dtype=float)
        # Thermal resistance vertical (oxide between tiers) — higher = traps heat
        self.R_vert = 2.5  # K/W per cell vertical (tuned)
        self.R_lat = 0.8   # K/W lateral
        self.R_ambient = 1.2  # top/bottom to ambient

    def step(self, iterations=200):
        """Jacobi-like steady-state solve. Simple but shows trapping vs cooling."""
        for _ in range(iterations):
            new_T = self.T.copy()
            for z in range(self.nz):
                for y in range(self.gy):
                    for x in range(self.gx):
                        # Power injection
                        p = self.p
                        # Microfluidic cooling: bottom tier (z=0) is etched channels gpu.md:15
                        # model as strong heat sink to coolant_temp
                        if self.has_microfluidics and z == 0:
                            # convective sink: Q = h*A*(T - Tcool)
                            # discretize as T pulled toward coolant
                            sink = 0.65  # coupling strength
                            # neighbors + sink
                            neigh = []
                            for dz, dy, dx in [(1,0,0), (0,1,0),(0,-1,0),(1,0,0),(0,0,1),(0,0,-1)]:
                                nz, ny, nx = z+dz, y+dy, x+dx
                                if 0 <= nz < self.nz and 0 <= ny < self.gy and 0 <= nx < self.gx:
                                    neigh.append(self.T[nz, ny, nx])
                                else:
                                    neigh.append(T_AMBIENT if z == self.nz-1 else self.T[z,y,x])
                            avg = sum(neigh)/len(neigh) if neigh else self.T[z,y,x]
                            new_T[z,y,x] = (1-sink)* (avg + p*self.R_vert*0.5) + sink*self.coolant_temp
                        else:
                            neigh = []
                            if z+1 < self.nz: neigh.append(self.T[z+1,y,x])
                            else: neigh.append(T_AMBIENT)  # top to heatsink
                            if z-1 >= 0: neigh.append(self.T[z-1,y,x])
                            if y+1 < self.gy: neigh.append(self.T[z,y+1,x])
                            if y-1 >= 0: neigh.append(self.T[z,y-1,x])
                            if x+1 < self.gx: neigh.append(self.T[z,y,x+1])
                            if x-1 >= 0: neigh.append(self.T[z,y,x-1])
                            # also ambient at bounds
                            if not neigh:
                                avg = T_AMBIENT
                            else:
                                avg = sum(neigh)/len(neigh)
                            # vertical resistance stronger than lateral -> trapping
                            new_T[z,y,x] = avg + p * (self.R_vert if z < self.nz-1 else self.R_ambient) * 0.35
                            # add hotspot factor for inner tiers
                            if 0 < z < self.nz-1:
                                new_T[z,y,x] += 4.0  # trapping offset
            # clamp
            self.T = np.clip(new_T, T_AMBIENT, 500)
        return self.T

    def metrics(self):
        return {
            "t_max": float(np.max(self.T)),
            "t_avg": float(np.mean(self.T)),
            "t_per_tier": [float(np.mean(self.T[z])) for z in range(self.nz)],
            "t_center": float(self.T[self.nz//2, self.gy//2, self.gx//2]),
            "hotspot": float(np.max(self.T)),
            "ald_violation": bool(np.any(self.T > T_ALD_LIMIT)),
        }

def compare_stacks(p_per_cell=P_PER_CELL_W):
    """Run with vs without microfluidics, return delta."""
    s_no = M3DStack(p_per_cell=p_per_cell, has_microfluidics=False)
    s_no.step(300)
    m_no = s_no.metrics()
    s_yes = M3DStack(p_per_cell=p_per_cell, has_microfluidics=True)
    s_yes.step(300)
    m_yes = s_yes.metrics()
    return {"without": m_no, "with": m_yes, "delta_tmax": m_no["t_max"] - m_yes["t_max"]}

def demo():
    print("=== M3D Thermal Trap Demo  gpu.md:10,15 ===")
    print(f"Tiers={N_TIERS}, P/cell={P_PER_CELL_W}W, Ambient {T_AMBIENT}C, ALD limit {T_ALD_LIMIT}C")
    cmp = compare_stacks()
    print(f"Without microfluidics: Tmax={cmp['without']['t_max']:.1f}C avg={cmp['without']['t_avg']:.1f}C per-tier={[f'{v:.1f}' for v in cmp['without']['t_per_tier']]}")
    print(f"With microfluidics   : Tmax={cmp['with']['t_max']:.1f}C avg={cmp['with']['t_avg']:.1f}C per-tier={[f'{v:.1f}' for v in cmp['with']['t_per_tier']]}")
    print(f"Delta Tmax = {cmp['delta_tmax']:.1f}C  (cooling benefit)")
    print(f"ALD violation without: {cmp['without']['ald_violation']}, with: {cmp['with']['ald_violation']}")
    # also show scaling
    for p in [0.4, 0.8, 1.2]:
        c = compare_stacks(p_per_cell=p)
        print(f" P={p}W/cell -> Tmax no-cool {c['without']['t_max']:.0f}C vs cool {c['with']['t_max']:.0f}C")

if __name__ == "__main__":
    demo()
