"""Try many custom KDFs to find one that produces verify=8e03 (xor) or 0489 (raw)."""
import hashlib
import hmac
from Crypto.Cipher import AES
import struct

pw = b"this-is-a-really-long-password-you-will-not-guess-it-easily"
salt_x = bytes.fromhex("60cf7473ce0a6a88")  # xor-uniform
salt = bytes.fromhex("ea45fef94480e002")    # raw
verify_x = bytes.fromhex("8e03")
verify = bytes.fromhex("0489")
ct_x = bytes.fromhex("63f9bdb95ac3ccc9184bf2233c6ad6a2cdd5f494dae956")
ct = bytes.fromhex("e9733733d049464392c178a9b6e05c28475f7e1e5063dc")
mac_x = bytes.fromhex("504b01023f0333030100")
mac = bytes.fromhex("dac18b88b589b9898b8a")  # mac_x XOR 0x8A

filename = b"LQrzcQkpzrvBfEcXEpAdqqucVbYa"

# Strategy: generate keystream from a KDF, try AES-CTR/CBC/CFB/OFB,
# require the verify to match (some KDFs use bytes [-2:] or [0:2] of derived output as verify)

# pyzipper standard: PBKDF2-HMAC-SHA1(pw, salt, 1000, 16+16+2) -> aes_key | hmac_key | verify

def test_kdf(name, derive_bytes, n_test_bytes=34, salt_to_use=salt_x, ct_to_use=ct_x, verify_to_use=verify_x):
    """derive_bytes(salt) returns N bytes; we look for 2-byte verify match."""
    out = derive_bytes(salt_to_use)
    # Test verify at end (standard pyzipper position)
    if out[32:34] == verify_to_use:
        print(f"  VERIFY MATCH (pos 32:34): {name}")
        return out
    if out[16:18] == verify_to_use:
        print(f"  VERIFY MATCH (pos 16:18): {name}")
        return out
    if out[0:2] == verify_to_use:
        print(f"  VERIFY MATCH (pos 0:2): {name}")
        return out
    # Also test reversed verify (LE/BE)
    rev = verify_to_use[::-1]
    if out[32:34] == rev:
        print(f"  VERIFY MATCH (pos 32:34, reversed): {name}")
        return out
    if out[0:2] == rev:
        print(f"  VERIFY MATCH (pos 0:2, reversed): {name}")
        return out
    return None

# 1) Custom: iterated sha256 of pw concatenated with iteration index
def kdf_iter_sha256_counter(s, iters=1000):
    state = pw + s
    for i in range(iters):
        state = hashlib.sha256(state).digest()
    return state

# 2) Iterated sha1 with salt prepended
def kdf_iter_sha1_pre_salt(s, iters=1000):
    state = s + pw
    for i in range(iters):
        state = hashlib.sha1(state).digest()
    return state * 2  # pad

# 3) Direct PBKDF2 with SHA-256
def pbkdf2_sha256_n(s, iters):
    return hashlib.pbkdf2_hmac('sha256', pw, s, iters, 34)

# 4) PBKDF2 with SHA-512
def pbkdf2_sha512_n(s, iters):
    return hashlib.pbkdf2_hmac('sha512', pw, s, iters, 34)

# 5) Custom: scrypt-like simple xor-cycle
def kdf_repeat_xor(s, iters=1):
    state = pw + s
    for _ in range(iters):
        h = hashlib.sha256(state).digest()
        state = bytes(a ^ b for a, b in zip(state.ljust(32, b'\x00')[:32], h))
    return state * 2

# 6) HKDF-Expand-only
def kdf_hkdf(s, info=b''):
    from cryptography.hazmat.primitives.kdf.hkdf import HKDF
    from cryptography.hazmat.primitives import hashes
    return HKDF(algorithm=hashes.SHA256(), length=34, salt=s, info=info).derive(pw)

# Massive grid search
print("Testing custom KDFs for verify match (XOR-uniform salt)...")
candidates_to_test = [
    ("pbkdf2_sha256_1000", lambda s: pbkdf2_sha256_n(s, 1000)),
    ("pbkdf2_sha512_1000", lambda s: pbkdf2_sha512_n(s, 1000)),
    ("iter_sha256_1000", lambda s: kdf_iter_sha256_counter(s, 1000)),
    ("iter_sha1_pre_salt_1000", lambda s: kdf_iter_sha1_pre_salt(s, 1000)),
]

for name, fn in candidates_to_test:
    test_kdf(name, fn)

# Now try a VAST list of simple "derive 34 bytes" functions
print("\nBrute searching many simple KDFs...")
import time
start = time.time()

# Variants: H(pw + salt + counter) chained
def gen_kdf_variants():
    for h_name in ['sha1', 'sha256', 'sha512', 'md5', 'sha3_256', 'sha3_512',
                   'blake2b', 'blake2s', 'sha384', 'sha224', 'ripemd160']:
        for iters in [1, 10, 100, 256, 512, 1000, 4096, 10000]:
            for order in ['pw+salt', 'salt+pw', 'pw+salt+pw', 'salt+pw+salt']:
                for use_counter in [False, True]:
                    yield (h_name, iters, order, use_counter)

count = 0
matches = []
for (h_name, iters, order, use_counter) in gen_kdf_variants():
    count += 1
    if order == 'pw+salt':
        seed = pw + salt_x
    elif order == 'salt+pw':
        seed = salt_x + pw
    elif order == 'pw+salt+pw':
        seed = pw + salt_x + pw
    else:
        seed = salt_x + pw + salt_x
    state = seed
    for i in range(iters):
        if use_counter:
            state = hashlib.new(h_name, state + i.to_bytes(4, 'big')).digest()
        else:
            state = hashlib.new(h_name, state).digest()
    # Test verify at any 2-byte position
    for pos in range(len(state) - 1):
        if state[pos:pos+2] == verify_x:
            matches.append((h_name, iters, order, use_counter, pos, 'xor'))
        if state[pos:pos+2] == verify:
            matches.append((h_name, iters, order, use_counter, pos, 'raw'))

print(f"Tested {count} KDFs in {time.time()-start:.1f}s")
print(f"Matches found: {len(matches)}")
for m in matches[:30]:
    print(f"  {m}")
