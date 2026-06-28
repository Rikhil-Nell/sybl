# Security Policy

## Supported versions

| Version | Supported |
| ------- | --------- |
| 0.1.x   | Yes       |

## Reporting a vulnerability

Please **do not** open a public GitHub issue for security vulnerabilities.

Report them privately via one of:

- [GitHub Security Advisories](https://github.com/Rikhil-Nell/sybl/security/advisories/new)
  (preferred)
- Email: **nrikhil@gmail.com**

Include steps to reproduce, impact, and any suggested fix if you have one. We
will acknowledge receipt and work on a fix before public disclosure when possible.

## Scope notes

sybl is a local-first BYOK dictation tool. API keys are stored in the OS keyring
and sent only to STT providers you configure. Audio is not stored or transmitted
except to your chosen provider during transcription.
