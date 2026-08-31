#!/usr/bin/env python3
"""
Lean fallback GDS for viewers — no deps, pure GDSII binary.
If OpenLane fails (PDK 504, 1.9GB VM), viewers still get a viewable *.gds.
Shows die outline and cell names so gds-viewer.tinytapeout.com / gdsjam.com both render.

Usage: python3 tapeout/generate_placeholder_gds.py [output.gds]
"""
import struct, time, pathlib, sys

def u16(v): return struct.pack('>H', v)
def i16(v): return struct.pack('>h', v)
def i32(v): return struct.pack('>i', v)
def rec(rectype, datatype, data=b''):
    l = 4 + len(data)
    return u16(l) + bytes([rectype, datatype]) + data

def ascii_rec(rectype, datatype, s):
    b = s.encode('ascii') + (b'\x00' if len(s)%2==1 else b'')
    return rec(rectype, datatype, b)

def time_rec(rectype):
    t = time.gmtime()
    vals = [t.tm_year, t.tm_mon, t.tm_mday, t.tm_hour, t.tm_min, t.tm_sec]*2
    return rec(rectype, 0x01, b''.join(i16(v) for v in vals))

def gds_placeholder(path: str, die_um=200, title="cache_4d_controller placeholder gpu_1.md:3"):
    # Units: 1 micron = 1000 db units (standard sky130)
    # Layers: 1=met1, 2=via, 30=text, per gdsjam expected
    scale = 1000
    w = die_um * scale
    h = die_um * scale
    out=[]
    out.append(rec(0x00,0x02, u16(0x0258))) # HEADER 600
    out.append(time_rec(0x01)) # BGNLIB
    out.append(time_rec(0x01)) # duplicate BGNLIB really last mod?
    # Actually BGNLIB + LIBNAME + UNITS
    out.append(ascii_rec(0x02,0x06, "GPU_CHIP"))
    out.append(rec(0x03,0x05, struct.pack('>ii', 1, 1000) + struct.pack('>ii', 1, 1000))) # UNITS: user 1e-6, meter 1e-9 (placeholder)
    # Use proper UNITS: double 1e-6 and 1e-9 encoded as 8-byte real? simplified use integers via datatype 5
    # Instead write correct 8-byte real units manually: fallback to standard 0x03 0x05 with two 8-byte reals
    # We'll overwrite above with true IEEE double GDS reals:
    def gds_real(x):
        # GDSII 8-byte real: 1bit sign, 7bit exponent (64 bias), 56bit mantissa base16
        import math
        if x==0: return b'\x00'*8
        sign = 0 if x>0 else 1
        x=abs(x)
        exp = int(math.floor(math.log(x,16)))+1
        mant = x / (16**exp)
        # mant in [1/16,1)
        mant_int = int(mant * (1<<56))
        # exponent bias 64
        exp_biased = exp + 64
        b0 = (sign<<7) | exp_biased
        return bytes([b0]) + mant_int.to_bytes(7,'big')
    out[-1]= rec(0x03,0x05, gds_real(0.001) + gds_real(1e-9))  # 1 um = 0.001 mm, db 1nm
    # BGNSTR
    out.append(time_rec(0x05))
    out.append(ascii_rec(0x06,0x06, title[:32]))
    # Die outline on layer 1 datatype 0 (BOUNDARY)
    out.append(rec(0x08,0x00)) # BOUNDARY
    out.append(rec(0x0D,0x02, i16(1))) # LAYER 1 (met1)
    out.append(rec(0x0E,0x02, i16(0))) # DATATYPE
    pts=[(0,0),(w,0),(w,h),(0,h),(0,0)]
    xy = b''.join(i32(x)+i32(y) for x,y in pts)
    out.append(rec(0x10,0x03, xy)) # XY
    out.append(rec(0x11,0x00)) # ENDEL
    # Inner core 80%
    out.append(rec(0x08,0x00))
    out.append(rec(0x0D,0x02, i16(2))) # layer 2
    out.append(rec(0x0E,0x02, i16(0)))
    m=int(w*0.1); M=int(w*0.9)
    pts2=[(m,m),(M,m),(M,M),(m,M),(m,m)]
    out.append(rec(0x10,0x03, b''.join(i32(x)+i32(y) for x,y in pts2)))
    out.append(rec(0x11,0x00))
    # Text labels: cache4d + wdm
    for txt, x, y in [("cache_4d 42cells", w//2, h//2), ("sky130A Si-proxy", w//2, h//2 - 20*scale), ("gpu.md:7 4D", w//2, h//2 + 20*scale)]:
        out.append(rec(0x0C,0x00)) # TEXTELEM
        out.append(rec(0x0D,0x02, i16(30))) # layer 30 text
        out.append(rec(0x16,0x02, i16(0))) # TEXTTYPE
        out.append(rec(0x17,0x02, i16(0x0000))) # PRESENTATION
        out.append(rec(0x10,0x03, i32(x)+i32(y))) # XY
        out.append(ascii_rec(0x19,0x06, txt)) # STRING
        out.append(rec(0x11,0x00))
    out.append(rec(0x07,0x00)) # ENDSTR
    out.append(rec(0x04,0x00)) # ENDLIB
    pathlib.Path(path).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(path).write_bytes(b''.join(out))
    print(f"Wrote placeholder GDS {path} die {die_um}um ({w}x{h} dbu) {title}")

if __name__=="__main__":
    gds_placeholder(sys.argv[1] if len(sys.argv)>1 else "tapeout/gds/cache_4d_controller.placeholder.gds")
    # also wdm placeholder if requested
    if len(sys.argv)>2:
        gds_placeholder(sys.argv[2], die_um=120, title="wdm_tdm_arbiter placeholder gpu.md:6")
    else:
        # auto second file for wdm if first was cache
        try:
            gds_placeholder("tapeout/gds/wdm_tdm_arbiter.placeholder.gds", die_um=120, title="wdm_tdm_arbiter placeholder gpu.md:6")
        except: pass
