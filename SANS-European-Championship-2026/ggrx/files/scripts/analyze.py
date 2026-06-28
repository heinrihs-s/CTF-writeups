"""Initial spectral analysis of the GQRX IQ recording.

File naming convention: gqrx_<date>_<time>_<centerFreq>_<sampleRate>_fc.raw
  centerFreq = 405000000 (405 MHz)
  sampleRate = 2000000   (2 MHz)
  fc = complex float32 (interleaved I,Q float32)
"""
import os, sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

RAW = r"C:\Users\Administrator\Documents\claude\sans\challenges\ggrx\artifacts\gqrx_20250207_112408_405000000_2000000_fc.raw"
OUT = r"C:\Users\Administrator\Documents\claude\sans\challenges\ggrx\out"
os.makedirs(OUT, exist_ok=True)

CENTER_HZ = 405_000_000
SAMP_RATE = 2_000_000

raw = np.memmap(RAW, dtype=np.float32, mode="r")
n_samples = raw.size // 2
print(f"file size bytes: {os.path.getsize(RAW)}")
print(f"samples (complex): {n_samples}")
print(f"duration: {n_samples / SAMP_RATE:.3f} s")

# Reshape to complex
iq = raw[: 2 * n_samples].view(np.complex64)
# iq is now N complex samples; the .view trick only works because float32 -> complex64
# Actually we need interleaved I,Q -> complex; np.float32 length 2N viewed as complex64 length N works.
print(f"iq dtype: {iq.dtype}, shape: {iq.shape}")
print(f"iq[:5] = {iq[:5]}")

# Quick stats
power = (np.abs(iq[:2_000_000])**2).mean()
print(f"avg power (first 1s window): {power:.6g}")

# PSD using Welch
from scipy import signal
N_FFT = 4096
f, Pxx = signal.welch(iq[:5_000_000], fs=SAMP_RATE, nperseg=N_FFT, return_onesided=False)
f = np.fft.fftshift(f)
Pxx = np.fft.fftshift(Pxx)
freqs_hz = f + CENTER_HZ
plt.figure(figsize=(12, 4))
plt.plot(freqs_hz / 1e6, 10*np.log10(Pxx + 1e-20))
plt.xlabel("Frequency (MHz)")
plt.ylabel("PSD (dB)")
plt.title("PSD of GQRX recording (center 405 MHz, span 2 MHz)")
plt.grid(True)
plt.tight_layout()
plt.savefig(os.path.join(OUT, "psd.png"), dpi=120)
plt.close()
print("wrote psd.png")

# Find peaks above noise floor
psd_db = 10*np.log10(Pxx + 1e-20)
noise = np.median(psd_db)
print(f"noise floor (median PSD dB): {noise:.2f}")
# bins more than 15 dB above noise
peaks_mask = psd_db > noise + 15
if peaks_mask.any():
    peak_bins = np.where(peaks_mask)[0]
    # cluster contiguous bins
    groups = []
    cur = [peak_bins[0]]
    for b in peak_bins[1:]:
        if b - cur[-1] <= 3:
            cur.append(b)
        else:
            groups.append(cur)
            cur = [b]
    groups.append(cur)
    print(f"{len(groups)} peak group(s) above noise+15dB:")
    for g in groups:
        center_bin = g[len(g)//2]
        bw_hz = (g[-1] - g[0]) * (SAMP_RATE / N_FFT)
        peak_freq = freqs_hz[center_bin]
        peak_db = psd_db[center_bin]
        print(f"  ~{peak_freq/1e6:.4f} MHz  ({(peak_freq-CENTER_HZ)/1e3:+.1f} kHz offset)  BW~{bw_hz/1e3:.1f} kHz  peak {peak_db:.1f} dB")
else:
    print("no strong peaks; the signal may be wideband")

# Also: spectrogram for time-evolution
plt.figure(figsize=(12, 4))
n_used = min(iq.size, 2_000_000 * 6)
f2, t2, Sxx = signal.spectrogram(iq[:n_used], fs=SAMP_RATE, nperseg=2048, noverlap=1024, return_onesided=False)
f2 = np.fft.fftshift(f2)
Sxx = np.fft.fftshift(Sxx, axes=0)
plt.pcolormesh(t2, (f2 + CENTER_HZ)/1e6, 10*np.log10(Sxx + 1e-20), shading="auto")
plt.ylabel("Frequency (MHz)")
plt.xlabel("Time (s)")
plt.colorbar(label="PSD dB")
plt.title("Spectrogram")
plt.tight_layout()
plt.savefig(os.path.join(OUT, "spectrogram.png"), dpi=120)
plt.close()
print("wrote spectrogram.png")
