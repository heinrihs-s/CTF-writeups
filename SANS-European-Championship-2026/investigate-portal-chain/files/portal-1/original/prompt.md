# InvestiGate Portal 1

- **Category:** Web Portal Offensive (100pts)
- **Platform URL:** https://ranges.io/event/bf72b90c-2149-11f1-9ad7-316439613462/challenge/49ea1684-56b0-11f1-9f90-646231653833
- **Portal URL:** https://nm04.bootupctf.net:8000/login

## Briefing

Disaster has struck at InvestiGate—our database of confidential evidence has been compromised. We pride ourselves on maintaining the utmost privacy in our investigations, yet someone has managed to gain unauthorized access to critical case files and highly sensitive evidence. This breach could put witnesses at risk and jeopardize ongoing cases.

Recently, we began rebuilding our online portal, a system designed for our investigators to securely register cases and store legal evidence. However, the site is still under development. One of our IT staff mentioned that production data has already been transferred into the development database—a decision that may have inadvertently exposed our information to attackers.

Your mission is to investigate how the attackers gained access and determine what case- and evidence data has potentially been compromised.

Note: This is challenge 1 of 5 in a series sharing the same web app. The same portal instance must be reused.

## Status

Web challenge — pending solve agent. Likely entry-point: SQL injection on /login or default-creds/admin path.
