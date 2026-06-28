"""Decode the 2-FSK signal in burst 1 (and burst 2).
deviation: +-100 kHz; symbol rate: 10 kBaud; sample rate: 2 MHz.
Samples per symbol: 200.
"""
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import signal

RAW = r"C:\Users\Administrator\Documents\claude\sans\challenges\ggrx\artifacts\gqrx_20250207_112408_405000000_2000000_fc.raw"
OUT = r"C:\Users\Administrator\Documents\claude\sans\challenges\ggrx\out"
SAMP_RATE = 2_000_000
SYMBOL_RATE = 10_000
SPS = SAMP_RATE // SYMBOL_RATE  # 200

raw = np.memmap(RAW, dtype=np.float32, mode="r")
iq = raw.view(np.complex64)

def fm_demod(x):
    """Return inst frequency (Hz) array."""
    phase = np.unwrap(np.angle(x))
    return np.diff(phase) / (2*np.pi) * SAMP_RATE

# Mask out the noisy outside of the burst by finding active region within window
def find_burst_edges(iq_slice, samp_rate=SAMP_RATE):
    """Find sample range where signal is active using power envelope."""
    win = int(0.001 * samp_rate)  # 1ms windows
    n = (iq_slice.size // win) * win
    power_db = 10*np.log10(np.abs(iq_slice[:n].reshape(-1, win))**2 + 1e-20).mean(axis=1)
    # Use max - 10 dB as threshold (signal definitely loud)
    thresh = power_db.max() - 10
    on = np.where(power_db > thresh)[0]
    if on.size == 0:
        return None
    return on[0]*win, (on[-1]+1)*win

def decode_burst(iq_full, burst_start_s, burst_end_s, name):
    s = int(burst_start_s * SAMP_RATE)
    e = int(burst_end_s * SAMP_RATE)
    chunk = iq_full[s:e].copy()
    edges = find_burst_edges(chunk)
    if edges is None:
        print(f"{name}: no burst found")
        return
    bs, be = edges
    # Pad a little inward to ensure we're solidly in signal
    pad = int(0.001 * SAMP_RATE)
    bs = bs + pad
    be = be - pad
    sig = chunk[bs:be]
    print(f"\n=== {name} ===")
    print(f"active samples: {sig.size} (~{sig.size/SAMP_RATE*1000:.1f} ms)")

    # FM demod
    inst_freq = fm_demod(sig)
    # Smooth/low-pass to suppress noise
    # Cutoff < symbol_rate/2 is too aggressive; use ~symbol_rate
    b, a = signal.butter(4, SYMBOL_RATE * 1.5 / (SAMP_RATE/2), btype="low")
    inst_freq_lp = signal.filtfilt(b, a, inst_freq)

    # Show short snippet
    plt.figure(figsize=(14,3))
    snippet = inst_freq_lp[:5*SPS]  # 5 symbols
    plt.plot(np.arange(snippet.size)/SAMP_RATE*1e6, snippet/1e3)
    plt.xlabel("Time (us)")
    plt.ylabel("Inst freq (kHz)")
    plt.title(f"{name}: first 5 symbols (after LPF)")
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(os.path.join(OUT, f"{name}_first_symbols.png"), dpi=140)
    plt.close()

    # Slice to bits: sample at center of each symbol
    # Estimate timing offset by finding the first transition
    # Just decide bit per symbol period:
    n_syms = sig.size // SPS - 2
    bits = []
    for k in range(n_syms):
        # sample window in middle of symbol
        s0 = k*SPS + SPS//4
        s1 = k*SPS + 3*SPS//4
        if s1 > inst_freq_lp.size:
            break
        avg = inst_freq_lp[s0:s1].mean()
        bits.append(1 if avg > 0 else 0)
    bits = np.array(bits, dtype=np.uint8)
    print(f"raw bits length: {bits.size}")
    print(f"first 200 bits: {''.join(str(b) for b in bits[:200])}")

    # Try to find timing more precisely with eye/clock recovery
    # Simpler: try different starting offsets and see which gives 'best' (consistent symbol values)
    best_score = -1
    best_offset = 0
    for off in range(0, SPS, 5):
        score = 0
        for k in range(n_syms - 1):
            s0 = off + k*SPS + SPS//4
            s1 = off + k*SPS + 3*SPS//4
            if s1 > inst_freq_lp.size:
                break
            chunk = inst_freq_lp[s0:s1]
            # confidence = abs(mean) / std
            m = chunk.mean()
            sd = chunk.std() + 1e-9
            score += abs(m) / sd
        if score > best_score:
            best_score = score
            best_offset = off
    print(f"best timing offset within first symbol: {best_offset} samples (score {best_score:.1f})")

    # Re-decode with that offset
    bits = []
    for k in range(n_syms):
        s0 = best_offset + k*SPS + SPS//4
        s1 = best_offset + k*SPS + 3*SPS//4
        if s1 > inst_freq_lp.size:
            break
        avg = inst_freq_lp[s0:s1].mean()
        bits.append(1 if avg > 0 else 0)
    bits = np.array(bits, dtype=np.uint8)
    bitstr = "".join(str(b) for b in bits)
    print(f"bits (length {len(bitstr)}):")
    for i in range(0, len(bitstr), 80):
        print(f"  {bitstr[i:i+80]}")

    # Try ASCII decoding with different alignments / orderings
    print("\nDecoding attempts:")
    print(f"--- 8-bit groups, MSB first, normal (1=high freq) ---")
    for start in range(min(8, len(bitstr))):
        bs2 = bitstr[start:]
        bs2 = bs2[: (len(bs2)//8)*8]
        bytes_arr = bytes(int(bs2[i:i+8], 2) for i in range(0, len(bs2), 8))
        # Score by printability
        printable = sum(1 for c in bytes_arr if 32 <= c < 127)
        if printable / max(1, len(bytes_arr)) > 0.5:
            try:
                txt = bytes_arr.decode("latin-1")
                print(f"  align={start} printable={printable}/{len(bytes_arr)}: {txt!r}")
            except Exception:
                pass
    print(f"--- 8-bit groups, MSB first, INVERTED ---")
    inv = "".join("0" if c=="1" else "1" for c in bitstr)
    for start in range(min(8, len(inv))):
        bs2 = inv[start:]
        bs2 = bs2[: (len(bs2)//8)*8]
        bytes_arr = bytes(int(bs2[i:i+8], 2) for i in range(0, len(bs2), 8))
        printable = sum(1 for c in bytes_arr if 32 <= c < 127)
        if printable / max(1, len(bytes_arr)) > 0.5:
            try:
                txt = bytes_arr.decode("latin-1")
                print(f"  align={start} printable={printable}/{len(bytes_arr)}: {txt!r}")
            except Exception:
                pass
    print(f"--- 8-bit groups, LSB first ---")
    for start in range(min(8, len(bitstr))):
        bs2 = bitstr[start:]
        bs2 = bs2[: (len(bs2)//8)*8]
        bytes_arr = bytes(int(bs2[i:i+8][::-1], 2) for i in range(0, len(bs2), 8))
        printable = sum(1 for c in bytes_arr if 32 <= c < 127)
        if printable / max(1, len(bytes_arr)) > 0.5:
            try:
                txt = bytes_arr.decode("latin-1")
                print(f"  align={start} printable={printable}/{len(bytes_arr)}: {txt!r}")
            except Exception:
                pass

    return bitstr

b1 = decode_burst(iq, 1.00, 1.35, "burst1")
b2 = decode_burst(iq, 4.20, 4.55, "burst2")

if b1 and b2:
    print(f"\nburst1 == burst2 ? {b1 == b2}")
    print(f"burst1 length: {len(b1)}, burst2 length: {len(b2)}")
    if len(b1) == len(b2):
        diff = sum(1 for a,b in zip(b1,b2) if a!=b)
        print(f"differing bits: {diff}")
