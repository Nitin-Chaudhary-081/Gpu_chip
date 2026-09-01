"""
Python golden for simd_alu.sv — numpy float32 exact int path
gpu_A.md:94 ADD/MUL/MAX 8-lane
"""
import struct
import numpy as np

LANES = 8

def f32_to_bits(f):
    return struct.unpack('>I', struct.pack('>f', np.float32(f)))[0]

def bits_to_f32(b):
    return struct.unpack('>f', struct.pack('>I', int(b) & 0xFFFFFFFF))[0]

def fp32_add(a_bits, b_bits):
    a = bits_to_f32(a_bits)
    b = bits_to_f32(b_bits)
    return f32_to_bits(np.float32(a + b))

def fp32_mul(a_bits, b_bits):
    a = bits_to_f32(a_bits)
    b = bits_to_f32(b_bits)
    return f32_to_bits(np.float32(a * b))

def fp32_max(a_bits, b_bits):
    a = bits_to_f32(a_bits)
    b = bits_to_f32(b_bits)
    # numpy max handles -0 etc; use Python max for float
    # If NaN, return the other (match RTL)
    if np.isnan(a):
        return b_bits
    if np.isnan(b):
        return a_bits
    m = a if a > b else b
    # For -0 vs +0, Python -0.0 == 0.0, need to prefer +0 if either is +0?
    # We'll return +0 if max is zero and either is +0
    if m == 0.0:
        # check sign bits: +0 is 0x00000000, -0 is 0x80000000
        # if either input is +0, return +0
        if a_bits == 0 or b_bits == 0:
            return 0
    return f32_to_bits(np.float32(m))

def simd_alu_golden(a_vec, b_vec, op):
    """
    a_vec, b_vec: list of 8 float32 values or bits
    op: 0 ADD 1 MUL 2 MAX
    returns list of 8 bits
    """
    res = []
    for av, bv in zip(a_vec, b_vec):
        # accept either float or bits; if float convert
        if isinstance(av, float) or isinstance(av, np.floating):
            av = f32_to_bits(av)
        if isinstance(bv, float) or isinstance(bv, np.floating):
            bv = f32_to_bits(bv)
        if op == 0:
            rv = fp32_add(av, bv)
        elif op == 1:
            rv = fp32_mul(av, bv)
        elif op == 2:
            rv = fp32_max(av, bv)
        else:
            rv = av
        res.append(rv & 0xFFFFFFFF)
    return res

def demo():
    # simple check
    a = [1.0, 2.0, 3.5, -1.0, 0.0, 5.0, 1.0, -2.0]
    b = [2.0, 3.0, 1.5, 1.0, 0.0, 5.0, -1.0, 2.0]
    print("ADD", simd_alu_golden(a,b,0))
    print("MUL", simd_alu_golden(a,b,1))
    print("MAX", simd_alu_golden(a,b,2))

if __name__ == "__main__":
    demo()
