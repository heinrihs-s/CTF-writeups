# 3 Layer Forensic

> Category: Truly Mixed / Forensics. Event: SANS European Championship 2026.

This one was one of them "simple file, surely 5 min" challenges. Of course it was not 5 min, it became zip archaeology and byte bullying.

## Challenge

We got a zip called `fh01.zip`. Inside was a GIF-ish thing. The brief basically said download files and find the flag. Very helpful, thanks.

The accepted flag ended up being:

```text
Flag: emBedDedX0R-01118
```

## Files

I added the real bits in [files/](files/), so this is not just story time.

- [files/MANIFEST.md](files/MANIFEST.md) has the full list
- `files/original/` has the prompt and flag
- `files/artifacts/` has `fh01.zip`, `flag.gif`, the XOR trailer, fixed zip, and one extracted frame
- `files/scripts/` has the messy solve scripts that got me there

## First look

First move was boring:

```bash
file fh01.zip
unzip fh01.zip
file flag.gif
```

The image looked like a normal enough GIF, so first I thought "stego in frames maybe". I poked at frames, trailers, ZIP signatures, all the usual trash.

The important thing was the GIF terminator byte. GIF ends with `0x3b`. After that, there was more bytes. That is always sus, because after the trailer byte the parser is done, but the file can still have junk appended.

## Where I went wrong

I saw bytes that looked like a WinZip AES / pyzipper thing and immediately ran into the wall:

```python
import io, pyzipper

with pyzipper.AESZipFile(io.BytesIO(zip_bytes)) as zf:
    zf.setpassword(b"this-is-a-really-long-password-you-will-not-guess-it-easily")
    print(zf.read(zf.namelist()[0]))
```

At one point the notes had like 30 scripts trying PBKDF2, SHA1, SHA256, weird salt offsets, AES CTR/CBC/OFB, whatever. Very professional way to say "i am lost".

The funny bit: there was a password in the data, and that made the fake AES path feel real enough. The password was:

```text
this-is-a-really-long-password-you-will-not-guess-it-easily
```

So yeah, I trusted the bait too hard.

## The actual trick

The post-GIF trailer was XORed with `0x8a`.

After unmasking, it looked like a little ZIP-ish object. But the right mental model was not "let pyzipper do magic". The challenge was more hand-made. The appended area had the encrypted-ish blob and the password, and the real plaintext could be recovered after undoing the XOR and not overthinking the ZIP metadata.

The key observation:

```python
trailer = bytes(b ^ 0x8a for b in gif[885577:])
```

Offset matters here. Earlier I had a slightly wrong offset and that made everything look cursed. Correct offset, less cursed.

## Solve sketch

This is the cleaned version of what the solve did:

```python
import io
import pyzipper

with open("flag.gif", "rb") as f:
    gif = f.read()

# GIF trailer 0x3b is at 885576, so everything after it is extra stuff.
extra = gif[885577:]
zip_bytes = bytes(b ^ 0x8a for b in extra)

# Trim at ZIP end-of-central-directory.
end = zip_bytes.find(b"PK\x05\x06")
zip_bytes = zip_bytes[:end + 22]

password = b"this-is-a-really-long-password-you-will-not-guess-it-easily"

with pyzipper.AESZipFile(io.BytesIO(zip_bytes)) as zf:
    zf.setpassword(password)
    print(zf.read(zf.namelist()[0]).decode())
```

Output:

```text
Flag: emBedDedX0R-01118
```

## Why it worked

GIF parsers stop at the trailer byte. Anything appended after that can be invisible to normal viewers but still be perfect for hiding data. Here the extra data was just lightly masked with XOR, so it wasnt encrypted in any serious way.

The security take-away is basic but still funny: file formats allow trailing garbage more often than people remember. If you stop at `file` and a viewer, you miss half the party.

Also if a challenge gives you a "obvious AES zip" path, maybe ask if it is bait before you spend one hour making PBKDF2 sad.
