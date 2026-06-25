# Contributing to AlleyCat GPG

Thanks for your interest in contributing. AlleyCat GPG is a solo-maintained
project that welcomes pull requests from anyone.

---

## Ground Rules

1. **No new dependencies.** The app uses Python stdlib + tkinter only. Do not
   add pip packages. This keeps the app lightweight, auditable, and easy to
   package cross-platform.

2. **Must work on all three platforms.** macOS, Windows, and Linux. If you
   can only test one platform, say so in your PR and we'll test the others.

3. **No custom cryptography.** All crypto must go through the system `gpg`
   binary. Do not implement or introduce any cryptographic primitives.

4. **No `shell=True`.** All subprocess calls must use list arguments. This is
   a security requirement, not a style preference.

5. **No plaintext storage.** Do not add any feature that saves, logs, or
   caches plaintext messages, passphrases, or key material.

6. **No network calls from the app.** The app must remain fully local. No
   telemetry, no keyserver lookups, no update checks.

---

## What We Welcome

- Bug fixes
- Platform compatibility improvements
- UI/UX improvements
- Accessibility improvements
- Documentation improvements
- New themes
- Performance improvements
- Additional GPG operations (key generation, revocation, etc.)
- Mobile support (future milestone — coordinate first)

---

## How to Contribute

### 1. Fork and clone

```bash
git clone https://github.com/YOUR_USERNAME/gpg-messenger.git
cd gpg-messenger
```

### 2. Run locally

```bash
python3 gpg_messenger.py
```

Requires Python 3.9+ and tkinter. No pip install needed.

### 3. Make your changes

Keep changes focused — one fix or feature per PR. If you're unsure whether
something fits, open an issue first to discuss.

### 4. Test on your platform

At minimum test on the platform you're changing. Note in your PR description
which platforms you tested.

### 5. Open a pull request

- Describe what the change does and why
- Note which platforms were tested
- Reference any related issues

---

## Reporting Bugs

Open a [GitHub Issue](../../issues/new/choose) using the Bug Report template.

Include:
- Your OS and version
- Your Python version (`python3 --version`)
- Your GPG version (`gpg --version`)
- Steps to reproduce
- What you expected vs what happened

---

## Security Issues

**Do not open public issues for security vulnerabilities.**

Report privately to: **alleycat.elite337@passmail.net**

See [SECURITY.md](SECURITY.md) for the full policy.

---

## Code Style

- Follow the existing style — the codebase uses standard Python conventions
- Keep functions focused and named clearly
- Comment non-obvious logic, especially anything GPG-related
- No type annotations required but welcome
