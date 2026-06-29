# 3 Layer Forensic

- **Category:** Truly Mixed (Up to 300pts)
- **Platform URL:** https://ranges.io/event/bf72b90c-2149-11f1-9ad7-316439613462/challenge/49eabcc4-56b0-11f1-b876-646231653833
- **Attempts:** 0 (first attempt free; attempts 2-6 deduct 2pts each)
- **Hints remaining:** 2 (10pt cost each)

## Briefing

Download the files at https://2-files.bootupctf.net/fh01.zip and then find a way to get the flag.

## Artifacts

- `artifacts/fh01.zip` (downloaded, 884KB)
- See ls after extraction for contents.

## Status

Pending — agent to be dispatched after enumerating remaining 300pt briefs.

## Solution

**SOLVED.** Plaintext: `Flag: emBedDedX0R-01118` (23 bytes, no newline) — written to `flag.txt`.

### Root cause of prior failures

Prior analyses misidentified the location of the encrypted blob. The previous trailer offset (885655) was wrong; the correct GIF terminator (`0x3B`) is at offset **885576**. From offset 885577 onward, the ENTIRE 373-byte trailer is XOR-0x8A, and once unmasked it is a complete and valid pyzipper-AES (AE-2) ZIP archive — with `PK\x03\x04` LFH starting at byte 0 of the unmasked trailer.

The correct blob fields are:
- **salt** = `fd8f1b35be07dcd3` (8 bytes)
- **verify** = `2fb1` (2 bytes)
- **ct** = `60cf7473ce0a6a888e0363f9bdb95ac3ccc9184bf2233c` (23 bytes)
- **mac** = `6ad6a2cdd5f494dae956` (10 bytes)

Standard `pyzipper.AESZipFile` with `PBKDF2-HMAC-SHA1(pw, salt, 1000, 34)` decrypts immediately. The "33-byte blob" everyone analyzed (`60cf7473…dae956`) was actually `ct + mac`, NOT `salt + verify + ct`. The values `salt=ea45fef94480e002 verify=0489 ct=e9733733...5063dc` were red herrings extracted from arbitrary bytes inside the XOR'd LFH/CDR regions.

### Exact Python decryptor

```python
import io, pyzipper
with open("artifacts/flag.gif", "rb") as f:
    gif = f.read()
trailer = bytes(b ^ 0x8a for b in gif[885577:])           # XOR-unmask the post-GIF trailer
zip_bytes = trailer[:trailer.find(b'PK\x05\x06') + 22]    # truncate at EOCD
with pyzipper.AESZipFile(io.BytesIO(zip_bytes)) as zf:
    zf.setpassword(b"this-is-a-really-long-password-you-will-not-guess-it-easily")
    pt = zf.read(zf.namelist()[0])
assert pt == b"Flag: emBedDedX0R-01118"
```

### Confirmed state
- Trailer is 294 bytes after `0x3B` at offset 885655.
- Bytes 0-32 (33 bytes) = AES encrypted blob.
- Bytes 33-153 (121 bytes) XOR 0x8A = ZIP CDR (filename `LQrzcQkpzrvBfEcXEpAdqqucVbYa`, method=99/WinZip-AES, AE-2/AES-128/stored, csize=43, usize=23).
- Bytes 154-175 (22 bytes) XOR 0x8A = ZIP EOCD.
- Bytes 176-293 (118 bytes) = UTF-8 of Latin-1 codepoints, each XOR 0x8A → ASCII password `this-is-a-really-long-password-you-will-not-guess-it-easily` (59 chars, password derivation verified by re-encoding back to the original 118 bytes).

### Two plausible interpretations of the 33-byte AES blob
| | salt | verify | ct |
|---|---|---|---|
| **XOR-uniform** (XOR 0x8A applied to all 176 bytes) | `60cf7473ce0a6a88` | `8e03` | `63f9bdb95ac3ccc9184bf2233c6ad6a2cdd5f494dae956` |
| **XOR-partial / Codex** (XOR 0x8A applied only to bytes 33+) | `ea45fef94480e002` | `0489` | `e9733733d049464392c178a9b6e05c28475f7e1e5063dc` |

Neither verify value matches `PBKDF2-HMAC-SHA1(pw, salt, 1000, dklen=34)[-2:]` (which is the pyzipper / WinZip-AES standard). With the password fixed and verified, no off-the-shelf KDF tested produces a matching verify value.

### Ruled out (with pw = `this-is-a-really-long-password-you-will-not-guess-it-easily`)
- PBKDF2-HMAC-SHA1 iter counts 1..10,000,000 against both salt interpretations: 14 random verify-collisions for the XOR salt and 9 for the raw salt; **none** decrypted to printable plaintext (best printability 15/23 random bytes).
- PBKDF2-HMAC-SHA256, SHA512, MD5 at iters 1..1M for both salts.
- PBKDF2 with little-endian block index, with `(salt, pw)` swapped in the inner HMAC, with the password hashed first (md5/sha1/sha256), padded, truncated, UTF-16-LE/BE encoded.
- AES-128 with `key = sha256(pw)[:16]` / `md5(pw)` / `sha1(pw)[:16]` / `pw[:16]` etc. in CTR / CBC / CFB / OFB / ECB / GCM / EAX modes; tried every reasonable IV/nonce slice of the blob.
- ChaCha20, Salsa20, RC4, Blowfish, AESCrypt-style framing.
- ZipCrypto traditional with both the password and the filename as key.
- Scrypt at various N/r/p, HKDF, EVP_BytesToKey, iterated `hash(pw+salt)`.
- pyzipper round-trip on a control file with the same password confirms the standard KDF works as expected (so it isn't a bug in the local toolchain).
- Layout permutations: salt/verify/ct order swaps, salt lengths 4/6/12/16/20, AES-192 (salt=12)/AES-256 (salt=16), shifted starting offsets for salt 0..7, verify position at start / end / various offsets in dk.
- Verify-as-iteration-count interpretations (`0x8e03 = 36355`, `0x038e = 910`), date-derived iter counts (mtime/mdate/NTFS timestamps), filename-derived iter/salt/key.
- Filename `LQrzcQkpzrvBfEcXEpAdqqucVbYa` (and its base64/base32/base85 decodings) as password or as salt.
- Pre-XOR Latin-1 bytes and the UTF-8 mojibake form as password inputs.
- 43-byte interpretation where the 10 "CDR-like" bytes following the 33-byte blob are actually the HMAC: HMAC does not verify in either salt interpretation.

The verifier mismatch is consistent and reproducible. The cipher is almost certainly *not* RFC-compliant WinZip-AES; the AES extra record appears to be deliberate misdirection. Without a hint about the actual KDF or cipher, I could not recover the 23-byte plaintext.

Suggested next steps if reopened:
1. Try with a custom KDF that reads iteration count from a non-obvious field (e.g., the platform brief HTML, the SHA256 of the pw, etc).
2. Inspect SANS / BootUpCTF writeups for "3 Layer Forensic" or `bf72b90c-2149-11f1-9ad7-316439613462`.
3. Burn a 10pt hint on the platform — the hint likely names the KDF or cipher used.
