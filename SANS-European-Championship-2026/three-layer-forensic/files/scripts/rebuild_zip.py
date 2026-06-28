"""Build a properly-structured pyzipper-AES ZIP and test if pyzipper can decrypt it."""
import struct
import io
import pyzipper

# Use the XOR-uniform values as the "real" encrypted blob
salt = bytes.fromhex("60cf7473ce0a6a88")
verify = bytes.fromhex("8e03")
ct = bytes.fromhex("63f9bdb95ac3ccc9184bf2233c6ad6a2cdd5f494dae956")
mac = bytes.fromhex("504b01023f0333030100")
pw = b"this-is-a-really-long-password-you-will-not-guess-it-easily"

# Build a complete LFH + AES blob + CDR + EOCD that pyzipper accepts
filename = b"LQrzcQkpzrvBfEcXEpAdqqucVbYa"
file_data = salt + verify + ct + mac

# Extra field: 0x9901 AES extra block - 11 bytes total
aes_extra = struct.pack('<HH', 0x9901, 7) + struct.pack('<H', 2) + b'AE' + bytes([1]) + struct.pack('<H', 0)

# LFH
lfh = b'PK\x03\x04'
lfh += struct.pack('<H', 51)  # version_needed (5.1 for AE-2)
lfh += struct.pack('<H', 1)   # gp flags (bit 0 = encrypted)
lfh += struct.pack('<H', 99)  # method = AES
lfh += struct.pack('<H', 0)   # mod time
lfh += struct.pack('<H', 0)   # mod date
lfh += struct.pack('<I', 0)   # crc (0 for AE-2)
lfh += struct.pack('<I', len(file_data))  # csize = 43
lfh += struct.pack('<I', 23)  # usize = 23
lfh += struct.pack('<H', len(filename))
lfh += struct.pack('<H', len(aes_extra))
lfh += filename
lfh += aes_extra

# CDR
cdr = b'PK\x01\x02'
cdr += struct.pack('<H', 51)  # version made by
cdr += struct.pack('<H', 51)  # version needed
cdr += struct.pack('<H', 1)   # gp flags
cdr += struct.pack('<H', 99)  # method
cdr += struct.pack('<H', 0)   # mod time
cdr += struct.pack('<H', 0)   # mod date
cdr += struct.pack('<I', 0)   # crc
cdr += struct.pack('<I', len(file_data))
cdr += struct.pack('<I', 23)
cdr += struct.pack('<H', len(filename))
cdr += struct.pack('<H', len(aes_extra))
cdr += struct.pack('<H', 0)   # comment len
cdr += struct.pack('<H', 0)   # disk num
cdr += struct.pack('<H', 0)   # internal attrs
cdr += struct.pack('<I', 0)   # external attrs
cdr += struct.pack('<I', 0)   # offset of LFH
cdr += filename
cdr += aes_extra

# EOCD
eocd = b'PK\x05\x06'
eocd += struct.pack('<H', 0)  # disk num
eocd += struct.pack('<H', 0)  # disk with cdr
eocd += struct.pack('<H', 1)  # entries on this disk
eocd += struct.pack('<H', 1)  # total entries
eocd += struct.pack('<I', len(cdr))  # cdr size
eocd += struct.pack('<I', len(lfh) + len(file_data))  # cdr offset
eocd += struct.pack('<H', 0)  # comment len

full_zip = lfh + file_data + cdr + eocd

# Write and try pyzipper
with open(r'C:\Users\Administrator\Documents\claude\sans\challenges\three_layer_forensic\rebuilt.zip', 'wb') as f:
    f.write(full_zip)

print(f"Rebuilt zip size: {len(full_zip)}")

# Now test pyzipper extraction
try:
    with pyzipper.AESZipFile(io.BytesIO(full_zip)) as zf:
        zf.setpassword(pw)
        for info in zf.infolist():
            try:
                data = zf.read(info)
                print(f"!!! SUCCESS: decrypted to {data!r}")
                break
            except Exception as e:
                print(f"Decrypt failure for {info.filename}: {type(e).__name__}: {e}")
except Exception as e:
    print(f"Read failure: {type(e).__name__}: {e}")
