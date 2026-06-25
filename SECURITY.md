# Security Policy

## Project: AlleyCat GPG

AlleyCat GPG is a local desktop wrapper for GnuPG. All cryptographic operations
are delegated to the system `gpg` binary. This project takes security seriously
and appreciates responsible disclosure.

---

## Supported Versions

| Version | Supported |
|---------|-----------|
| 2.x (latest) | ✅ Active |
| 1.x | ❌ No longer maintained |

Always use the latest release from the
[Releases page](../../releases).

---

## Reporting a Vulnerability

**Do not open a public GitHub issue for security vulnerabilities.**

Report privately to:

📧 **alleycat.elite337@passmail.net**

Please include:

- A clear description of the vulnerability
- Steps to reproduce
- Potential impact
- Your suggested fix (if any)

You will receive an acknowledgment within **48 hours** and a status update
within **7 days**.

If a fix is warranted, we will:

1. Develop and test a patch
2. Release a patched version
3. Credit you in the release notes (unless you prefer anonymity)
4. Publish a GitHub Security Advisory

---

## Security Design

AlleyCat GPG is designed as an **encryption workstation**, not a chat app.

### What it does

- Wraps the locally installed `gpg` binary via subprocess
- Encrypts and decrypts messages and files using OpenPGP
- Supports PGP key encryption and passphrase-only (symmetric) encryption
- Delegates all passphrase prompts to `gpg-agent` / `pinentry`

### What it does not do

- Does not implement any custom cryptography
- Does not store plaintext messages, decrypted content, or passphrases
- Does not log key material, fingerprints, or message contents
- Does not make network requests
- Does not send telemetry
- Does not use `shell=True` in subprocess calls
- Does not auto-copy plaintext to clipboard

### Known limitations and scope

- **Not safe if your OS is compromised.** If an attacker has access to your
  machine, device, or kernel, no desktop encryption tool can protect you.
  AlleyCat GPG does not provide OS-level or memory-level security guarantees.

- **Not a Signal replacement.** Signal provides forward secrecy, sealed sender,
  and disappearing messages. AlleyCat GPG provides OpenPGP encryption for
  messages and files sent over any medium (SMS, email, etc.) and avoids
  ISP/cell tower visibility into message content. These are complementary tools
  with different threat models.

- **Key trust is your responsibility.** Always verify fingerprints out-of-band
  before trusting a contact's public key.

- **Mobile not supported.** This is a desktop application only.

---

## Threat Model

See [THREAT_MODEL.md](THREAT_MODEL.md) for a full threat model.
