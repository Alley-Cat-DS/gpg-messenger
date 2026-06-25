# GPG Messenger

A local desktop GUI wrapper for GnuPG — secure copy-paste encrypted messaging without touching the command line.

> **All cryptography is handled by your system's `gpg` binary. This app never implements its own crypto.**

---

## Download

Go to the [Releases](../../releases) page and download for your platform:

| Platform | File |
|----------|------|
| macOS | `GPG-Messenger-macOS.dmg` |
| Windows | `GPG-Messenger-Setup.exe` |
| Linux | `GPG-Messenger-Linux-x86_64.AppImage` |

---

## Features

- **Compose & encrypt** messages to PGP key recipients or with passphrase-only (symmetric) encryption
- **Sign + encrypt** with your own key
- **Decrypt** armored PGP messages with full signature status display
- **File encryption** — encrypt/decrypt any file (PDF, image, zip, etc.)
- **Import contacts** — paste a public key block to import, with fingerprint verification reminder
- **Fingerprint viewer** — for both your identities and contacts
- **Theme system** — Dark, Light, Solarized, High Contrast, or fully custom colors
- **Panic button** (`⌘⇧X`) — clears all fields, clipboard, and GPG cache instantly
- **Cache viewer** — session log and shell history viewer (GPG commands hidden)
- **Privacy tools** — clear fields, clipboard, GPG agent cache, shell history
- **First-run setup** — auto-installs Homebrew, gnupg, and pinentry-mac on macOS

---

## Security Philosophy

- Does not implement custom cryptography
- Uses the installed `gpg` binary via subprocess (no `shell=True`)
- Does not store plaintext messages or decrypted content
- Does not log passphrases, key material, or message contents
- Does not send telemetry or make network requests
- Treats clipboard use as a risk — never auto-copies plaintext
- Lets `gpg-agent` / `pinentry` handle all passphrase prompts

---

## Requirements

### macOS
- macOS 10.14+
- GnuPG: `brew install gnupg`
- pinentry-mac (recommended): `brew install pinentry-mac`
- The app will offer to install these on first run

### Windows
- Windows 10+
- [Gpg4win](https://gpg4win.org) (includes GnuPG and a graphical pinentry)

### Linux
- Any modern distro (x86_64)
- GnuPG: `sudo apt install gnupg` or equivalent
- The AppImage is self-contained — no installation needed

---

## Building from Source

Requires Python 3.9+ and tkinter.

```bash
git clone https://github.com/YOUR_USERNAME/gpg-messenger
cd gpg-messenger

# Run directly
python3 gpg_messenger.py

# Build for your platform
bash build_mac.sh       # macOS → .dmg
build_windows.bat       # Windows → .exe + installer
bash build_linux.sh     # Linux → .AppImage
```

### Automated builds

Push a version tag to trigger GitHub Actions builds for all three platforms:

```bash
git tag v2.0.1
git push origin v2.0.1
```

This creates a GitHub Release with `.dmg`, `.exe`, and `.AppImage` attached automatically.

---

## Adding a Custom Icon

Replace the placeholder icons before building:

- `assets/icon.icns` — macOS (512×512 recommended)
- `assets/icon.ico` — Windows (256×256 recommended)
- `assets/icon.png` — Linux (256×256 PNG)

---

## Troubleshooting

**Passphrase prompt fails / GPG timeout on macOS**

Install the graphical pinentry and wire it up:
```bash
brew install pinentry-mac
echo "pinentry-program $(which pinentry-mac)" >> ~/.gnupg/gpg-agent.conf
gpgconf --reload gpg-agent
```

Or add to `~/.zshrc`:
```bash
export GPG_TTY=$(tty)
```

**App won't open on macOS (Gatekeeper warning)**

Right-click the app → Open → Open anyway. This is expected for unsigned apps.
For production distribution, code signing and notarization via Apple Developer account removes this warning.

**tkinter not found (macOS/Homebrew Python)**

```bash
brew install python-tk@3.14   # match your Python version
```

---

## License

MIT — see [LICENSE](LICENSE)
