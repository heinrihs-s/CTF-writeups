"""Decode 2-FSK at 2400 baud and search for the flag."""
import os, sys
import numpy as np
from scipy import signal
from scipy.io import wavfile

RAW = r"C:\Users\Administrator\Documents\claude\sans\challenges\ggrx\artifacts\gqrx_20250207_112408_405000000_2000000_fc.raw"
OUT = r"C:\Users\Administrator\Documents\claude\sans\challenges\ggrx\out"
SAMP_RATE = 2_000_000
SYMBOL_RATE = 2400
SPS = SAMP_RATE / SYMBOL_RATE  # 833.33

raw = np.memmap(RAW, dtype=np.float32, mode="r")
iq = raw.view(np.complex64)

def fm_demod(x):
    phase = np.unwrap(np.angle(x))
    return np.diff(phase) / (2*np.pi) * SAMP_RATE

def decode(start_s, end_s, name, polarity=1):
    s = int(start_s * SAMP_RATE)
    e = int(end_s * SAMP_RATE)
    sig = iq[s:e].copy()
    inst_freq = fm_demod(sig) * polarity
    # LPF to symbol bandwidth
    b, a = signal.butter(4, SYMBOL_RATE * 2 / (SAMP_RATE/2), btype="low")
    lp = signal.filtfilt(b, a, inst_freq)

    # Pre-amble sync: find first strong transition to anchor symbol clock
    sign = np.sign(lp)
    # Use a transition-based clock recovery: find all zero crossings
    crossings = np.where(np.diff(sign) != 0)[0]
    # The minimum gap between consecutive transitions is ~1 symbol = 833 samples
    # Use the median of the smallest crossings as one symbol
    diffs = np.diff(crossings)
    one_sym = np.median(diffs[diffs < 1200])  # filter to one-symbol diffs
    if np.isnan(one_sym):
        one_sym = SPS
    print(f"\n{name}: estimated samples/symbol from crossings: {one_sym:.2f} (theory {SPS:.2f})")
    sps = float(one_sym) if 800 < one_sym < 900 else SPS

    # Time of first transition where signal is "obviously" on
    # Find sample where envelope first stays high
    power = np.abs(sig)**2
    win = 200
    smoothed = np.convolve(power, np.ones(win)/win, mode="same")
    pthresh = smoothed.max() * 0.5
    on = np.where(smoothed > pthresh)[0]
    start_idx = on[0] if on.size else 0
    end_idx = on[-1] if on.size else sig.size
    print(f"  active samples: {start_idx}..{end_idx} ({(end_idx-start_idx)/SAMP_RATE*1000:.1f} ms)")

    # Sample at center of each symbol period
    # Find best timing offset by looking at first ~50 ms of active signal for max sign clarity
    n_sym = int((end_idx - start_idx) / sps) - 2
    best_score = -1
    best_off = 0
    for off in range(0, int(sps), 5):
        s0 = start_idx + off
        score = 0
        for k in range(min(200, n_sym)):
            center = int(s0 + k*sps + sps/2)
            if center < lp.size:
                # mean over middle half
                lo = int(s0 + k*sps + sps*0.3)
                hi = int(s0 + k*sps + sps*0.7)
                m = lp[lo:hi].mean()
                sd = lp[lo:hi].std() + 1e-9
                score += abs(m) / sd
        if score > best_score:
            best_score = score
            best_off = off
    print(f"  best timing offset: {best_off} samples (score {best_score:.1f})")

    bits = []
    s0 = start_idx + best_off
    for k in range(n_sym):
        lo = int(s0 + k*sps + sps*0.3)
        hi = int(s0 + k*sps + sps*0.7)
        if hi > lp.size:
            break
        m = lp[lo:hi].mean()
        bits.append(1 if m > 0 else 0)
    bits = "".join(str(b) for b in bits)
    print(f"  bits len {len(bits)}")
    print(f"  first 256: {bits[:256]}")
    return bits

b1 = decode(1.00, 1.35, "burst1", polarity=1)
b2 = decode(4.20, 4.55, "burst2", polarity=1)

print(f"\nb1 == b2 (full)?  {b1==b2}")
print(f"b1[:200] == b2[:200]?  {b1[:200]==b2[:200]}")
print(f"b1 length: {len(b1)} | b2 length: {len(b2)}")

# Look for POCSAG sync codeword 0x7CD215D8 (and its inverse)
POCSAG_SYNC = 0x7CD215D8
sync_bits = bin(POCSAG_SYNC)[2:].zfill(32)
inv_sync_bits = "".join("1" if c=="0" else "0" for c in sync_bits)

def find_pattern(bits, pat):
    locations = []
    i = 0
    while True:
        idx = bits.find(pat, i)
        if idx < 0:
            break
        locations.append(idx)
        i = idx + 1
    return locations

print("\nSearching for POCSAG sync 0x7CD215D8...")
for bs, name in [(b1, "burst1"), (b2, "burst2")]:
    locs = find_pattern(bs, sync_bits)
    locs_inv = find_pattern(bs, inv_sync_bits)
    print(f"  {name}: {len(locs)} matches normal, {len(locs_inv)} matches inverted")
    if locs:
        print(f"    normal locations: {locs[:5]}")
    if locs_inv:
        print(f"    inverted locations: {locs_inv[:5]}")

# Try ASCII MSB-first across alignments and polarities
print("\n--- ASCII decode attempts (MSB-first, both polarities, 8 alignments) ---")
for src_name, src in [("b1", b1), ("b2", b2)]:
    for inv in [False, True]:
        b = "".join("1" if c=="0" else "0" for c in src) if inv else src
        for off in range(8):
            bs2 = b[off:]
            bs2 = bs2[:(len(bs2)//8)*8]
            data = bytes(int(bs2[i:i+8], 2) for i in range(0, len(bs2), 8))
            printable = sum(1 for c in data if 32 <= c < 127 or c in (10,13,9))
            ratio = printable/max(1,len(data))
            if ratio > 0.6:
                text = "".join(chr(c) if 32<=c<127 else "." for c in data)
                print(f"  {src_name} inv={inv} off={off} ratio={ratio:.2f}: {text[:120]!r}")
