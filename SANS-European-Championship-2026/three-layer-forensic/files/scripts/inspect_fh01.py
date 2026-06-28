"""Inspect fh01.zip and the GIF inside for any cipher hint."""
import zipfile

with open(r"C:\Users\Administrator\Documents\claude\sans\challenges\three_layer_forensic\artifacts\fh01.zip", "rb") as f:
    data = f.read()

print(f"fh01.zip size: {len(data)}")

# Show last 200 bytes
print(f"\nLast 200 bytes of fh01.zip:")
print(data[-200:].hex())

# Extract zip contents
import io
zf = zipfile.ZipFile(io.BytesIO(data))
for info in zf.infolist():
    print(f"{info.filename}: size={info.file_size}, csize={info.compress_size}, comment={info.comment!r}")
    print(f"  flag_bits={info.flag_bits}, compress_type={info.compress_type}, date_time={info.date_time}")
    print(f"  extra: {info.extra.hex()}")
    if info.comment:
        print(f"  comment: {info.comment!r}")

# Comment on the ZIP
print(f"\nfh01.zip comment: {zf.comment!r}")
