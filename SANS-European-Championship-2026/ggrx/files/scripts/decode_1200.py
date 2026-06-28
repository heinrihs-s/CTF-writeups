"""Try 1200 baud (run of 833 us = 1 symbol at 1200 baud)."""
import os
import numpy as np
from scipy import signal

RAW = r"C:\Users\Administrator\Documents\claude\sans\challenges\ggrx\artifacts\gqrx_20250207_112408_405000000_2000000_fc.raw"
SAMP_RATE = 2_000_000
SYMBOL_RATE = 1200
SPS = SAMP_RATE / SYMBOL_RATE  # 1666.67

raw = np.memmap(RAW, dtype=np.float32, mode="r")
iq = raw.view(np.complex64)

def fm_demod(x):
    phase = np.unwrap(np.angle(x))
    return np.diff(phase) / (2*np.pi) * SAMP_RATE

def decode_burst(start_s, end_s, name):
    s = int(start_s * SAMP_RATE)
    e = int(end_s * SAMP_RATE)
    sig = iq[s:e].copy()
    inst_freq = fm_demod(sig)
    b, a = signal.butter(4, SYMBOL_RATE*2/(SAMP_RATE/2), btype="low")
    lp = signal.filtfilt(b, a, inst_freq)

    # Active region
    power = np.abs(sig)**2
    win = 200
    smoothed = np.convolve(power, np.ones(win)/win, mode="same")
    pthresh = smoothed.max() * 0.5
    on = np.where(smoothed > pthresh)[0]
    start_idx = on[0]
    end_idx = on[-1]
    print(f"\n{name}: active samples {start_idx}..{end_idx} ({(end_idx-start_idx)/SAMP_RATE*1000:.1f}ms)")

    # Find first transition after start_idx
    sign = np.sign(lp[start_idx:])
    cross = np.where(np.diff(sign) != 0)[0]
    if cross.size:
        first_cross = start_idx + cross[0]
        print(f"first transition at: {first_cross} (={(first_cross-start_idx)/SAMP_RATE*1e6:.0f} us into burst)")

    # Search best timing offset across 0..SPS
    n_sym = int((end_idx - start_idx) / SPS) - 2
    sps = SPS
    best_score = -1
    best_off = 0
    for off in np.arange(0, sps, 20):
        s0 = start_idx + off
        score = 0
        for k in range(min(300, n_sym)):
            lo = int(s0 + k*sps + sps*0.3)
            hi = int(s0 + k*sps + sps*0.7)
            if hi >= lp.size:
                break
            m = lp[lo:hi].mean()
            sd = lp[lo:hi].std() + 1e-9
            score += abs(m) / sd
        if score > best_score:
            best_score = score
            best_off = int(off)
    print(f"best timing offset: {best_off} (score {best_score:.1f})")

    # Decode
    bits = []
    s0 = start_idx + best_off
    for k in range(n_sym):
        lo = int(s0 + k*sps + sps*0.3)
        hi = int(s0 + k*sps + sps*0.7)
        if hi >= lp.size:
            break
        m = lp[lo:hi].mean()
        bits.append(1 if m > 0 else 0)
    bits = "".join(str(b) for b in bits)
    print(f"bits len {len(bits)}")
    print(f"first 256: {bits[:256]}")
    return bits

b1 = decode_burst(1.00, 1.35, "burst1")
b2 = decode_burst(4.20, 4.55, "burst2")
print(f"\nb1 == b2? {b1==b2}")
print(f"b1 len {len(b1)} b2 len {len(b2)}")
if len(b1) == len(b2):
    diff = sum(1 for a,b in zip(b1,b2) if a!=b)
    print(f"diff bits {diff}")

# POCSAG sync search
POCSAG_SYNC = 0x7CD215D8
sync_bits = bin(POCSAG_SYNC)[2:].zfill(32)
inv_sync_bits = "".join("1" if c=="0" else "0" for c in sync_bits)
for src_name, src in [("b1", b1), ("b2", b2)]:
    for inv in [False, True]:
        b = "".join("1" if c=="0" else "0" for c in src) if inv else src
        for pat_name, pat in [("SYNC", sync_bits), ("INVSYNC", inv_sync_bits)]:
            locs = []
            i = 0
            while True:
                idx = b.find(pat, i)
                if idx < 0:
                    break
                locs.append(idx)
                i = idx + 1
            if locs:
                print(f"  {src_name} inv={inv} {pat_name} at {locs[:5]}")

# Try ASCII
print("\n--- ASCII attempts ---")
for src_name, src in [("b1", b1), ("b2", b2)]:
    for inv in [False, True]:
        b = "".join("1" if c=="0" else "0" for c in src) if inv else src
        for off in range(8):
            bs2 = b[off:]
            bs2 = bs2[:(len(bs2)//8)*8]
            data = bytes(int(bs2[i:i+8], 2) for i in range(0, len(bs2), 8))
            printable = sum(1 for c in data if 32<=c<127)
            if printable/max(1,len(data)) > 0.6:
                text = data.decode("latin-1")
                print(f"  {src_name} inv={inv} off={off}: {text[:120]!r}")
        # LSB
        for off in range(8):
            bs2 = b[off:]
            bs2 = bs2[:(len(bs2)//8)*8]
            data = bytes(int(bs2[i:i+8][::-1], 2) for i in range(0, len(bs2), 8))
            printable = sum(1 for c in data if 32<=c<127)
            if printable/max(1,len(data)) > 0.6:
                text = data.decode("latin-1")
                print(f"  {src_name} inv={inv} LSB off={off}: {text[:120]!r}")
