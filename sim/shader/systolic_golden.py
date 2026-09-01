"""Golden for systolic_4x4 — numpy int8 GEMM"""
import numpy as np

SIZE=4
def systolic_4x4_golden(A, B):
    """
    A, B: 4x4 numpy int8 arrays or flat lists length 16
    Returns 4x4 int32 result C = A @ B
    """
    if isinstance(A, list) or isinstance(A, tuple):
        A = np.array(A, dtype=np.int8).reshape(4,4)
    if isinstance(B, list) or isinstance(B, tuple):
        B = np.array(B, dtype=np.int8).reshape(4,4)
    A = np.array(A, dtype=np.int8).reshape(4,4)
    B = np.array(B, dtype=np.int8).reshape(4,4)
    C = A.astype(np.int32) @ B.astype(np.int32)
    return C.astype(np.int32)

def pack_a_b(A,B):
    # pack to flat ints for RTL: row-major byte pack
    # Returns ints for a_flat, b_flat as 128-bit (16*8)
    # We represent as Python int for packing helper
    A = np.array(A, dtype=np.int8).reshape(16)
    B = np.array(B, dtype=np.int8).reshape(16)
    # pack into 128-bit int little-endian lane0 LSB
    a_flat = 0
    b_flat = 0
    for i, (av,bv) in enumerate(zip(A,B)):
        a_flat |= (int(av) & 0xFF) << (i*8)
        b_flat |= (int(bv) & 0xFF) << (i*8)
    return a_flat, b_flat

def unpack_c(c_flat):
    # c_flat 512-bit (16*32) int -> 4x4 int32
    vals=[]
    for i in range(16):
        v = (c_flat >> (i*32)) & 0xFFFFFFFF
        # sign extend 32
        if v & 0x80000000:
            v -= 0x100000000
        vals.append(v)
    return np.array(vals, dtype=np.int32).reshape(4,4)

def demo():
    A = np.array([[1,2,3,4],[5,6,7,8],[9,10,11,12],[13,14,15,16]], dtype=np.int8)
    B = np.eye(4, dtype=np.int8)*2
    print(systolic_4x4_golden(A,B))

if __name__=="__main__":
    demo()
