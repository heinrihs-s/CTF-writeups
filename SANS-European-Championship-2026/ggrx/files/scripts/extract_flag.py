"""Extract the full flag with proper alignment."""
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

def decode_burst(start_s, end_s, name):
    s = int(start_s * SAMP_RATE)
    e = int(end_s * SAMP_RATE)
    sig = iq[s:e].copy()
    inst_freq = fm_demod(sig)
    b, a = signal.butter(4, SYMBOL_RATE*2/(SAMP_RATE/2), btype="low")
    lp = signal.filtfilt(b, a, inst_freq)
    power = np.abs(sig)**2
    win = 200
    smoothed = np.convolve(power, np.ones(win)/win, mode="same")
    pthresh = smoothed.max() * 0.5
    on = np.where(smoothed > pthresh)[0]
    start_idx = on[0]
    end_idx = on[-1]
    print(f"\n{name}: {start_idx}..{end_idx} ({(end_idx-start_idx)/SAMP_RATE*1000:.1f}ms)")

    # Better timing recovery: use first transition to phase-lock
    # 0101 preamble → transitions every 1 symbol
    sign = np.sign(lp[start_idx:start_idx + int(20*SPS)])
    cross = np.where(np.diff(sign) != 0)[0]
    # The first valid 1->-1 or -1->1 transition (after settling) anchors symbol boundary
    # Symbol boundary should be at midpoint of two crossings of same direction? No — for FSK, each transition is at start of a new symbol where bit changes
    if cross.size:
        first_cross = cross[0]
        print(f"first cross at +{first_cross} samples (={first_cross/SAMP_RATE*1e6:.1f} us)")
    # The preamble alternates 0101 -> transitions at every symbol boundary
    # Place sample at symbol center: first_cross + sps/2 + k*sps
    # Refine timing offset by maximizing |lp(center)|
    n_syms = int((end_idx - start_idx) / SPS) - 1

    best = (None, None, -1)
    for off_pre in range(-50, 50, 5):  # fine search around first_cross
        if cross.size == 0:
            break
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
        if score > best[2]:
            best = (s0, off_pre, score)
    s0, off_pre, score = best
    print(f"chosen s0 (first sym center): {s0}, off_pre {off_pre}, score {score:.1f}")

    bits = []
    for k in range(n_syms):
        ctr = s0 + int(k*SPS)
        lo = ctr - int(SPS*0.2)
        hi = ctr + int(SPS*0.2)
        if hi >= lp.size:
            break
        m = lp[lo:hi].mean()
        bits.append(1 if m > 0 else 0)
    bs = "".join(str(b) for b in bits)
    print(f"bits ({len(bs)}): {bs[:300]}")
    return bs

b1 = decode_burst(1.00, 1.35, "burst1")
b2 = decode_burst(4.20, 4.55, "burst2")

# Decode ASCII
for src_name, src in [("b1", b1), ("b2", b2)]:
    for off in range(8):
        bs2 = src[off:]
        bs2 = bs2[:(len(bs2)//8)*8]
        data = bytes(int(bs2[i:i+8], 2) for i in range(0, len(bs2), 8))
        printable = sum(1 for c in data if 32<=c<127)
        ratio = printable/max(1,len(data))
        if ratio > 0.6:
            try:
                text = data.decode("ascii", errors="replace")
            except Exception:
                text = data.decode("latin-1")
            print(f"{src_name} off={off} ratio={ratio:.2f}: {text!r}")
            # Look for {...} flag
            import re
            for m in re.finditer(r"\{[^{}]+\}", text):
                print(f"  >>> POSSIBLE FLAG: {m.group(0)!r}")
