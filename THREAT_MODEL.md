# AlleyCat GPG — Threat Model

## Purpose

This document describes what AlleyCat GPG protects against, what it does not
protect against, and what assumptions it makes about the user's environment.

It is intended to help users make informed decisions about when and how to use
this tool.

---

## What AlleyCat GPG Is

AlleyCat GPG is a local desktop GUI wrapper for GnuPG (GPG). It lets users
encrypt and decrypt text messages and files using OpenPGP public-key
cryptography or symmetric passphrase encryption — without using the command
line.

The intended use case is sending encrypted content over any channel that
carries text or files: SMS, iMessage, email, Signal, Telegram, Discord, etc.

---

## Primary Threat: Passive Surveillance

### What we protect against

**ISP and cell tower traffic interception.**

When you send an unencrypted SMS or email, the content is visible to:
- Your mobile carrier
- The recipient's mobile carrier
- Any network infrastructure in between
- Law enforcement with a subpoena to any of the above

AlleyCat GPG encrypts the message content **before** it leaves your device.
What gets transmitted is an armored PGP block — opaque ciphertext. The carrier
sees that you sent a message, but not what it says.

**Passive dragnet surveillance.**

Bulk interception programs that collect message content in transit see only
ciphertext. Without the recipient's private key, the content is
computationally infeasible to decrypt.

**File and document confidentiality.**

Encrypted files sent as attachments (PDF, image, zip, etc.) are unreadable
without the recipient's private key or the shared passphrase.

---

## What We Do NOT Protect Against

### Compromised operating system

If an attacker has root/kernel access to your machine, they can:
- Read memory while plaintext is displayed on screen
- Log keystrokes including passphrases
- Intercept GPG subprocess calls
- Access your private key directly

**AlleyCat GPG provides no protection if your OS is compromised.**

### Compromised GPG binary

This app calls the system `gpg` binary. If that binary has been replaced or
tampered with, all bets are off. Use package manager verification and OS
integrity tools to protect your system binaries.

### Physical access to unlocked device

If someone has physical access to your unlocked computer while the app is
running, they can read decrypted content on screen. Use the Panic button
(`⌘⇧X`) to clear the screen immediately when not in use.

### Recipient device compromise

Encryption protects content in transit. Once the recipient decrypts the
message on their device, the content is only as secure as their device.

### Metadata

AlleyCat GPG encrypts **content**, not **metadata**. Your carrier, ISP, and
any surveillance infrastructure can still see:
- That you sent a message to a particular number or address
- When you sent it
- Approximately how large it was

If metadata is part of your threat model, combine AlleyCat GPG with a
metadata-resistant transport (e.g. Signal for delivery, using AlleyCat GPG
for the content layer).

### Key verification failure

If you encrypt to the wrong public key — or a key that has been substituted
by an attacker (MITM on key import) — the attacker can decrypt your message.

**Always verify key fingerprints out-of-band** (phone call, in person,
a separate trusted channel) before relying on a contact's public key.
AlleyCat GPG reminds you to do this after every key import.

### Weak passphrases (symmetric mode)

In passphrase-only (symmetric) encryption mode, the security of the message
depends entirely on the strength of the passphrase. Use a long, random
passphrase. Share it through a separate, trusted channel — never in the same
message as the encrypted content.

### Private key theft

Your private key is stored in your local GPG keyring (`~/.gnupg`). If an
attacker copies your keyring and knows your passphrase, they can decrypt any
message encrypted to your key.

Protect your private key with a strong passphrase. Consider hardware key
storage (YubiKey / OpenPGP smart card) for high-value keys.

---

## Assumptions

1. The user's OS and hardware are not compromised at time of use.
2. The user's GPG installation is authentic and unmodified.
3. The user verifies key fingerprints before trusting them.
4. The user understands that metadata (who, when, how much) is not protected.
5. The user uses strong passphrases to protect their private key.

---

## Comparison with Signal

| Property | AlleyCat GPG | Signal |
|----------|-------------|--------|
| Content encryption | ✅ OpenPGP | ✅ Signal Protocol |
| Forward secrecy | ❌ No | ✅ Yes |
| Metadata protection | ❌ No | ✅ Sealed sender |
| Disappearing messages | ❌ No | ✅ Yes |
| Works over SMS/email | ✅ Yes | ❌ No |
| File encryption | ✅ Yes | ✅ Yes (in-app) |
| Desktop + mobile | Desktop only | ✅ Both |
| Open standard (OpenPGP) | ✅ Yes | ❌ Proprietary |
| No account required | ✅ Yes | ❌ Phone number required |

These tools serve different threat models and complement each other.
AlleyCat GPG is best for situations where you need to encrypt content
that will be delivered over an untrusted channel (SMS, email, any messenger)
and want to avoid ISP/carrier visibility into the content.

---

## Reporting Security Issues

See [SECURITY.md](SECURITY.md).
