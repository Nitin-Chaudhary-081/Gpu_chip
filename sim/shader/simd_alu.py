"""
Python golden for simd_alu.sv — numpy float32 exact int path + INT8
gpu_A.md:94 ADD/MUL/MAX 8-lane FP32 + INT8
"""
import struct
import numpy as np

LANES = 8

def f32_to_bits(f):
    return struct.unpack('>I', struct.pack('>f', np.float32(f)))[0]

def bits_to_f32(b):
    return struct.unpack('>f', struct.pack('>I', int(b) & 0xFFFFFFFF))[0]

def int8_to_bits(i):
    return int(i) & 0xFF

def bits_to_int8(b):
    val = int(b) & 0xFF
    return val if val < 128 else val - 256

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
    if np.isnan(a):
        return b_bits
    if np.isnan(b):
        return a_bits
    m = a if a > b else b
    if m == 0.0:
        if a_bits == 0 or b_bits == 0:
            return 0
    return f32_to_bits(np.float32(m))

def int8_add(a_bits, b_bits):
    a = bits_to_int8(a_bits)
    b = bits_to_int8(b_bits)
    sum_val = a + b
    if sum_val > 127: sum_val = 127
    elif sum_val < -128: sum_val = -128
    return int8_to_bits(sum_val)

def int8_mul(a_bits, b_bits):
    a = bits_to_int8(a_bits)
    b = bits_to_int8(b_bits)
    prod = a * b
    if prod > 127: prod = 127
    elif prod < -128: prod = -128
    return int8_to_bits(prod)

def int8_max(a_bits, b_bits):
    a = bits_to_int8(a_bits)
    b = bits_to_int8(b_bits)
    return int8_to_bits(a if a > b else b)

def simd_alu_golden(a_vec, b_vec, op, is_fp32=True):
    """
    a_vec, b_vec: list of 8 float32 values or bits
    op: 0 INT8_ADD 1 INT8_MUL 2 INT8_MAX 3 FP32_ADD 4 FP32_MUL 5 FP32_MAX
    is_fp32: True for FP32 ops, False for INT8 ops
    returns list of 8 bits (32-bit results)
    """
    res = []
    for av, bv in zip(a_vec, b_vec):
        if isinstance(av, float) or isinstance(av, np.floating):
            av = f32_to_bits(av)
        if isinstance(bv, float) or isinstance(bv, np.floating):
            bv = f32_to_bits(bv)
        if not is_fp32:
            # INT8 ops use lower 8 bits
            a8 = av & 0xFF
            b8 = bv & 0xFF
            if op == 0:
                rv = int8_add(a8, b8)
            elif op == 1:
                rv = int8_mul(a8, b8)
            elif op == 2:
                rv = int8_max(a8, b8)
            else:
                rv = a8
            # sign extend to 32 bits
            rv = rv if rv < 128 else rv - 256
            rv = rv & 0xFFFFFFFF
        else:
            if op == 3:
                rv = fp32_add(av, bv)
            elif op == 4:
                rv = fp32_mul(av, bv)
            elif op == 5:
                rv = fp32_max(av, bv)
            else:
                rv = av
        res.append(rv & 0xFFFFFFFF)
    return res

def demo():
    # simple check
    a = [1.0, 2.0, 3.5, -1.0, 0.0, 5.0, 1.0, -2.0]
    b = [2.0, 3.0, 1.5, 1.0, 0.0, 5.0, -1.0, 2.0]
    print("FP32 ADD", simd_alu_golden(a,b,3,True))
    print("FP32 MUL", simd_alu_golden(a,b,4,True))
    print("FP32 MAX", simd_alu_golden(a,b,5,True))
    # INT8
    a_int8 = [1, 2, 3, -1, 0, 5, 1, -2]
    b_int8 = [2, 3, 1, 1, 0, 5, -1, 2]
    print("INT8 ADD", simd_alu_golden(a_int8,b_int8,0,False))
    print("INT8 MUL", simd_alu_golden(a_int8,b_int8,1,False))
    print("INT8 MAX", simd_alu_golden(a_int8,b_int8,2,False))

if __name__ == "__main__":
    demo()