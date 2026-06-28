"""Look for steganographic content in GIF: comment blocks, application extensions, etc."""

with open(r"C:\Users\Administrator\Documents\claude\sans\challenges\three_layer_forensic\artifacts\flag.gif", "rb") as f:
    data = f.read()

print(f"Total GIF size: {len(data)}")

# GIF89a structure: HEADER + LSD + GCT? + (extensions/image blocks) + 0x3B trailer
# Parse the GIF structure

assert data[:6] in (b"GIF87a", b"GIF89a")
print(f"Header: {data[:6]}")

# LSD (Logical Screen Descriptor)
import struct
lsd = data[6:13]
width, height, packed, bg, ar = struct.unpack('<HHBBB', lsd)
print(f"Screen: {width}x{height} packed=0x{packed:02x} bg={bg} ar={ar}")
gct_flag = (packed >> 7) & 1
gct_size = (packed & 7)
print(f"GCT flag: {gct_flag}, GCT size bits: {gct_size}")

pos = 13
if gct_flag:
    gct_bytes = 3 * (1 << (gct_size + 1))
    print(f"GCT bytes: {gct_bytes}")
    pos += gct_bytes

# Now parse blocks
extensions = []
images = []
while pos < len(data):
    b = data[pos]
    if b == 0x3B:
        print(f"Trailer 0x3B at {pos}")
        break
    elif b == 0x21:
        # Extension
        label = data[pos+1]
        sub_pos = pos + 2
        sub_blocks = []
        while True:
            sz = data[sub_pos]
            if sz == 0:
                sub_pos += 1
                break
            sub_blocks.append(data[sub_pos+1:sub_pos+1+sz])
            sub_pos += 1 + sz
        ext_data = b''.join(sub_blocks)
        ext_type = {
            0xF9: 'Graphic Control',
            0xFE: 'Comment',
            0x01: 'Plain Text',
            0xFF: 'Application',
        }.get(label, f'Unknown 0x{label:02x}')
        print(f"  Extension at {pos}: type=0x{label:02x} ({ext_type}), sub-blocks total {len(ext_data)} bytes")
        if label == 0xFE:  # Comment
            print(f"    COMMENT: {ext_data!r}")
        elif label == 0xFF:  # Application
            print(f"    Application: header={sub_blocks[0]!r}, data={b''.join(sub_blocks[1:])!r}")
        extensions.append((label, ext_data))
        pos = sub_pos
    elif b == 0x2C:
        # Image descriptor
        img_left, img_top, img_w, img_h, img_packed = struct.unpack('<HHHHB', data[pos+1:pos+10])
        lct_flag = (img_packed >> 7) & 1
        lct_size = img_packed & 7
        sub_pos = pos + 10
        if lct_flag:
            lct_bytes = 3 * (1 << (lct_size + 1))
            sub_pos += lct_bytes
        # LZW minimum code size
        lzw_min = data[sub_pos]
        sub_pos += 1
        # Image data sub-blocks
        sub_blocks = []
        while True:
            sz = data[sub_pos]
            if sz == 0:
                sub_pos += 1
                break
            sub_blocks.append(data[sub_pos+1:sub_pos+1+sz])
            sub_pos += 1 + sz
        img_data = b''.join(sub_blocks)
        images.append((pos, img_left, img_top, img_w, img_h, len(img_data)))
        pos = sub_pos
    else:
        print(f"Unknown byte 0x{b:02x} at {pos}, stopping")
        break

print(f"\nTotal extensions: {len(extensions)}")
print(f"Total images: {len(images)}")
print(f"\nLast image ends at {pos}, file size {len(data)}")
print(f"Trailer offset: {pos}, expecting 0x3B = {data[pos]:#04x}")

# Check after trailer
trailer = data[pos+1:]
print(f"\nBytes after trailer (length {len(trailer)}): {trailer[:50].hex()}...")
