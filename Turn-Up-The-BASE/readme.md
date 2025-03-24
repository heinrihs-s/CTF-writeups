# "Turn Up the Base" CTF Writeup

## Challenge Details
**Challenge Name:** Turn Up the Base
**Description:** "Patience pays off. When you get to the end, you'll surely understand."
**Files Provided:** data.txt

## Initial Analysis
When examining the challenge, I immediately noticed two key hints:
1. The title "Turn up the base" - a clever wordplay suggesting Base64 encoding
2. The description mentioning "getting to the end" - implying multiple layers of encoding

The challenge seemed to involve a file that had been repeatedly encoded with Base64, requiring multiple rounds of decoding to reach the final flag.

## Solution Approach
Based on the hints, I decided to write a Python script that would repeatedly decode the Base64-encoded content until it could no longer be decoded or the output stopped changing.

### The Python Script
```python
import base64

# Read the encoded data from file
with open('data.txt', 'r') as f:
    data = f.read().strip()

count = 1

while True:
    try:
        decoded_bytes = base64.b64decode(data)
        new_data = decoded_bytes.decode('utf-8')
        print(f"--- Layer {count} ---")
        print(new_data, "\n")
        
        # Check if the data has changed
        if new_data == data:
            # No change, so exit the loop
            break
            
        data = new_data
        count += 1
        
    except Exception as e:
        print("No further decoding possible.")
        print("Final output:")
        print(data)
        break
```

### Execution Results
After running the script, it went through multiple layers of decoding:

```
--- Layer 1 ---
[Base64 encoded text...]

... [many layers of decoding] ...

--- Layer 38 ---
Q1RGe0JlMXo2NF9GMHJfRDR5JH0=

--- Layer 39 ---
CTF{Be1z64_F0r_D4y$}
```

## The Flag
After 39 rounds of Base64 decoding, the final flag was revealed:
`CTF{Be1z64_F0r_D4y$}`

