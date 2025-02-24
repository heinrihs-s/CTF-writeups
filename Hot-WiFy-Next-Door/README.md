# Hot WiFy Next Door - WiFi Cracking Challenge

## Challenge Overview
**Category:** WiFi Security  
**Difficulty:** Easy  
**Points:** 100  
**Files Provided:** zodiak_wify_ctf-01.cap

## TL;DR
1. Cracked WiFi password from capture file using aircrack-ng
2. Used password to decrypt traffic in Wireshark
3. Found flag in HTTP traffic

## Challenge Description
We were provided with a Wireshark capture file containing WiFi traffic from a network named "Hot WiFy Next Door". The challenge involved cracking the network password and analyzing the encrypted traffic to find the hidden flag.

## Required Tools
- Wireshark
- aircrack-ng
- rockyou.txt wordlist

## Detailed Solution

### Step 1: Initial Analysis
Opening the capture file in Wireshark showed typical WiFi traffic including:
- Beacon frames
- Probe requests/responses
- WPA handshake packets

### Step 2: Password Cracking
Using aircrack-ng with the rockyou wordlist:

```bash
aircrack-ng -w /path/to/rockyou.txt zodiak_wify_ctf-01.cap
```

After about 26,000 attempts, we got our password:
```
[00:00:01] 26171/10303727 keys tested (35330.61 k/s)
Time left: 4 minutes, 50 seconds                           0.25%

                    KEY FOUND! [ alfaromeo ]

Master Key     : 25 DC B7 BE 05 71 A8 9E BC 57 1F 2F 01 25 5F AE
                4B 22 36 B8 8E E7 B7 4A 45 E7 97 CA 73 E6 29 7C
```

### Step 3: Traffic Decryption
With the password in hand, we configured Wireshark to decrypt the traffic:

1. Navigate to Edit → Preferences → Protocols → IEEE 802.11
2. Enable decryption
3. Add decryption key:
   - Password: alfaromeo
   - SSID: Hot WiFy Next Door

### Step 4: Finding the Flag
After enabling decryption, we filtered for HTTP traffic and found our flag:

**Flag: ctf{WiFi-is-HOT}**

## Key Takeaways
- WPA2 networks can be easily cracked if a weak password is used
- Captured handshakes are crucial for WiFi password cracking
- Wireshark's decryption capabilities are powerful for analyzing encrypted traffic

## Files
- [zodiak_wify_ctf-01.cap](./zodiak_wify_ctf-01.cap) - Original capture file

## References
- [Wireshark IEEE 802.11 Decryption Guide](https://wiki.wireshark.org/HowToDecrypt802.11)
- [aircrack-ng Documentation](https://www.aircrack-ng.org/doku.php?id=documentation)

---
*Created: February 24, 2025*  
