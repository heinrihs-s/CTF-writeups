# .GGRX

> Category: Mixed Offensive / SDR. Event: SANS European Championship 2026.

This was radio stuff. I do not pretend I am a ham wizard, but IQ files are basically "numbers pretending to be radio", so Python can bully them.

## Challenge

We got a GQRX IQ recording:

```text
gqrx_20250207_112408_405000000_2000000_fc.raw
```

The hint in the name basically screams:

- center frequency: 405 MHz
- sample rate: 2 MHz
- raw IQ float data

The inner flag in the signal was:

```text
{GroUndC0ntr0l2MajorTom}
```

The platform wanted the wrapped version:

```text
mne{GroUndC0ntr0l2MajorTom}
```

## Files

Simple layout:

- [prompt.md](prompt.md) is the original prompt
- [files/sdr.7z](files/sdr.7z) is the original SDR archive
- this README is the thought process
- the expanded 89MB raw IQ file is not committed, becouse that is too much for a public writeup repo

## First look

I started with spectrum pictures and guessed too many protocols. POCSAG? some pager thing? maybe something more fancy?

Nope. It was much dumber and better: two FSK bursts, around 1200 baud.

The useful flow was:

1. load IQ as `complex64`
2. FM demod by phase difference
3. low-pass around symbol rate
4. detect burst by power
5. sample symbols
6. decode ASCII at the right bit offset

## The code that mattered

The demod bit was this:

```python
import numpy as np
from scipy import signal

SAMP_RATE = 2_000_000
SYMBOL_RATE = 1200
SPS = SAMP_RATE / SYMBOL_RATE

raw = np.memmap("gqrx.raw", dtype=np.float32, mode="r")
iq = raw.view(np.complex64)

def fm_demod(x):
    phase = np.unwrap(np.angle(x))
    return np.diff(phase) / (2*np.pi) * SAMP_RATE

sig = iq[int(1.00*SAMP_RATE):int(1.35*SAMP_RATE)].copy()
inst_freq = fm_demod(sig)

b, a = signal.butter(4, SYMBOL_RATE*2/(SAMP_RATE/2), btype="low")
lp = signal.filtfilt(b, a, inst_freq)
```

Then I used power to find the burst:

```python
power = np.abs(sig)**2
smoothed = np.convolve(power, np.ones(200)/200, mode="same")
on = np.where(smoothed > smoothed.max() * 0.5)[0]
start_idx, end_idx = on[0], on[-1]
```

The most annoying part was symbol alignment. If you sample 1/4 symbol off, ASCII becomes garbage and you start seeing ghosts.

## Dumb dead end

I searched for POCSAG sync. Because radio recording = pager maybe? This was wrong enough:

```python
POCSAG_SYNC = 0x7CD215D8
sync_bits = bin(POCSAG_SYNC)[2:].zfill(32)
```

No useful sync. So back to boring ASCII.

## Getting text

After timing search, offset 1 was the good one. Turning bits into bytes:

```python
bits = decode_burst(1.00, 1.35)
bs = bits[1:]
bs = bs[:(len(bs)//8)*8]
data = bytes(int(bs[i:i+8], 2) for i in range(0, len(bs), 8))
print(data)
```

And the nice little brace string appeared:

```text
{GroUndC0ntr0l2MajorTom}
```

## Why it worked

FSK is simple: one frequency means one bit, another frequency means the other bit. FM demod turns frequency wiggle into positive/negative values, and then it is just timing.

The trick was not crypto. It was just "do you know how to turn an IQ blob back into bits". Once the baud and offset were right, the flag was not hidden anymore, it was yelling.
