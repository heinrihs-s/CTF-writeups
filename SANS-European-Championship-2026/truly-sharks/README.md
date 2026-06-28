# Sharks

> Category: Truly Mixed / packet forensics. Event: SANS European Championship 2026.

This was a Wireshark challenge pretending to be about broken pictures. It was mostly about not trusting your first file extractor.

Flag:

```text
C4tch1ng_H0n3y_p0Ts_w1TH_a_Sh4rk!
```

## Challenge

We got a pcapng, and the prompt was basically "reconstruct files and find flag". Name was `Sharks`, so yeah Wireshark time.

Inside the capture there was a custom UDP file transfer thing. Not HTTP, not SMB, not anything nice. Just a small protocol on loopback.

## Protocol notes

After staring at the packets:

```text
client -> server: "get <filename>" padded to 58 bytes
server -> client: 4 byte little endian file size
client -> server: 8 byte little endian ACK sequence
server -> client: [8 byte sequence][2064 bytes data]
```

Files transferred:

```text
1.jpg
2.txt
3.eps
4.jpg
5.zip
```

At first I reassembled chunks and got broken files. JPGs only rendered the top part. Zip was truncated. EPS was fat and annoying. It looked like packet loss.

But then the dumb important part:

```text
same sequence numbers missing in every file
```

Random loss does not do that. Challenge authors do.

## Dead ends

I did normal pcap panic stuff:

```bash
tshark -r fx01.pcapng
binwalk 1.jpg
strings 2.txt | grep -i flag
exiftool 4.jpg
unzip 5.zip
```

`2.txt` was War of the Worlds text. That was bait or just filler. JPGs were damaged in a very "maybe stego" way. The ZIP could not inflate right.

I also got distracted by the EPS because PostScript can do funny stuff. It rendered, but that also was not the straight win.

## The clue

The client ACK packets were tiny. Everyone always ignores ACK-looking packets because "they are just sequence numbers". That was the mistake.

Those 8 bytes were not just boring. The missing chunk pattern and the ACK stream were the thing to inspect, not the corrupted files themselves.

The quick check was to dump 8 byte UDP payloads:

```bash
tshark -r fx01.pcapng -Y "udp.length == 16" \
  -T fields -e frame.number -e udp.srcport -e udp.dstport -e udp.payload
```

Then decode the non-zero high bytes from the ACKs. The important idea was:

```python
payload = bytes.fromhex(hex_payload.replace(":", ""))
seq = int.from_bytes(payload[:4], "little")
covert = payload[4:]
```

Those "unused" bytes were not unused. Classic.

## Why it worked

The server used a file transfer protocol where client packets looked like boring ACKs. But CTF packet captures love hiding data in "metadata" fields: sequence gaps, checksums, timestamps, padding, high bytes, etc.

The visible files were all damaged in the same way so I would waste time trying to repair JPEG/ZIP data. The actual flag was in the control channel.

Wireshark lesson: if data is broken in a too-perfect pattern, look at the protocol around it. The missing chunks are sometimes just arrows pointing at the covert channel.
