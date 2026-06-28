"""Brute force XOR stream search.

For each candidate derivation, generate a long keystream, then check every 23-byte window
to see if it XORs ct to printable ASCII."""
import hashlib
import hmac
import time

pw = b"this-is-a-really-long-password-you-will-not-guess-it-easily"
salt_x = bytes.fromhex("60cf7473ce0a6a88")
salt = bytes.fromhex("ea45fef94480e002")
verify_x = bytes.fromhex("8e03")
verify = bytes.fromhex("0489")
ct_x = bytes.fromhex("63f9bdb95ac3ccc9184bf2233c6ad6a2cdd5f494dae956")
ct = bytes.fromhex("e9733733d049464392c178a9b6e05c28475f7e1e5063dc")
mac_x = bytes.fromhex("504b01023f0333030100")
mac_raw = bytes.fromhex("dac18b88b589b9898b8a")
filename = b"LQrzcQkpzrvBfEcXEpAdqqucVbYa"

def is_printable_or_close(s, threshold=20):
    return sum(1 for b in s if 32 <= b < 127) >= threshold

def gen_keystreams():
    """Yield long byte sequences."""
    # Single hash digests, repeated
    for h_name in ['md5', 'sha1', 'sha256', 'sha512', 'sha3_256', 'sha3_512', 'sha384', 'sha224',
                   'blake2b', 'blake2s']:
        try:
            d = hashlib.new(h_name, pw).digest()
            yield (f"H-{h_name}(pw)", d * 10)
            d2 = hashlib.new(h_name, pw + salt_x).digest()
            yield (f"H-{h_name}(pw+salt_x)", d2 * 10)
            d3 = hashlib.new(h_name, salt_x + pw).digest()
            yield (f"H-{h_name}(salt_x+pw)", d3 * 10)
            d4 = hashlib.new(h_name, pw + salt).digest()
            yield (f"H-{h_name}(pw+salt)", d4 * 10)
            d5 = hashlib.new(h_name, salt + pw).digest()
            yield (f"H-{h_name}(salt+pw)", d5 * 10)
            d6 = hashlib.new(h_name, pw + filename).digest()
            yield (f"H-{h_name}(pw+fn)", d6 * 10)
            d7 = hashlib.new(h_name, filename + pw).digest()
            yield (f"H-{h_name}(fn+pw)", d7 * 10)
        except: pass

    # Counter-based: H(pw + counter) for various lengths
    for h_name in ['sha1', 'sha256', 'md5', 'blake2b']:
        ks = b''
        for i in range(64):
            ks += hashlib.new(h_name, pw + i.to_bytes(4, 'big')).digest()
        yield (f"iter-{h_name}(pw+i_be4)", ks)

        ks = b''
        for i in range(64):
            ks += hashlib.new(h_name, pw + i.to_bytes(4, 'little')).digest()
        yield (f"iter-{h_name}(pw+i_le4)", ks)

        ks = b''
        for i in range(64):
            ks += hashlib.new(h_name, pw + salt_x + i.to_bytes(4, 'big')).digest()
        yield (f"iter-{h_name}(pw+salt_x+i_be4)", ks)

        ks = b''
        for i in range(64):
            ks += hashlib.new(h_name, pw + salt + i.to_bytes(4, 'big')).digest()
        yield (f"iter-{h_name}(pw+salt+i_be4)", ks)

        ks = b''
        for i in range(64):
            ks += hashlib.new(h_name, salt_x + pw + i.to_bytes(4, 'big')).digest()
        yield (f"iter-{h_name}(salt_x+pw+i_be4)", ks)

        ks = b''
        for i in range(64):
            ks += hashlib.new(h_name, salt + pw + i.to_bytes(4, 'big')).digest()
        yield (f"iter-{h_name}(salt+pw+i_be4)", ks)

        # i_be8
        ks = b''
        for i in range(64):
            ks += hashlib.new(h_name, pw + salt_x + i.to_bytes(8, 'big')).digest()
        yield (f"iter-{h_name}(pw+salt_x+i_be8)", ks)

        # i_be1 (1 byte counter)
        ks = b''
        for i in range(64):
            ks += hashlib.new(h_name, pw + salt_x + bytes([i])).digest()
        yield (f"iter-{h_name}(pw+salt_x+i_be1)", ks)

    # HMAC variants
    for h_name in ['sha1', 'sha256', 'md5', 'sha512']:
        ks = b''
        for i in range(64):
            ks += hmac.new(pw, salt_x + i.to_bytes(4, 'big'), h_name).digest()
        yield (f"hmac-{h_name}(pw, salt_x+i)", ks)

        ks = b''
        for i in range(64):
            ks += hmac.new(pw, salt + i.to_bytes(4, 'big'), h_name).digest()
        yield (f"hmac-{h_name}(pw, salt+i)", ks)

        ks = b''
        for i in range(64):
            ks += hmac.new(salt_x, pw + i.to_bytes(4, 'big'), h_name).digest()
        yield (f"hmac-{h_name}(salt_x, pw+i)", ks)

    # PBKDF2 with various output lengths
    for h_name in ['sha1', 'sha256', 'sha512']:
        for iters in [1, 100, 1000, 10000]:
            for s in [salt_x, salt]:
                try:
                    out = hashlib.pbkdf2_hmac(h_name, pw, s, iters, 200)
                    yield (f"pbkdf2-{h_name}-{iters}-salt_{'x' if s==salt_x else 'raw'}", out)
                except: pass

    # Just pw repeated
    yield ("pw_repeated", pw * 5)

    # Filename and pw concatenated repeatedly
    yield ("fn+pw_repeated", (filename + pw) * 3)

    # md5(pw)+md5(pw)+...
    md5_pw = hashlib.md5(pw).digest()
    yield ("md5(pw)*4", md5_pw * 4)

    # sha1(pw)*4
    sha1_pw = hashlib.sha1(pw).digest()
    yield ("sha1(pw)*4", sha1_pw * 4)

# For each keystream, slide a 23-byte window and try XOR against both ct interpretations
print("Searching for keystreams that XOR ct to printable plaintext...")
start = time.time()
results = []

for name, ks in gen_keystreams():
    for ct_label, ct_v in [("raw", ct), ("xor", ct_x)]:
        for offset in range(min(len(ks) - 23, 200)):
            window = ks[offset:offset+23]
            pt = bytes(a ^ b for a, b in zip(window, ct_v))
            score = sum(1 for b in pt if 32 <= b < 127)
            if score >= 18:
                results.append((score, name, ct_label, offset, pt))

print(f"Done in {time.time()-start:.1f}s. Found {len(results)} candidates.")
results.sort(reverse=True)
for r in results[:30]:
    print(f"  score={r[0]} {r[1]:50s} ct={r[2]} off={r[3]:3d} pt={r[4]!r}")
