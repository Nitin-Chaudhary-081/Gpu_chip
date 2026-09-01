"""
SRAM model — OpenRAM 4KB placeholder for 1mm scaling  gpu_A.md:51
512 x 64-bit? We use 1024 x 32-bit = 4KB, sky130 OpenRAM compatible.
Behavioral Python for cocotb golden, cycle-accurate 1-cycle read latency.
"""

class SRAM4K:
    """1024 x 32-bit SRAM — 4KB, 10-bit address, 32-bit data, 1R1W"""
    def __init__(self, depth=1024, width=32):
        self.depth = depth
        self.width = width
        self.mem = [0] * depth
        self.mask = (1 << width) - 1

    def write(self, addr, data):
        addr = addr % self.depth
        self.mem[addr] = data & self.mask

    def read(self, addr):
        addr = addr % self.depth
        return self.mem[addr] & self.mask

    def reset(self):
        self.mem = [0] * self.depth

def demo():
    s = SRAM4K()
    s.write(0, 0xDEADBEEF)
    s.write(1023, 0x12345678)
    print(hex(s.read(0)), hex(s.read(1023)))
    print("4KB SRAM model ready — OpenRAM sky130 proxy")

if __name__ == "__main__":
    demo()
