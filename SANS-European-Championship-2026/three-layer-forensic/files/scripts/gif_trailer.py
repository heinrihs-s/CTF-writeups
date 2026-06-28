"""Extract the GIF trailer and identify what's been XORed."""

with open(r"C:\Users\Administrator\Documents\claude\sans\challenges\three_layer_forensic\artifacts\flag.gif", "rb") as f:
    data = f.read()

print(f"GIF total size: {len(data)}")

# Find the GIF terminator (0x3B)
terminator_offset = data.rfind(b'\x3B')
print(f"Last 0x3B offset: {terminator_offset}")

# Look for the 0x3B that ends the proper GIF
# GIF89a structure ends with 0x3B trailer
# But the inner 0x3B might be inside data
# Find the LAST trailing 0x3B such that everything after is "extra" payload
# Actually use the known fact: trailer starts at offset 885655
trailer_start = 885655 + 1  # after the 0x3B byte
trailer = data[trailer_start:]
print(f"Trailer at offset {trailer_start}, length {len(trailer)}")

# Bytes 0..32 (33 bytes)
print(f"\nBytes 0..33 (AES blob): {trailer[:33].hex()}")
# Bytes 33..153 (CDR after XOR 0x8A)
print(f"\nBytes 33..153 (CDR, XOR'd): {trailer[33:154].hex()}")
print(f"Bytes 33..153 XOR 0x8A: {bytes(b ^ 0x8a for b in trailer[33:154]).hex()}")

# Bytes 154..175 (EOCD after XOR 0x8A)
print(f"\nBytes 154..176 (EOCD, XOR'd): {trailer[154:176].hex()}")
print(f"Bytes 154..176 XOR 0x8A: {bytes(b ^ 0x8a for b in trailer[154:176]).hex()}")

# Bytes 176..293 = password
print(f"\nBytes 176..294: {trailer[176:].hex()}")
# Decode as UTF-8, then convert each codepoint XOR 0x8A
decoded = trailer[176:].decode('utf-8')
pw_bytes = bytes(ord(c) ^ 0x8a for c in decoded)
print(f"Decoded password: {pw_bytes}")

# Compare: layer2.bin from the workspace
with open(r"C:\Users\Administrator\Documents\claude\sans\challenges\three_layer_forensic\artifacts\layer2.bin", "rb") as f:
    l2 = f.read()
print(f"\nlayer2.bin (176 bytes): {l2.hex()}")
print(f"First 33 bytes match trailer[:33] (raw)?  {l2[:33] == trailer[:33]}")
print(f"First 33 bytes match trailer[:33] XOR 0x8A?  {l2[:33] == bytes(b ^ 0x8a for b in trailer[:33])}")

# What about bytes 33+ ?
print(f"\nlayer2.bin[33:43]: {l2[33:43].hex()}")
print(f"trailer[33:43] raw: {trailer[33:43].hex()}")
print(f"trailer[33:43] XOR 0x8A: {bytes(b ^ 0x8a for b in trailer[33:43]).hex()}")
