# Outside-expert consult: Sharks (SANS CTF, Truly Mixed, 400pts)

You are an outside expert. I am stuck. The challenge brief and platform say:

> Title: Sharks
> Category: Truly Mixed (400pts)
> Brief: "We've captured this Wireshark traffic, can you reconstruct the files and find the flag?"
> Artifact: `artifacts/fx01.pcapng` (~5.7MB)

## What I've figured out (verified)

The pcap contains a custom UDP file-transfer protocol on the loopback between two ephemeral ports (observed: client ↔ server, ports `5555` and `40485`).

**Protocol (reverse-engineered from the pcap):**
- Client → Server: 58-byte UDP packet `b"get <filename>\x00..."` (filename padded with NULs).
- Server → Client: 4-byte little-endian "file size" reply.
- Client → Server: 8-byte LE "ack sequence" packets, one per chunk.
- Server → Client: chunks of `[8-byte LE seq][2064 bytes data]`. Total per chunk = 2072 bytes (with UDP/IP headers in pcap framing).

**5 files transferred in this session:** `1.jpg`, `2.txt`, `3.eps`, `4.jpg`, `5.zip`. Extracted them with a tshark-based Python script (`/root/ctf/truly_sharks/work/extract3.py` on the VPS, also copied locally to `artifacts/`).

## The block

**All 5 files are missing the SAME sequence numbers: 4, 248, 249, ..., 260** (and a few more identical seqs across all files). This is NOT random packet loss — the pattern is identical across every transfer, which strongly suggests the dropped packets are *intentional* (the challenge is hiding the flag in the packets the protocol "loses", or there is a second hidden channel).

- `1.jpg`, `4.jpg` render only the top ~15% of each image (chameleon on grass / dimly visible scene); the rest is corrupted gray noise. No visible flag in the rendered portion.
- `2.txt` = H. G. Wells "War of the Worlds" Gutenberg text. Skimmed for flag-like markers (flag{, FLAG{, sans, bootup, _, hyphen-digit patterns) — nothing.
- `3.eps` = Adobe Illustrator EPS. Mostly binary stream; haven't fully PostScript-rendered it yet.
- `5.zip` = truncated; deflate fails partway through (~19KB short on compressed data).

## What I need from you

Look at `artifacts/fx01.pcapng` (read-only access). Open questions:

1. **Are the "missing" seqs (4, 248-260, etc.) actually present in the pcap as packets that my extractor isn't recognizing?** Possibilities:
   - They're sent with a different source/dest port, a malformed header, or out-of-band (e.g. ICMP, raw IP, or a separate UDP flow).
   - The "ack" packets from the client might themselves carry payload bytes I'm ignoring.
   - There's a third party in the conversation (a 3-way capture).
2. **Is there a covert channel in the timing, IP IDs, TTLs, UDP checksums, or sequence-number metadata?**
3. **The challenge name "Sharks" + the corrupted-then-truncated pattern feels deliberate. Is there a steganographic encoding in the *image data we DO have* (LSB of the JPEG bytes that did arrive, EOI/SOI markers, comment segments, etc.)?**
4. **Or is the flag in the EPS file (3.eps) — and what's the right way to render/parse a PostScript program that was *intended* to print a flag?**
5. **The 5.zip truncation: is there enough of its central directory to know the filename inside, and could 5.zip's content be retrievable via partial decompression of the present blocks?**

If you can either (a) name the trick or (b) write a script that recovers the flag from the existing pcap + extracted artifacts, that's the win. Read-only sandbox is fine — I'll run any code you propose.

Print your answer concretely: what is the flag (or what is the exact next command/script to run that yields it). Don't ask follow-up questions unless absolutely necessary; make your best guess and explain why.

## File index

```
artifacts/
  fx01.pcapng       — original capture (5.7MB)
  1.jpg             — 1st file from protocol (corrupted, partial render)
  2.txt             — War of the Worlds text
  3.eps             — Adobe Illustrator EPS
  4.jpg             — 4th file (also corrupted, similar artifact pattern as 1.jpg)
  5.zip             — truncated zip; partial deflate
```

Constraints: don't submit guesses to the platform on my behalf — just print the flag candidate and the chain of reasoning that produced it.
