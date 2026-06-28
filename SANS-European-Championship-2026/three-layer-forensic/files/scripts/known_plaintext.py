"""For each candidate plaintext, compute keystream = pt XOR ct, then test:
- Could this keystream be the output of AES-128 in CTR/OFB mode with a derived key?
- If yes, derive what key produces this output."""
import hashlib
import hmac
from Crypto.Cipher import AES
from Crypto.Util import Counter

pw = b"this-is-a-really-long-password-you-will-not-guess-it-easily"
salt_x = bytes.fromhex("60cf7473ce0a6a88")
salt = bytes.fromhex("ea45fef94480e002")
verify = bytes.fromhex("0489")
verify_x = bytes.fromhex("8e03")
ct = bytes.fromhex("e9733733d049464392c178a9b6e05c28475f7e1e5063dc")
ct_x = bytes.fromhex("63f9bdb95ac3ccc9184bf2233c6ad6a2cdd5f494dae956")
filename = b"LQrzcQkpzrvBfEcXEpAdqqucVbYa"

# Massive candidate list
candidates = [
    # HACKERS
    b"crash-override-12345678", b"crash-override-acid-bur",
    b"mess-with-best-die-rest", b"hack-the-planet-1995!!_",
    b"hack-the-gibson-prophet", b"dade-murphy-zero-cool-X",
    b"hack-the-planet-rules!_", b"mess_with_the_best_die_",
    b"hackers-1995-crash-over", b"crash_override_hack1995",
    b"hack-the-planet-12345!_", b"i_think_im_in_love_dude",
    b"zerocool-and-acid-burn!", b"this-is-our-world-now!_",
    # Matrix
    b"follow-the-white-rabbit", b"there-is-no-spoon-said!",
    b"wake-up-neo-the-matrix1", b"red-pill-blue-pill-cypr",
    b"do-not-bend-the-spoon-1", b"morpheus-says-neo-is-on",
    # Generic CTF
    b"flag-is-something-here_", b"this-is-the-secret-text",
    b"i-am-the-flag-do-not-rm", b"the-flag-must-be-found1",
    b"flag-of-23-bytes-here!!", b"the-secret-of-life-23bx",
    b"hack-the-planet-Murphy!", b"plague-is-the-bad-guy!_",
    # Variants with extra char
    b"crashoverride-acidburn1", b"thisistheflagdontreadit",
    # All same char (sanity check)
    b"aaaaaaaaaaaaaaaaaaaaaaa",
    b"AAAAAAAAAAAAAAAAAAAAAAA",
    b"flag{follow_the_rabbit}",
    b"flag{crash_override_yo}",
    b"flag{hack_the_planet_y}",
    b"flag{this_is_my_secret}",
    b"flag-this-was-it-y0u-wo",
    b"3-layer-forensic-FLAG1!",
    b"three_layer_forensic_OK",
    b"hack-the-planet-rules!!",
    b"the-flag-is-not-here!!!",
]

def is_printable(s, threshold=22):
    return sum(1 for b in s if 32 <= b < 127) >= threshold

# For each candidate, compute keystream and see if it has structure
results = []
for cand in candidates:
    if len(cand) != 23: continue
    for ct_label, ct_v in [("raw", ct), ("xor", ct_x)]:
        ks = bytes(a ^ b for a, b in zip(cand, ct_v))
        # Test: is ks the AES encryption of counter 0 (or 1) using some key?
        # Try ALL keys derived from common KDFs
        for h_name in ['md5', 'sha1', 'sha256', 'sha512']:
            for inp_name, inp in [
                ('pw', pw),
                ('pw+salt', pw + (salt if ct_label == 'raw' else salt_x)),
                ('salt+pw', (salt if ct_label == 'raw' else salt_x) + pw),
                ('filename', filename),
                ('filename+pw', filename + pw),
                ('pw+filename', pw + filename),
            ]:
                try:
                    k = hashlib.new(h_name, inp).digest()
                    # Try AES-CTR with various counters
                    for klen in [16, 24, 32]:
                        if len(k) < klen: continue
                        for ctr_init in [0, 1, 2]:
                            for endian in ['big', 'little']:
                                try:
                                    if endian == 'big':
                                        counter = Counter.new(128, initial_value=ctr_init, little_endian=False)
                                    else:
                                        counter = Counter.new(128, initial_value=ctr_init, little_endian=True)
                                    cipher = AES.new(k[:klen], AES.MODE_CTR, counter=counter)
                                    generated_ks = cipher.encrypt(b'\x00' * 32)
                                    if generated_ks[:23] == ks:
                                        print(f"!!! MATCH: cand={cand!r} ct_label={ct_label}, key=AES-{klen*8} {h_name}({inp_name}), CTR init={ctr_init} endian={endian}")
                                        results.append((cand, ct_label, h_name, inp_name, klen, ctr_init, endian))
                                except: pass

                    # AES-ECB on counter blocks
                    try:
                        cipher = AES.new(k[:16], AES.MODE_ECB)
                        block0 = cipher.encrypt(bytes(16))
                        block1 = cipher.encrypt(b'\x00'*15 + b'\x01')
                        ks_test = (block0 + block1)[:23]
                        if ks_test == ks:
                            print(f"!!! AES-ECB MATCH: cand={cand!r} key={h_name}({inp_name})")
                            results.append((cand, ct_label, h_name, inp_name, 'ECB'))
                    except: pass

                    # AES-OFB with various IVs
                    for iv_name, iv in [
                        ('zero', b'\x00'*16),
                        ('salt+pad', (salt if ct_label == 'raw' else salt_x) + b'\x00'*8),
                        ('verify+pad', (verify if ct_label == 'raw' else verify_x) + b'\x00'*14),
                        ('one', b'\x00'*15 + b'\x01'),
                    ]:
                        try:
                            cipher = AES.new(k[:16], AES.MODE_OFB, iv=iv)
                            ks_test = cipher.encrypt(b'\x00' * 32)[:23]
                            if ks_test == ks:
                                print(f"!!! AES-OFB MATCH: cand={cand!r} key={h_name}({inp_name}) iv={iv_name}")
                                results.append((cand, ct_label, h_name, inp_name, 'OFB', iv_name))
                        except: pass

                    # AES-CFB
                    for iv_name, iv in [
                        ('zero', b'\x00'*16),
                        ('salt+pad', (salt if ct_label == 'raw' else salt_x) + b'\x00'*8),
                    ]:
                        try:
                            cipher = AES.new(k[:16], AES.MODE_CFB, iv=iv, segment_size=128)
                            # CFB decryption: ct ^ AES(IV)
                            ks_test = AES.new(k[:16], AES.MODE_ECB).encrypt(iv)[:16] + AES.new(k[:16], AES.MODE_ECB).encrypt(ct_v[:16])[:16]
                            # Actually CFB decrypt directly
                            pt = cipher.decrypt(ct_v.ljust(32, b'\x00'))[:23]
                            if pt == cand:
                                print(f"!!! AES-CFB MATCH: cand={cand!r} key={h_name}({inp_name}) iv={iv_name}")
                                results.append((cand, ct_label, h_name, inp_name, 'CFB', iv_name))
                        except: pass

                except: pass

print(f"\nTotal: {len(results)} matches")
