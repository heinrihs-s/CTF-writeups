# Sharks - up to 400pts (Truly Mixed) - PARTIAL

**URL:** https://ranges.io/event/bf72b90c-2149-11f1-9ad7-316439613462/challenge/49ec22d0-56b0-11f1-8e0f-646231653833
**Status:** PARTIAL - extracted 5 files but JPEGs corrupted

## Prompt
Download https://1-files.bootupctf.net/fx01.zip; pcap inside.

## What's in fx01.pcapng (11.7MB)
Custom UDP file-transfer protocol port 5555<->40485. Format:
- Client: `get <filename>` 58 bytes, then 8-byte ACK per chunk
- Server: 4-byte size then chunks `[8-byte LE seq][2064 data]`
- Per-file: first 8 bytes of reassembled is `00 08 00 00 00 00 00 00` then file bytes

5 files transferred (1.jpg 1.25MB JPEG, 2.txt 360KB War of Worlds Gutenberg, 3.eps 5.2MB Adobe Illustrator, 4.jpg 1.77MB JPEG, 5.zip 554KB containing 5.jpg)

**Same seqs missing across ALL files** (seq 4, 248-260, ...) - not random packet loss, looks intentional.

## Tried
tshark + Python reassembly, binwalk, exiftool, steghide info, strings, JPEG EOI carve, 5.zip partial deflate (fails with invalid bit length repeat).

## Next time
- Eyeball 1.jpg / 4.jpg in Photo Viewer - flag might be visible in image
- Try jpegrescue / recover_jpeg
- Investigate other pcap channels: sigcomp, DCERPC, pathport (all had activity)
- Look for hidden payload in 40485->5555 small ACK packets

VPS: /root/ctf/truly_sharks/work/  Local: artifacts/
