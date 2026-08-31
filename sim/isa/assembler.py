"""
Assembler + Simulator for domain ISA — gpu.md:17
Parses asm, simulates on Cache4D + simple ALU.
"""
import re
import numpy as np
from dataclasses import dataclass
from typing import List, Dict, Tuple
from sim.cache4d.cache4d import Cache4D, Coord4D

OPCODES = {
    "TENSOR_LOAD.4D": 0x01,
    "TENSOR_STORE.4D": 0x02,
    "MATMUL_TILE": 0x03,
    "CONV_TILE": 0x04,
    "VEC_ADD": 0x05,
    "VEC_MUL": 0x06,
    "WDM_XFER": 0x07,
    "TDM_WAIT": 0x08,
    "CACHE_MAP": 0x09,
    "BARRIER": 0x0A,
    "HALT": 0xFF,
}

@dataclass
class Instr:
    op: str
    args: List[str]
    raw: str

def parse_asm(src: str) -> List[Instr]:
    prog = []
    for line in src.strip().splitlines():
        line = line.split(";")[0].strip().split("#")[0].strip()  # comments ; or #
        # keep #tile syntax -> strip after #
        # Actually tile param: handle , #8
        line = line.replace(",", " ").strip()
        if not line:
            continue
        # Re-tokenize: split but keep (x,y,z,t)
        # Simplify: op is first token, rest args split by space/comma/parens
        parts = line.split()
        op = parts[0].upper()
        # Normalize op: allow TENSOR_LOAD etc.
        # Map cleaned op
        if op not in OPCODES:
            # try to match with dot
            for k in OPCODES:
                if k.replace(".","") == op.replace(".",""):
                    op = k
                    break
        args = parts[1:]
        # Special handling: coords like (0 0 0 0) come as tokens "(0" "0" "0" "0)" -> merge
        merged = []
        buf = ""
        for a in args:
            if "(" in a and ")" not in a:
                buf = a
            elif buf:
                buf += " " + a
                if ")" in a:
                    merged.append(buf)
                    buf = ""
            else:
                merged.append(a)
        if buf:
            merged.append(buf)
        # Remove empty
        merged = [m.strip() for m in merged if m.strip()]
        prog.append(Instr(op=op, args=merged, raw=line))
    return prog

def parse_coord(s: str) -> Coord4D:
    m = re.search(r"\(\s*(-?\d+)\s+(-?\d+)\s+(-?\d+)\s+(-?\d+)\s*\)", s)
    if not m:
        m = re.search(r"\(\s*(-?\d+)\s*,\s*(-?\d+)\s*,\s*(-?\d+)\s*,\s*(-?\d+)\s*\)", s)
    if not m:
        raise ValueError(f"bad coord {s}")
    return Coord4D(int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4)))

class ISASimulator:
    def __init__(self, cache: Cache4D = None):
        self.cache = cache or Cache4D()
        self.tregs: Dict[str, np.ndarray] = {f"T{i}": np.zeros((8,8)) for i in range(8)}
        self.aregs: Dict[str, Coord4D] = {}
        self.pc = 0
        self.cycles = 0
        self.trace: List[str] = []

    def _reg(self, name: str) -> str:
        return name.upper().strip().replace(",","")

    def run(self, prog: List[Instr], verbose=False):
        self.pc = 0
        self.cycles = 0
        self.trace.clear()
        while self.pc < len(prog):
            ins = prog[self.pc]
            if verbose:
                print(f"[{self.pc:02d}] {ins.raw}  args={ins.args}")
            if ins.op == "HALT":
                self.trace.append(f"HALT cycles={self.cycles}")
                break
            elif ins.op == "TENSOR_LOAD.4D":
                # args: Tdst, (x,y,z,t), #tile?
                dst = self._reg(ins.args[0])
                coord = parse_coord(ins.args[1])
                # tile size default 8
                res = self.cache.load(coord)
                self.cycles += res["cycles"]
                if res["data"] is not None:
                    self.tregs[dst] = res["data"].copy()
                    self.trace.append(f"LOAD {dst} {coord} hit bank={res['bank']} cycles={res['cycles']}")
                else:
                    # miss: zero tile (cold)
                    self.tregs[dst] = np.zeros((8,8))
                    self.trace.append(f"LOAD {dst} {coord} MISS cycles={res['cycles']}")
            elif ins.op == "TENSOR_STORE.4D":
                src = self._reg(ins.args[0])
                coord = parse_coord(ins.args[1])
                res = self.cache.store(coord, self.tregs[src])
                self.cycles += res["cycles"]
                self.trace.append(f"STORE {src} -> {coord} bank={res['bank']} cycles={res['cycles']}")
            elif ins.op == "MATMUL_TILE":
                dst, a, b = [self._reg(x) for x in ins.args[:3]]
                # Tdst += TsrcA @ TsrcB  (accumulate)
                self.tregs[dst] = self.tregs[dst] + self.tregs[a] @ self.tregs[b]
                self.cycles += 8
                self.trace.append(f"MATMUL {dst} += {a}@{b} cycles=8")
            elif ins.op == "VEC_ADD":
                dst, a, b = [self._reg(x) for x in ins.args[:3]]
                self.tregs[dst] = self.tregs[a] + self.tregs[b]
                self.cycles += 4
            elif ins.op == "VEC_MUL":
                dst, a, b = [self._reg(x) for x in ins.args[:3]]
                self.tregs[dst] = self.tregs[a] * self.tregs[b]
                self.cycles += 4
            elif ins.op == "WDM_XFER":
                # move register logically (photonic)
                dst, src = self._reg(ins.args[0]), self._reg(ins.args[1])
                lam = int(ins.args[2].replace("#","").replace("λ","")) if len(ins.args)>2 else 0
                self.tregs[dst] = self.tregs[src].copy()
                self.cycles += 2  # fJ/bit latency ~2
                self.trace.append(f"WDM_XFER {src}->{dst} λ={lam}")
            elif ins.op == "TDM_WAIT":
                slot = int(ins.args[0].replace("#","")) if ins.args else 1
                self.cycles += slot * 2
                self.trace.append(f"TDM_WAIT slot={slot}")
            elif ins.op == "CACHE_MAP":
                dst = self._reg(ins.args[0])
                coord = parse_coord(ins.args[1])
                self.aregs[dst] = coord
                loc = self.cache.physical_location(coord)
                self.cycles += 1
                self.trace.append(f"CACHE_MAP {dst}={coord} -> {loc}")
            elif ins.op == "BARRIER":
                self.cycles += 2
            elif ins.op == "CONV_TILE":
                dst, a, b = [self._reg(x) for x in ins.args[:3]]
                # simplified: elementwise conv as matmul placeholder
                self.tregs[dst] = self.tregs[dst] + self.tregs[a] * 0.5
                self.cycles += 12
            else:
                self.trace.append(f"UNKNOWN {ins.op}")
                self.cycles += 1
            self.pc += 1
        return {"cycles": self.cycles, "trace": list(self.trace), "tregs": {k: v.copy() for k,v in self.tregs.items()}}

def demo():
    print("=== ISA Simulator Demo gpu.md:17 ===")
    cache = Cache4D()
    # preload two tiles
    cache.store(Coord4D(0,0,0,0), np.eye(8))
    cache.store(Coord4D(1,1,1,1), np.ones((8,8))*2)
    asm = """
    CACHE_MAP A0, (0,0,0,0)
    TENSOR_LOAD.4D T0, (0,0,0,0)
    TENSOR_LOAD.4D T1, (1,1,1,1)
    MATMUL_TILE T2, T0, T1
    WDM_XFER T3, T2, #2
    TDM_WAIT #1
    TENSOR_STORE.4D T3, (2,2,2,2)
    HALT
    """
    prog = parse_asm(asm)
    sim = ISASimulator(cache)
    res = sim.run(prog, verbose=True)
    print(f"Cycles: {res['cycles']}")
    print("T2 result (should be 2*I):\n", res['tregs']['T2'][:3,:3])

if __name__ == "__main__":
    demo()
