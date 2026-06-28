"""Examine run lengths from inst freq to deduce true symbol rate."""
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import signal

RAW = r"C:\Users\Administrator\Documents\claude\sans\challenges\ggrx\artifacts\gqrx_20250207_112408_405000000_2000000_fc.raw"
OUT = r"C:\Users\Administrator\Documents\claude\sans\challenges\ggrx\out"
SAMP_RATE = 2_000_000

raw = np.memmap(RAW, dtype=np.float32, mode="r")
iq = raw.view(np.complex64)

# Take a guaranteed-clean piece of burst1 (1.07s to 1.29s)
s, e = int(1.075*SAMP_RATE), int(1.290*SAMP_RATE)
sig = iq[s:e].copy()
print(f"clean burst1 samples: {sig.size}, dur {sig.size/SAMP_RATE*1000:.1f} ms")

phase = np.unwrap(np.angle(sig))
inst_freq = np.diff(phase) / (2*np.pi) * SAMP_RATE

# Light LPF
b, a = signal.butter(4, 50_000 / (SAMP_RATE/2), btype="low")
lp = signal.filtfilt(b, a, inst_freq)

# Find zero crossings -> transitions
sign = np.sign(lp)
# Runs of same sign
crossings = np.where(np.diff(sign) != 0)[0]
print(f"transitions: {crossings.size}")
runs = np.diff(crossings)
print(f"run length stats (samples): min={runs.min()} max={runs.max()} mean={runs.mean():.2f} median={np.median(runs):.1f}")
print(f"  in microseconds: min={runs.min()/SAMP_RATE*1e6:.1f} max={runs.max()/SAMP_RATE*1e6:.1f} median={np.median(runs)/SAMP_RATE*1e6:.1f}")

# Histogram of run lengths
plt.figure(figsize=(12,4))
plt.hist(runs/SAMP_RATE*1e6, bins=200)
plt.xlabel("Run length (us)")
plt.ylabel("count")
plt.title("Inst-freq sign-run lengths")
plt.tight_layout()
plt.savefig(os.path.join(OUT, "runs_hist.png"), dpi=140)
plt.close()

# GCD of runs (assuming integer symbol multiples)
from math import gcd
from functools import reduce
# Take only stable runs
runs_us = (runs / SAMP_RATE * 1e6).round().astype(int)
print(f"first 50 runs (us): {runs_us[:50]}")

# GCD
g = reduce(gcd, runs_us[:100])
print(f"GCD of first 100 runs (us): {g}")

# Try several symbol rates
for sym_rate in [10000, 9600, 4800, 2400, 5000, 2500, 20000, 25000, 50000]:
    sym_us = 1e6/sym_rate
    # ratio
    ratios = runs_us / sym_us
    rounded = np.round(ratios)
    err = np.abs(ratios - rounded)
    pct_within_5pct = (err < 0.1).mean()  # 10% tolerance
    print(f"sym_rate={sym_rate:>6} Hz ({sym_us:.2f} us/sym): {pct_within_5pct*100:.1f}% runs are integer multiples; sample run/sym: {ratios[:10].round(2)}")
