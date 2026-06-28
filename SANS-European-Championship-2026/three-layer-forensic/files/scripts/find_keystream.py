"""For pt=follow-the-white-rabbit, ks=8f1c5b5fbf3e6b37faa455dede89284d6a2d1f7c320aa8.
Find what input/algorithm produces this keystream."""
import hashlib
import hmac

pw = b"this-is-a-really-long-password-you-will-not-guess-it-easily"
salt_x = bytes.fromhex("60cf7473ce0a6a88")
salt = bytes.fromhex("ea45fef94480e002")
verify_x = bytes.fromhex("8e03")
verify = bytes.fromhex("0489")
ct = bytes.fromhex("e9733733d049464392c178a9b6e05c28475f7e1e5063dc")
target_ks = bytes.fromhex("8f1c5b5fbf3e6b37faa455dede89284d6a2d1f7c320aa8")
filename = b"LQrzcQkpzrvBfEcXEpAdqqucVbYa"

print(f"Target keystream (23 bytes): {target_ks.hex()}")
print(f"  Including next 2 bytes (would be verify): {target_ks.hex()}{verify.hex()}")
print(f"  Full target [25 bytes]: {target_ks.hex() + verify.hex()}")

# Generate huge list of hash outputs and check if any match
print("\n--- Searching for hash that produces target_ks ---")
inputs = [
    ('pw', pw),
    ('salt', salt),
    ('salt_x', salt_x),
    ('verify', verify),
    ('verify_x', verify_x),
    ('filename', filename),
    ('pw+salt', pw + salt),
    ('pw+salt_x', pw + salt_x),
    ('salt+pw', salt + pw),
    ('salt_x+pw', salt_x + pw),
    ('pw+filename', pw + filename),
    ('filename+pw', filename + pw),
    ('pw+verify', pw + verify),
    ('verify+pw', verify + pw),
    ('pw+verify_x', pw + verify_x),
    ('verify_x+pw', verify_x + pw),
    ('pw+salt+verify', pw + salt + verify),
    ('pw+salt_x+verify_x', pw + salt_x + verify_x),
    ('salt+pw+salt', salt + pw + salt),
    ('salt_x+pw+salt_x', salt_x + pw + salt_x),
]

hashes_to_try = ['md5', 'sha1', 'sha256', 'sha512', 'sha384', 'sha224',
                 'sha3_256', 'sha3_512', 'sha3_384', 'sha3_224',
                 'blake2b', 'blake2s',
                 'shake_128', 'shake_256',  # variable length
                 'ripemd160']

for h_name in hashes_to_try:
    for inp_name, inp in inputs:
        try:
            if h_name in ['shake_128', 'shake_256']:
                d = hashlib.new(h_name, inp).digest(64)
            else:
                d = hashlib.new(h_name, inp).digest()
            # Check at every offset
            for off in range(len(d) - 22):
                if d[off:off+23] == target_ks:
                    print(f"!!! HASH MATCH: {h_name}({inp_name}) at offset {off}: {d.hex()}")
        except Exception as e:
            pass

# PBKDF2 variants
print("\n--- PBKDF2 ---")
for h_name in ['sha1', 'sha256', 'sha512', 'sha3_256']:
    for iters in [1, 2, 4, 8, 16, 32, 64, 100, 128, 200, 256, 500, 512, 1000, 1024, 2048, 4096, 8192, 10000, 16384, 32768, 65536, 100000]:
        for s_label, s in [('xor', salt_x), ('raw', salt)]:
            try:
                d = hashlib.pbkdf2_hmac(h_name, pw, s, iters, 64)
                for off in range(len(d) - 22):
                    if d[off:off+23] == target_ks:
                        print(f"!!! PBKDF2-{h_name} iter={iters} salt_{s_label} offset={off}: {d.hex()}")
            except: pass

# HMAC variants
print("\n--- HMAC ---")
for h_name in ['md5', 'sha1', 'sha256', 'sha512']:
    for k_name, k in inputs[:8]:
        for m_name, m in inputs[:8]:
            try:
                hm = hmac.new(k, m, h_name).digest()
                if hm[:23] == target_ks:
                    print(f"!!! HMAC-{h_name}({k_name}, {m_name})[:23] = target_ks")
                if hm[-23:] == target_ks:
                    print(f"!!! HMAC-{h_name}({k_name}, {m_name})[-23:] = target_ks")
            except: pass

# Iterated hash with counter
print("\n--- Iterated hash with counter ---")
for h_name in ['md5', 'sha1', 'sha256', 'sha512', 'blake2b', 'blake2s']:
    for inp_pattern in ['pw+i', 'pw+salt+i', 'salt+pw+i', 'pw+salt_x+i', 'salt_x+pw+i']:
        for tag_len in [1, 2, 4, 8]:
            for byteorder in ['big', 'little']:
                ks = b''
                for i in range(64):
                    if 'pw+salt+i' in inp_pattern:
                        seed = pw + salt + i.to_bytes(tag_len, byteorder)
                    elif 'salt+pw+i' in inp_pattern:
                        seed = salt + pw + i.to_bytes(tag_len, byteorder)
                    elif 'pw+salt_x+i' in inp_pattern:
                        seed = pw + salt_x + i.to_bytes(tag_len, byteorder)
                    elif 'salt_x+pw+i' in inp_pattern:
                        seed = salt_x + pw + i.to_bytes(tag_len, byteorder)
                    else:  # pw+i
                        seed = pw + i.to_bytes(tag_len, byteorder)
                    ks += hashlib.new(h_name, seed).digest()
                    if len(ks) >= 50:
                        break
                if ks[:23] == target_ks:
                    print(f"!!! Iterated MATCH: {h_name}({inp_pattern}, taglen={tag_len}, {byteorder})")
                # Sliding window
                for off in range(len(ks) - 22):
                    if ks[off:off+23] == target_ks:
                        print(f"!!! Iterated MATCH (offset {off}): {h_name}({inp_pattern}, taglen={tag_len}, {byteorder})")

# Special: Maybe it's pyzipper with KDF iter parameter we missed?
# pyzipper standard: dklen = 2*klen + 2
# verify bytes appear at positions 32-34 of derivation
# But target_ks is the keystream USED for XOR (separate from verify)
# Maybe target_ks IS the first 23 bytes of an AES-CTR keystream

# Compute the AES-128 CTR keystream from pyzipper KDF:
# key = pbkdf2_hmac(sha1, pw, salt, 1000, 34)[0:16]
# IV in pyzipper-AES = counter, starts at 1 (NOT 0!)
from Crypto.Cipher import AES
from Crypto.Util import Counter

for h_name in ['sha1', 'sha256', 'sha512', 'sha384', 'sha3_256', 'sha3_512']:
    for iters in [1, 100, 1000, 10000, 100000]:
        for s_label, s in [('raw', salt), ('xor', salt_x)]:
            for klen in [16, 24, 32]:
                try:
                    dk = hashlib.pbkdf2_hmac(h_name, pw, s, iters, klen*2+2)
                    aes_key = dk[:klen]
                    # WinZip-AES uses big-endian counter starting at 1
                    for initial_val in [0, 1]:
                        ctr = Counter.new(128, initial_value=initial_val, little_endian=False)
                        cipher = AES.new(aes_key, AES.MODE_CTR, counter=ctr)
                        ks = cipher.encrypt(b'\x00' * 32)
                        for off in range(10):
                            if ks[off:off+23] == target_ks:
                                print(f"!!! AES-CTR MATCH: h={h_name} iter={iters} salt={s_label} klen={klen} initial={initial_val} offset={off}")

                        # Try with LE counter
                        ctr_le = Counter.new(128, initial_value=initial_val, little_endian=True)
                        cipher_le = AES.new(aes_key, AES.MODE_CTR, counter=ctr_le)
                        ks_le = cipher_le.encrypt(b'\x00' * 32)
                        for off in range(10):
                            if ks_le[off:off+23] == target_ks:
                                print(f"!!! AES-CTR(LE) MATCH: h={h_name} iter={iters} salt={s_label} klen={klen} initial={initial_val} offset={off}")
                except: pass
