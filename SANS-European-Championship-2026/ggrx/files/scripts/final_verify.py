"""Final verification: decode both bursts, show full payloads, hex dump."""
import os
import numpy as np
from scipy import signal

RAW = r"C:\Users\Administrator\Documents\claude\sans\challenges\ggrx\artifacts\gqrx_20250207_112408_405000000_2000000_fc.raw"
SAMP_RATE = 2_000_000
SYMBOL_RATE = 1200
SPS = SAMP_RATE / SYMBOL_RATE

raw = np.memmap(RAW, dtype=np.float32, mode="r")
iq = raw.view(np.complex64)

def fm_demod(x):
    phase = np.unwrap(np.angle(x))
    return np.diff(phase) / (2*np.pi) * SAMP_RATE

def decode(start_s, end_s, name):
    s = int(start_s*SAMP_RATE)
    e = int(end_s*SAMP_RATE)
    sig = iq[s:e].copy()
    inst_freq = fm_demod(sig)
    b, a = signal.butter(4, SYMBOL_RATE*2/(SAMP_RATE/2), btype="low")
    lp = signal.filtfilt(b, a, inst_freq)
    power = np.abs(sig)**2
    smoothed = np.convolve(power, np.ones(200)/200, mode="same")
    pthresh = smoothed.max() * 0.5
    on = np.where(smoothed > pthresh)[0]
    start_idx, end_idx = on[0], on[-1]
    sign = np.sign(lp[start_idx:start_idx + int(20*SPS)])
    cross = np.where(np.diff(sign) != 0)[0]
    first_cross = cross[0]
    n_syms = int((end_idx - start_idx) / SPS) - 1
    best = (None, -1)
    for off_pre in range(-100, 100, 2):
        s0 = start_idx + first_cross + off_pre + int(SPS/2)
        score = 0
        for k in range(min(400, n_syms)):
            ctr = s0 + int(k*SPS)
            lo = ctr - int(SPS*0.2)
            hi = ctr + int(SPS*0.2)
            if hi >= lp.size:
                break
            m = lp[lo:hi].mean()
            sd = lp[lo:hi].std() + 1e-9
            score += abs(m)/sd
        if score > best[1]:
            best = (s0, score)
    s0 = best[0]
    bits = []
    for k in range(n_syms):
        ctr = s0 + int(k*SPS)
        lo = ctr - int(SPS*0.2)
        hi = ctr + int(SPS*0.2)
        if hi >= lp.size:
            break
        m = lp[lo:hi].mean()
        bits.append(1 if m > 0 else 0)
    return "".join(str(b) for b in bits)

for s, e, name in [(1.00, 1.35, "burst1"), (4.20, 4.55, "burst2")]:
    bits = decode(s, e, name)
    print(f"\n=== {name} ({len(bits)} bits) ===")
    # off=1 is the winner
    bs = bits[1:]
    bs = bs[:(len(bs)//8)*8]
    data = bytes(int(bs[i:i+8], 2) for i in range(0, len(bs), 8))
    print("hex:", data.hex())
    text = "".join(chr(c) if 32<=c<127 else f"\\x{c:02x}" for c in data)
    print("repr:", text)
    print("bytes len:", len(data))
    import re
    m = re.search(rb"\{([^{}]+)\}", data)
    if m:
        print("FLAG inner:", m.group(1).decode("ascii"))
        print("FLAG with braces:", m.group(0).decode("ascii"))
