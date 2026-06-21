# Security Policy

## Scope

AirmonGUI is a **local-first** application. By design it binds its API and dev server to
`127.0.0.1` and makes no outbound network connections. The most relevant security concerns
are therefore:

- Command/argument injection through the subprocess layer (`backend/app/utils.py`).
- Path traversal in capture file handling (`backend/app/routes/captures.py`).
- Any change that would cause the server to bind to a non-loopback interface by default.
- CORS / WebSocket origin handling.

## Reporting a Vulnerability

If you discover a security issue, **please do not open a public issue.**

Instead, report it privately via GitHub's
[**Security Advisories**](https://github.com/ELHart05/AirmonGUI/security/advisories/new)
("Report a vulnerability"). Include:

- A clear description of the issue and its impact.
- Steps to reproduce (a minimal proof-of-concept is ideal).
- The affected file(s) / endpoint(s) and any suggested fix.

You can expect an initial acknowledgement within a few days. Coordinated, responsible
disclosure is appreciated, and contributors who report valid issues will be credited
(unless you prefer to remain anonymous).

## Responsible Use

AirmonGUI is a front-end for offensive wireless tooling intended **only** for authorized
testing on networks you own or have written permission to assess. Reports describing how to
misuse the tool against third parties are out of scope. This policy covers defects in
AirmonGUI itself, not the capabilities of the aircrack-ng suite.
