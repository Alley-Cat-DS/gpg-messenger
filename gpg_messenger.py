#!/usr/bin/env python3
"""
GPG GUI v2 — A local desktop wrapper for GnuPG.
Delegates all cryptography to the system gpg binary.
Does not store plaintext, ciphertext, or key material.

New in v2:
  - First-run dependency installer (Homebrew, gnupg, pinentry-mac, python-tk)
  - Panic button (Cmd+Shift+X / Ctrl+Shift+X) — clears everything instantly
  - Theme system: Dark (default), Light, Solarized, High Contrast, Custom
  - Cache Viewer tab: shell history + app session log
  - File encryption: upload any file, encrypt/decrypt to .gpg
  - Passphrase-only (symmetric) encryption mode — no PGP key required
  - Encryption Method selector on Compose and Decrypt tabs
"""

import os
import sys
import subprocess
import platform
import shutil
import base64
import tempfile
import json
import datetime
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, colorchooser

# ─── Theme Engine ─────────────────────────────────────────────────────────────

THEMES = {
    "Dark": {
        "BG":      "#1a1b1e",
        "BG2":     "#242529",
        "BG3":     "#2e2f34",
        "BORDER":  "#3a3b41",
        "ACCENT":  "#7c9ef0",
        "ACCENT2": "#a8c0ff",
        "FG":      "#d4d6de",
        "FG2":     "#8b8fa8",
        "GREEN":   "#5ecf87",
        "RED":     "#f06b6b",
        "YELLOW":  "#e8c46a",
    },
    "Light": {
        "BG":      "#f5f5f7",
        "BG2":     "#ffffff",
        "BG3":     "#ebebed",
        "BORDER":  "#c8c8cc",
        "ACCENT":  "#2d6df6",
        "ACCENT2": "#1a4fd6",
        "FG":      "#1c1c1e",
        "FG2":     "#6e6e73",
        "GREEN":   "#1d9c5a",
        "RED":     "#d93025",
        "YELLOW":  "#b5830a",
    },
    "Solarized": {
        "BG":      "#002b36",
        "BG2":     "#073642",
        "BG3":     "#0d3d4a",
        "BORDER":  "#586e75",
        "ACCENT":  "#268bd2",
        "ACCENT2": "#2aa198",
        "FG":      "#839496",
        "FG2":     "#657b83",
        "GREEN":   "#859900",
        "RED":     "#dc322f",
        "YELLOW":  "#b58900",
    },
    "High Contrast": {
        "BG":      "#000000",
        "BG2":     "#0a0a0a",
        "BG3":     "#111111",
        "BORDER":  "#444444",
        "ACCENT":  "#00ff88",
        "ACCENT2": "#00ffcc",
        "FG":      "#ffffff",
        "FG2":     "#aaaaaa",
        "GREEN":   "#00ff88",
        "RED":     "#ff3333",
        "YELLOW":  "#ffdd00",
    },
}

# Active theme colors — module-level globals updated by apply_theme_colors()
BG = BORDER = ACCENT = ACCENT2 = FG = FG2 = GREEN = RED = YELLOW = ""
BG2 = BG3 = ""

MONO = ("Courier New", 10) if platform.system() == "Windows" else ("Courier", 10)
SANS = ("Segoe UI", 10)    if platform.system() == "Windows" else ("Helvetica Neue", 10)
SANS_SM = ("Segoe UI", 9)  if platform.system() == "Windows" else ("Helvetica Neue", 9)

_current_theme_name = "Dark"
_custom_theme = dict(THEMES["Dark"])  # user-editable copy

# App-level session log (non-persistent, metadata only — no plaintext)
_session_log = []

def _log(msg):
    ts = datetime.datetime.now().strftime("%H:%M:%S")
    _session_log.append(f"[{ts}] {msg}")
    if len(_session_log) > 500:
        _session_log.pop(0)


def get_theme_colors(name):
    if name == "Custom":
        return _custom_theme
    return THEMES.get(name, THEMES["Dark"])


def apply_theme_colors(name):
    global BG, BG2, BG3, BORDER, ACCENT, ACCENT2, FG, FG2, GREEN, RED, YELLOW
    global _current_theme_name
    _current_theme_name = name
    t = get_theme_colors(name)
    BG      = t["BG"]
    BG2     = t["BG2"]
    BG3     = t["BG3"]
    BORDER  = t["BORDER"]
    ACCENT  = t["ACCENT"]
    ACCENT2 = t["ACCENT2"]
    FG      = t["FG"]
    FG2     = t["FG2"]
    GREEN   = t["GREEN"]
    RED     = t["RED"]
    YELLOW  = t["YELLOW"]


apply_theme_colors("Dark")

# ─── Dependency Installer ─────────────────────────────────────────────────────

def _run_quietly(*cmd):
    try:
        r = subprocess.run(list(cmd), capture_output=True, text=True, timeout=120)
        return r.returncode == 0, r.stdout + r.stderr
    except Exception as e:
        return False, str(e)


def check_brew():
    return shutil.which("brew") is not None


def check_gpg_bin():
    return shutil.which("gpg") is not None


def check_pinentry_mac():
    return shutil.which("pinentry-mac") is not None


def run_first_time_setup(log_callback):
    """
    Check and install missing dependencies on macOS.
    log_callback(str) is called with progress lines.
    Returns True if everything is ready.
    """
    system = platform.system()
    if system != "Darwin":
        log_callback("Auto-install is macOS-only. Please install gnupg manually.")
        return check_gpg_bin()

    log_callback("Checking dependencies…")

    # Homebrew
    if not check_brew():
        log_callback("Homebrew not found. Installing Homebrew…")
        log_callback("(This may take a few minutes and may prompt for your password)")
        ok, out = _run_quietly(
            "/bin/bash", "-c",
            '/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"'
        )
        log_callback("Homebrew installed." if ok else f"Homebrew install failed:\n{out}")
        if not ok:
            return False
    else:
        log_callback("✓ Homebrew")

    # gnupg
    if not check_gpg_bin():
        log_callback("Installing gnupg…")
        ok, out = _run_quietly("brew", "install", "gnupg")
        log_callback("✓ gnupg installed." if ok else f"gnupg install failed:\n{out}")
        if not ok:
            return False
    else:
        log_callback("✓ gnupg")

    # pinentry-mac
    if not check_pinentry_mac():
        log_callback("Installing pinentry-mac (graphical passphrase prompts)…")
        ok, out = _run_quietly("brew", "install", "pinentry-mac")
        if ok:
            log_callback("✓ pinentry-mac installed.")
            # Wire it up
            gnupghome = os.path.expanduser("~/.gnupg")
            os.makedirs(gnupghome, exist_ok=True)
            conf_path = os.path.join(gnupghome, "gpg-agent.conf")
            pinentry_path = shutil.which("pinentry-mac") or "/usr/local/bin/pinentry-mac"
            line = f"pinentry-program {pinentry_path}\n"
            try:
                existing = open(conf_path).read() if os.path.exists(conf_path) else ""
                if "pinentry-program" not in existing:
                    with open(conf_path, "a") as f:
                        f.write(line)
                    log_callback("  → Configured gpg-agent to use pinentry-mac.")
                    _run_quietly("gpgconf", "--reload", "gpg-agent")
            except Exception as e:
                log_callback(f"  (Could not write gpg-agent.conf: {e})")
        else:
            log_callback(f"pinentry-mac install failed (non-fatal):\n{out}")
    else:
        log_callback("✓ pinentry-mac")

    log_callback("All dependencies ready.")
    return check_gpg_bin()


# ─── GPG Utilities ────────────────────────────────────────────────────────────

def get_env():
    env = os.environ.copy()
    try:
        tty = subprocess.check_output(["tty"], text=True, stderr=subprocess.DEVNULL).strip()
        if tty:
            env["GPG_TTY"] = tty
    except Exception:
        pass
    return env


def run_gpg(*args, input_data=None, input_bytes=None):
    """Run gpg. Pass input_data for text, input_bytes for binary. Returns (stdout, stderr, rc)."""
    cmd = ["gpg"] + list(args)
    try:
        if input_bytes is not None:
            result = subprocess.run(
                cmd, input=input_bytes,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                env=get_env(),
            )
            return result.stdout.decode("utf-8", errors="replace"), \
                   result.stderr.decode("utf-8", errors="replace"), \
                   result.returncode
        else:
            result = subprocess.run(
                cmd, input=input_data,
                capture_output=True, text=True,
                env=get_env(),
            )
            return result.stdout, result.stderr, result.returncode
    except FileNotFoundError:
        return "", "gpg not found", 1


def check_gpg():
    stdout, stderr, rc = run_gpg("--version")
    return rc == 0, stdout.splitlines()[0] if stdout else stderr


def parse_keys_from_colon_output(output):
    keys = []
    current = None
    for line in output.splitlines():
        fields = line.split(":")
        if not fields:
            continue
        rec = fields[0]
        if rec in ("pub", "sec"):
            if current:
                keys.append(current)
            current = {
                "type": "secret" if rec == "sec" else "public",
                "keyid": fields[4] if len(fields) > 4 else "",
                "fingerprint": "",
                "uids": [],
                "capabilities": fields[11] if len(fields) > 11 else "",
                "expires": fields[6] if len(fields) > 6 else "",
                "trust": fields[1] if len(fields) > 1 else "",
            }
        elif rec == "fpr" and current is not None:
            if not current["fingerprint"]:
                current["fingerprint"] = fields[9] if len(fields) > 9 else ""
        elif rec == "uid" and current is not None:
            uid = fields[9] if len(fields) > 9 else ""
            if uid:
                current["uids"].append(uid)
    if current:
        keys.append(current)
    return keys


def format_key_label(key):
    uid = key["uids"][0] if key["uids"] else "(no uid)"
    kid = key["keyid"][-8:] if key["keyid"] else "????????"
    exp = f"  [exp {key['expires']}]" if key.get("expires") else ""
    return f"{uid} — …{kid}{exp}"


def list_secret_keys():
    stdout, _, _ = run_gpg("--list-secret-keys", "--keyid-format", "LONG", "--with-colons")
    return parse_keys_from_colon_output(stdout)


def list_public_keys():
    stdout, _, _ = run_gpg("--list-keys", "--keyid-format", "LONG", "--with-colons")
    return parse_keys_from_colon_output(stdout)


def parse_sig_status(stderr):
    signer = ""
    for line in stderr.splitlines():
        ll = line.lower()
        if "good signature from" in ll:
            signer = line.split("from", 1)[-1].strip().strip('"')
            return "Good ✓", GREEN, signer
        if "bad signature" in ll:
            return "BAD — do not trust", RED, ""
        if "no public key" in ll or "key not found" in ll:
            return "Unknown key — import sender's key", YELLOW, ""
        if "expired" in ll and "signature" in ll:
            return "Signed with expired key", YELLOW, ""
    if "encrypted" in stderr.lower() and "signature" not in stderr.lower():
        return "None detected", FG2, ""
    return "None detected", FG2, ""


def format_fingerprint(fp):
    fp = fp.replace(" ", "")
    return "  ".join(fp[i:i+4] for i in range(0, len(fp), 4))


def friendly_error(stderr):
    s = stderr.lower()
    if "no valid openpgp data" in s:
        return ("Not a valid PGP message.\n\nMake sure you copied the full block, "
                "from -----BEGIN PGP MESSAGE----- to -----END PGP MESSAGE-----.")
    if "no secret key" in s or "bad passphrase" in s or "decryption failed" in s:
        return ("Decryption failed.\n\nThis message was not encrypted to any private key "
                "on this computer, or the passphrase was wrong.")
    if "bad signature" in s:
        return "Bad signature. The message may have been altered or signed by a different key."
    if "no public key" in s or "key not found" in s:
        return "Signed by a key you don't have. Import and verify the sender's public key first."
    if "expired" in s:
        return "A key involved in this operation is expired. Proceed with caution."
    if "no recipients" in s or "no recipient" in s:
        return "No valid recipient key. Select a contact whose public key you have imported."
    if stderr.strip():
        return f"GPG error:\n{stderr.strip()}"
    return "An unknown error occurred."


# ─── Clipboard ────────────────────────────────────────────────────────────────

def copy_to_clipboard(root, text):
    root.clipboard_clear()
    root.clipboard_append(text)


def clear_clipboard(root):
    root.clipboard_clear()
    root.clipboard_append("")


# ─── Widget Helpers ───────────────────────────────────────────────────────────

def apply_ttk_theme():
    style = ttk.Style()
    style.theme_use("clam")
    style.configure("TFrame", background=BG2)
    style.configure("TNotebook", background=BG, borderwidth=0, tabmargins=[0, 0, 0, 0])
    style.configure("TNotebook.Tab", background=BG, foreground=FG2,
                    padding=[16, 8], font=(*SANS, "bold"), borderwidth=0)
    style.map("TNotebook.Tab",
              background=[("selected", BG2)],
              foreground=[("selected", ACCENT2)])
    style.configure("TCombobox", fieldbackground=BG3, background=BG3, foreground=FG,
                    selectbackground=ACCENT, selectforeground=FG,
                    bordercolor=BORDER, arrowcolor=FG2)
    style.map("TCombobox", fieldbackground=[("readonly", BG3)])
    style.configure("TLabel", background=BG2, foreground=FG, font=SANS)
    style.configure("TButton", background=BORDER, foreground=FG, font=SANS,
                    borderwidth=0, padding=[10, 5])
    style.map("TButton", background=[("active", ACCENT), ("pressed", ACCENT)])
    style.configure("Accent.TButton", background=ACCENT, foreground=BG,
                    font=(*SANS, "bold"), padding=[12, 6])
    style.map("Accent.TButton", background=[("active", ACCENT2)])
    style.configure("Panic.TButton", background=RED, foreground="#ffffff",
                    font=(*SANS, "bold"), padding=[12, 6])
    style.map("Panic.TButton", background=[("active", "#ff8888")])
    style.configure("Danger.TButton", background="#4a2020", foreground=RED,
                    font=SANS, padding=[10, 5])
    style.map("Danger.TButton", background=[("active", "#6b2b2b")])
    style.configure("TSeparator", background=BORDER)


def _attach_context_menu(widget):
    """Attach a right-click Cut / Copy / Paste / Select All menu to a Text widget."""
    menu = tk.Menu(widget, tearoff=0, bg=BG2, fg=FG, activebackground=ACCENT,
                   activeforeground=BG, bd=0, relief="flat")
    menu.add_command(label="Cut",        command=lambda: widget.event_generate("<<Cut>>"))
    menu.add_command(label="Copy",       command=lambda: widget.event_generate("<<Copy>>"))
    menu.add_command(label="Paste",      command=lambda: widget.event_generate("<<Paste>>"))
    menu.add_separator()
    menu.add_command(label="Select All", command=lambda: widget.tag_add("sel", "1.0", tk.END))

    def _show(event):
        # Temporarily enable so paste fires even on display-only boxes
        prev_state = str(widget.cget("state"))
        widget.config(state=tk.NORMAL)
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            widget.config(state=prev_state)

    widget.bind("<Button-2>", _show)   # macOS two-finger tap / middle-click
    widget.bind("<Button-3>", _show)   # standard right-click


def make_textbox(parent, height=8, mono=False, readonly=False):
    font = MONO if mono else SANS
    t = tk.Text(parent, height=height, bg=BG3, fg=FG, insertbackground=ACCENT,
                relief="flat", bd=0, font=font,
                selectbackground=ACCENT, selectforeground=BG,
                wrap=tk.WORD, padx=8, pady=8,
                state=tk.DISABLED if readonly else tk.NORMAL)
    _attach_context_menu(t)
    return t


def make_scrolled_textbox(parent, height=8, mono=False, readonly=False):
    """
    A tk.Text with its own vertical scrollbar packed into a container frame.
    Returns (container_frame, text_widget).
    The container should be packed/gridded by the caller.
    Trackpad scroll works natively inside tk.Text — this is the reliable approach.
    """
    font = MONO if mono else SANS
    container = tk.Frame(parent, bg=BG3)
    t = tk.Text(container, height=height, bg=BG3, fg=FG, insertbackground=ACCENT,
                relief="flat", bd=0, font=font,
                selectbackground=ACCENT, selectforeground=BG,
                wrap=tk.WORD, padx=8, pady=8,
                state=tk.DISABLED if readonly else tk.NORMAL,
                yscrollcommand=lambda *a: sb.set(*a))
    sb = ttk.Scrollbar(container, orient="vertical", command=t.yview)
    t.pack(side="left", fill="both", expand=True)
    sb.pack(side="right", fill="y")
    _attach_context_menu(t)
    return container, t


def set_text(widget, text):
    widget.config(state=tk.NORMAL)
    widget.delete("1.0", tk.END)
    widget.insert("1.0", text)


def get_text(widget):
    return widget.get("1.0", tk.END).rstrip("\n")


def clear_text(widget):
    widget.config(state=tk.NORMAL)
    widget.delete("1.0", tk.END)


def make_button(parent, text, command, style="TButton"):
    return ttk.Button(parent, text=text, command=command, style=style)


def make_combo(parent, values, textvariable=None, width=55):
    c = ttk.Combobox(parent, values=values, textvariable=textvariable,
                     width=width, state="readonly", font=SANS)
    return c


def section_label(parent, text):
    f = tk.Frame(parent, bg=BG2)
    tk.Label(f, text=text.upper(), bg=BG2, fg=ACCENT,
             font=(*SANS_SM, "bold"), anchor="w").pack(side="left")
    return f


# ─── Scrolled text helper ─────────────────────────────────────────────────────
# We gave up fighting Tkinter's scroll event chain on macOS.
# Solution: no outer scrollable frame at all. Each tab is a fixed layout
# that fills the window. Every tk.Text gets its own sidebar scrollbar so
# the user can always scroll text content with the trackpad (which works
# natively inside Text widgets) or with the visible scrollbar.

def tab_frame(parent):
    """Return a plain frame for tab content — no outer scrolling needed."""
    f = tk.Frame(parent, bg=BG2)
    return f, f   # (outer, inner) API compatibility


def install_class_scroll_bindings(root):
    """No-op — text boxes scroll natively; no outer frame scroll needed."""
    pass


def _attach_scroll_recursive(widget, canvas):
    """No-op — kept for call-site compatibility."""
    pass


# ─── Setup / First-Run Window ─────────────────────────────────────────────────

class SetupWindow(tk.Toplevel):
    def __init__(self, parent, on_done):
        super().__init__(parent)
        self.title("GPG GUI — First Run Setup")
        self.configure(bg=BG)
        self.resizable(False, False)
        self.grab_set()
        self.on_done = on_done

        tk.Label(self, text="Setting up dependencies…", bg=BG, fg=ACCENT2,
                 font=("Helvetica Neue", 13, "bold")).pack(padx=24, pady=(20, 8), anchor="w")

        self.log_box = tk.Text(self, height=16, width=64, bg=BG3, fg=FG,
                               font=MONO, relief="flat", padx=8, pady=8,
                               state=tk.DISABLED)
        self.log_box.pack(padx=24, pady=(0, 16))

        self.close_btn = make_button(self, "Please wait…", lambda: None)
        self.close_btn.pack(padx=24, pady=(0, 20), anchor="e")

        self.after(200, self._run)

    def _log(self, msg):
        self.log_box.config(state=tk.NORMAL)
        self.log_box.insert(tk.END, msg + "\n")
        self.log_box.see(tk.END)
        self.log_box.config(state=tk.DISABLED)
        self.update()

    def _run(self):
        ready = run_first_time_setup(self._log)
        if ready:
            self.close_btn.config(text="Continue →", command=self._finish)
        else:
            self._log("\nGPG is not available. Install it and restart the app.")
            self.close_btn.config(text="Close", command=self.destroy)

    def _finish(self):
        self.destroy()
        self.on_done()


# ─── Main App ─────────────────────────────────────────────────────────────────

PREFS_PATH = os.path.expanduser("~/.gnupg/gpggui_prefs.json")

def load_prefs():
    try:
        with open(PREFS_PATH) as f:
            return json.load(f)
    except Exception:
        return {}

def save_prefs(prefs):
    try:
        with open(PREFS_PATH, "w") as f:
            json.dump(prefs, f, indent=2)
    except Exception:
        pass


class GPGApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("GPG Messenger")
        self.configure(bg=BG)
        self.resizable(True, True)
        self.minsize(760, 580)

        self.prefs = load_prefs()
        theme_name = self.prefs.get("theme", "Dark")
        if theme_name == "Custom" and "custom_theme" in self.prefs:
            global _custom_theme
            _custom_theme = self.prefs["custom_theme"]
        apply_theme_colors(theme_name)
        apply_ttk_theme()

        self.secret_keys = []
        self.public_keys  = []
        self._file_path = None       # currently loaded file for file encryption
        self._file_bytes = None

        # Check GPG — if missing, show setup
        ok, version_line = check_gpg()
        if not ok or self.prefs.get("show_setup", True):
            self._build_splash()
            SetupWindow(self, self._launch_main)
        else:
            self._launch_main(version_line)

    def _build_splash(self):
        self._splash = tk.Frame(self, bg=BG)
        self._splash.pack(expand=True, fill="both")
        tk.Label(self._splash, text="🔐  GPG Messenger",
                 bg=BG, fg=ACCENT2, font=("Helvetica Neue", 20, "bold")).pack(expand=True)

    def _launch_main(self, version_line=None):
        if hasattr(self, "_splash"):
            self._splash.destroy()
        if version_line is None:
            _, version_line = check_gpg()
        ok, version_line = check_gpg()
        if not ok:
            self._show_no_gpg()
            return

        self.prefs["show_setup"] = False
        save_prefs(self.prefs)

        self._build_header(version_line)
        self._build_panic_bar()
        self._build_tabs()
        self._refresh_all_keys()

        # Class-level scroll bindings (must be after window exists)
        install_class_scroll_bindings(self)

        # Panic hotkey
        self.bind_all("<Control-Shift-X>", lambda e: self._panic())
        self.bind_all("<Command-Shift-X>", lambda e: self._panic())

        _log("App launched.")

    # ── No GPG ────────────────────────────────────────────────────────────────

    def _show_no_gpg(self):
        f = tk.Frame(self, bg=BG, padx=40, pady=40)
        f.pack(expand=True, fill="both")
        tk.Label(f, text="GPG not found", bg=BG, fg=RED,
                 font=("Helvetica Neue", 18, "bold")).pack(anchor="w", pady=(0, 12))
        tk.Label(f, text=(
            "Install GnuPG and restart.\n\n"
            "  macOS:   brew install gnupg\n"
            "  Linux:   sudo apt install gnupg\n"
            "  Windows: install Gpg4win from https://gpg4win.org"
        ), bg=BG, fg=FG, font=MONO, justify="left").pack(anchor="w")

    # ── Header ────────────────────────────────────────────────────────────────

    def _build_header(self, version_line):
        h = tk.Frame(self, bg=BG, padx=20, pady=8)
        h.pack(fill="x")
        tk.Label(h, text="🔐  GPG Messenger", bg=BG, fg=ACCENT2,
                 font=("Helvetica Neue", 14, "bold")).pack(side="left")

        # Theme selector
        theme_names = list(THEMES.keys()) + ["Custom"]
        self._theme_var = tk.StringVar(value=_current_theme_name)
        theme_combo = ttk.Combobox(h, values=theme_names,
                                   textvariable=self._theme_var,
                                   width=14, state="readonly", font=SANS_SM)
        theme_combo.pack(side="right", padx=(8, 0))
        tk.Label(h, text="Theme:", bg=BG, fg=FG2, font=SANS_SM).pack(side="right")
        theme_combo.bind("<<ComboboxSelected>>", self._on_theme_change)

        tk.Label(h, text=version_line, bg=BG, fg=FG2, font=MONO).pack(side="right", padx=12)

    # ── Panic bar ─────────────────────────────────────────────────────────────

    def _build_panic_bar(self):
        bar = tk.Frame(self, bg="#2a0a0a", padx=12, pady=4)
        bar.pack(fill="x")
        make_button(bar, "🚨  PANIC CLEAR  (⌘⇧X)", self._panic, "Panic.TButton").pack(side="left")
        tk.Label(bar, text="Clears all fields, clipboard, and GPG cache instantly.",
                 bg="#2a0a0a", fg="#cc6666", font=SANS_SM).pack(side="left", padx=12)

    def _panic(self):
        _log("PANIC CLEAR triggered.")
        # Clear all text widgets
        for attr in ("compose_input", "compose_output", "decrypt_input", "decrypt_output",
                     "import_input", "file_encrypt_output", "file_decrypt_status"):
            w = getattr(self, attr, None)
            if w:
                try:
                    clear_text(w)
                except Exception:
                    pass
        # Clear file state
        self._file_path = None
        self._file_bytes = None
        if hasattr(self, "_file_label"):
            self._file_label.config(text="No file selected.")

        # Sig labels
        for attr in ("sig_status_label", "sig_signer_label"):
            w = getattr(self, attr, None)
            if w:
                try:
                    w.config(text="—" if attr == "sig_status_label" else "")
                except Exception:
                    pass

        # Clipboard
        clear_clipboard(self)

        # Kill agent
        try:
            subprocess.run(["gpgconf", "--kill", "gpg-agent"],
                           capture_output=True, env=get_env())
        except Exception:
            pass

        # Flash the window title briefly
        self.title("⚠ CLEARED ⚠")
        self.after(1500, lambda: self.title("GPG Messenger"))

    # ── Theme change ──────────────────────────────────────────────────────────

    def _on_theme_change(self, event=None):
        name = self._theme_var.get()
        if name == "Custom":
            self._open_custom_theme_editor()
            return
        apply_theme_colors(name)
        apply_ttk_theme()
        self.prefs["theme"] = name
        save_prefs(self.prefs)
        messagebox.showinfo("Theme Changed",
                            f"Theme set to '{name}'.\n\nRestart the app to apply fully.")

    def _open_custom_theme_editor(self):
        win = tk.Toplevel(self)
        win.title("Custom Theme Editor")
        win.configure(bg=BG)
        win.resizable(False, False)
        win.grab_set()

        tk.Label(win, text="Custom Theme", bg=BG, fg=ACCENT2,
                 font=("Helvetica Neue", 13, "bold")).pack(padx=24, pady=(16, 8), anchor="w")

        fields = [
            ("Background",        "BG"),
            ("Panel / Tab BG",    "BG2"),
            ("Input BG",          "BG3"),
            ("Border",            "BORDER"),
            ("Accent",            "ACCENT"),
            ("Accent 2",          "ACCENT2"),
            ("Primary Text",      "FG"),
            ("Secondary Text",    "FG2"),
            ("Good / Green",      "GREEN"),
            ("Error / Red",       "RED"),
            ("Warning / Yellow",  "YELLOW"),
        ]

        entries = {}
        grid = tk.Frame(win, bg=BG, padx=24)
        grid.pack()

        for i, (label, key) in enumerate(fields):
            tk.Label(grid, text=label, bg=BG, fg=FG, font=SANS, width=18, anchor="w").grid(
                row=i, column=0, pady=3, sticky="w")
            val = _custom_theme.get(key, "#ffffff")
            var = tk.StringVar(value=val)
            entries[key] = var
            swatch = tk.Label(grid, bg=val, width=4, relief="solid", bd=1)
            swatch.grid(row=i, column=1, padx=(0, 6))

            def make_picker(k, v, sw):
                def pick():
                    color = colorchooser.askcolor(color=v.get(), title=f"Pick {k}")[1]
                    if color:
                        v.set(color)
                        sw.config(bg=color)
                return pick

            e = tk.Entry(grid, textvariable=var, bg=BG3, fg=FG, font=MONO,
                         insertbackground=ACCENT, relief="flat", width=10)
            e.grid(row=i, column=2, padx=(0, 4))
            tk.Button(grid, text="Pick", bg=BORDER, fg=FG, font=SANS_SM, relief="flat",
                      command=make_picker(key, var, swatch)).grid(row=i, column=3)

        def save_custom():
            global _custom_theme
            for key, var in entries.items():
                _custom_theme[key] = var.get()
            apply_theme_colors("Custom")
            apply_ttk_theme()
            self.prefs["theme"] = "Custom"
            self.prefs["custom_theme"] = _custom_theme
            save_prefs(self.prefs)
            win.destroy()
            messagebox.showinfo("Saved", "Custom theme saved. Restart to apply fully.")

        btn_row = tk.Frame(win, bg=BG)
        btn_row.pack(padx=24, pady=(12, 20), fill="x")
        make_button(btn_row, "Save Custom Theme", save_custom, "Accent.TButton").pack(side="right")
        make_button(btn_row, "Cancel", win.destroy).pack(side="right", padx=(0, 8))

    # ── Tabs ──────────────────────────────────────────────────────────────────

    def _build_tabs(self):
        nb = ttk.Notebook(self)
        nb.pack(expand=True, fill="both")
        self.notebook = nb

        tabs = [
            ("Compose",        self._build_compose_tab),
            ("Decrypt",        self._build_decrypt_tab),
            ("File Encrypt",   self._build_file_tab),
            ("Contacts",       self._build_contacts_tab),
            ("Identities",     self._build_identities_tab),
            ("Cache Viewer",   self._build_cache_tab),
            ("Privacy Tools",  self._build_privacy_tab),
        ]
        for name, builder in tabs:
            f = tk.Frame(nb, bg=BG2, padx=20, pady=16)
            f.pack(fill="both", expand=True)
            builder(f)
            nb.add(f, text=f"  {name}  ")

    # ── Compose Tab ───────────────────────────────────────────────────────────

    def _build_compose_tab(self, f):
        f.columnconfigure(0, weight=1)
        f.rowconfigure(5, weight=1)   # message input expands
        f.rowconfigure(8, weight=1)   # ciphertext output expands

        # Row 0: method
        section_label(f, "Encryption Method").grid(row=0, column=0, sticky="w", pady=(0, 2))
        self.compose_method_var = tk.StringVar(value="PGP Key (Recipient)")
        method_combo = make_combo(f, ["PGP Key (Recipient)", "Passphrase Only (Symmetric)"],
                                  textvariable=self.compose_method_var, width=40)
        method_combo.grid(row=1, column=0, sticky="w", pady=(0, 8))
        method_combo.bind("<<ComboboxSelected>>", self._compose_method_changed)

        # Row 2: PGP from/to frame (shown/hidden by method)
        self.compose_pgp_frame = tk.Frame(f, bg=BG2)
        self.compose_pgp_frame.columnconfigure(0, weight=1)
        self.compose_pgp_frame.grid(row=2, column=0, sticky="ew")
        section_label(self.compose_pgp_frame, "From (your identity)").grid(row=0, column=0, sticky="w", pady=(0,2))
        self.compose_from_var = tk.StringVar()
        self.compose_from_combo = make_combo(self.compose_pgp_frame, [], textvariable=self.compose_from_var)
        self.compose_from_combo.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        section_label(self.compose_pgp_frame, "To (recipient)").grid(row=2, column=0, sticky="w", pady=(0,2))
        self.compose_to_var = tk.StringVar()
        self.compose_to_combo = make_combo(self.compose_pgp_frame, [], textvariable=self.compose_to_var)
        self.compose_to_combo.grid(row=3, column=0, sticky="ew", pady=(0, 8))

        # Symmetric note (hidden initially)
        self.compose_sym_frame = tk.Frame(f, bg=BG2)
        self.compose_sym_frame.columnconfigure(0, weight=1)
        tk.Label(self.compose_sym_frame,
                 text="GPG will prompt for a passphrase. Share it with the recipient through a secure channel.",
                 bg=BG2, fg=YELLOW, font=SANS_SM, anchor="w", wraplength=600
                 ).grid(row=0, column=0, sticky="w", pady=(0, 8))

        # Row 3: message label, Row 4: buttons, Row 5: message input
        section_label(f, "Message").grid(row=3, column=0, sticky="w", pady=(0, 2))
        btn_row = tk.Frame(f, bg=BG2)
        btn_row.grid(row=4, column=0, sticky="ew", pady=(0, 4))
        make_button(btn_row, "Encrypt Only", lambda: self._encrypt_only(), "Accent.TButton").pack(side="left", padx=(0, 8))
        make_button(btn_row, "Sign + Encrypt", lambda: self._sign_encrypt(), "Accent.TButton").pack(side="left", padx=(0, 8))
        make_button(btn_row, "Clear", lambda: self._clear_compose()).pack(side="right")

        c_in, self.compose_input = make_scrolled_textbox(f, height=7)
        c_in.grid(row=5, column=0, sticky="nsew", pady=(0, 8))

        # Row 6: output label, Row 7: copy button, Row 8: output
        section_label(f, "Ciphertext output").grid(row=6, column=0, sticky="w", pady=(0, 2))
        make_button(f, "Copy Ciphertext", lambda: self._copy_ciphertext()).grid(row=7, column=0, sticky="w", pady=(0, 4))
        c_out, self.compose_output = make_scrolled_textbox(f, height=7, mono=True)
        c_out.grid(row=8, column=0, sticky="nsew")

    def _compose_method_changed(self, event=None):
        method = self.compose_method_var.get()
        if method == "Passphrase Only (Symmetric)":
            self.compose_pgp_frame.grid_remove()
            self.compose_sym_frame.grid(row=2, column=0, sticky="ew")
        else:
            self.compose_sym_frame.grid_remove()
            self.compose_pgp_frame.grid(row=2, column=0, sticky="ew")

    def _get_compose_sender(self):
        idx = self.compose_from_combo.current()
        return self.secret_keys[idx] if 0 <= idx < len(self.secret_keys) else None

    def _get_compose_recipient(self):
        idx = self.compose_to_combo.current()
        return self.public_keys[idx] if 0 <= idx < len(self.public_keys) else None

    def _encrypt_only(self):
        plaintext = get_text(self.compose_input)
        if not plaintext.strip():
            messagebox.showwarning("Empty Message", "Type a message to encrypt.")
            return

        method = self.compose_method_var.get()

        if method == "Passphrase Only (Symmetric)":
            stdout, stderr, rc = run_gpg("--armor", "--symmetric", input_data=plaintext)
            _log("Symmetric encrypt (text) attempted.")
        else:
            recipient = self._get_compose_recipient()
            if not recipient:
                messagebox.showwarning("No Recipient", "Select a recipient contact first.")
                return
            rid = recipient["fingerprint"] or recipient["keyid"]
            stdout, stderr, rc = run_gpg("--armor", "--encrypt", "--recipient", rid,
                                         input_data=plaintext)
            _log(f"PGP encrypt (text) to ...{rid[-8:]} attempted.")

        if rc != 0 or not stdout.strip():
            messagebox.showerror("Encryption Failed", friendly_error(stderr))
            return
        set_text(self.compose_output, stdout)

    def _sign_encrypt(self):
        method = self.compose_method_var.get()
        if method == "Passphrase Only (Symmetric)":
            messagebox.showinfo("Not Applicable",
                                "Sign + Encrypt uses a PGP key.\n"
                                "Switch to 'PGP Key (Recipient)' mode.")
            return
        sender = self._get_compose_sender()
        recipient = self._get_compose_recipient()
        if not sender:
            messagebox.showwarning("No Sender", "Select a sender identity first.")
            return
        if not recipient:
            messagebox.showwarning("No Recipient", "Select a recipient contact first.")
            return
        plaintext = get_text(self.compose_input)
        if not plaintext.strip():
            messagebox.showwarning("Empty Message", "Type a message to encrypt.")
            return
        sid = sender["fingerprint"] or sender["keyid"]
        rid = recipient["fingerprint"] or recipient["keyid"]
        stdout, stderr, rc = run_gpg("--armor", "--local-user", sid,
                                     "--sign", "--encrypt", "--recipient", rid,
                                     input_data=plaintext)
        _log(f"Sign+encrypt (text) from ...{sid[-8:]} to ...{rid[-8:]} attempted.")
        if rc != 0 or not stdout.strip():
            messagebox.showerror("Sign + Encrypt Failed", friendly_error(stderr))
            return
        set_text(self.compose_output, stdout)

    def _clear_compose(self):
        clear_text(self.compose_input)
        clear_text(self.compose_output)

    def _copy_ciphertext(self):
        ct = get_text(self.compose_output)
        if ct.strip():
            copy_to_clipboard(self, ct)
            messagebox.showinfo("Copied", "Ciphertext copied to clipboard.")
        else:
            messagebox.showwarning("Nothing to Copy", "Encrypt a message first.")

    # ── Decrypt Tab ───────────────────────────────────────────────────────────

    def _build_decrypt_tab(self, f):
        f.columnconfigure(0, weight=1)
        f.rowconfigure(3, weight=1)   # input expands
        f.rowconfigure(7, weight=1)   # output expands

        section_label(f, "Encryption Method").grid(row=0, column=0, sticky="w", pady=(0, 2))
        self.decrypt_method_var = tk.StringVar(value="Auto-detect")
        make_combo(f, ["Auto-detect", "PGP Key", "Passphrase Only (Symmetric)"],
                   textvariable=self.decrypt_method_var, width=40).grid(row=1, column=0, sticky="w", pady=(0, 8))

        section_label(f, "Paste PGP message").grid(row=2, column=0, sticky="w", pady=(0, 2))
        c_in, self.decrypt_input = make_scrolled_textbox(f, height=7, mono=True)
        c_in.grid(row=3, column=0, sticky="nsew", pady=(0, 6))

        btn_row = tk.Frame(f, bg=BG2)
        btn_row.grid(row=4, column=0, sticky="ew", pady=(0, 6))
        make_button(btn_row, "Decrypt", lambda: self._decrypt(), "Accent.TButton").pack(side="left", padx=(0, 8))
        make_button(btn_row, "Clear All", lambda: self._clear_decrypt()).pack(side="right")

        sig_frame = tk.Frame(f, bg=BG3, padx=12, pady=8)
        sig_frame.grid(row=5, column=0, sticky="ew", pady=(0, 6))
        tk.Label(sig_frame, text="SIGNATURE STATUS", bg=BG3, fg=ACCENT,
                 font=(*SANS_SM, "bold"), anchor="w").pack(fill="x")
        self.sig_status_label = tk.Label(sig_frame, text="—", bg=BG3, fg=FG2, font=SANS, anchor="w")
        self.sig_status_label.pack(fill="x")
        self.sig_signer_label = tk.Label(sig_frame, text="", bg=BG3, fg=FG2, font=SANS_SM, anchor="w")
        self.sig_signer_label.pack(fill="x")

        section_label(f, "Decrypted plaintext").grid(row=6, column=0, sticky="w", pady=(0, 2))
        c_out, self.decrypt_output = make_scrolled_textbox(f, height=7)
        c_out.grid(row=7, column=0, sticky="nsew", pady=(0, 4))
        tk.Label(f, text="⚠  Decrypted text is shown here only. It is never saved or logged.",
                 bg=BG2, fg=FG2, font=SANS_SM).grid(row=8, column=0, sticky="w")

    def _decrypt(self):
        armored = get_text(self.decrypt_input)
        if not armored.strip():
            messagebox.showwarning("Empty", "Paste a PGP message to decrypt.")
            return
        stdout, stderr, rc = run_gpg("--decrypt", input_data=armored)
        _log("Decrypt (text) attempted.")
        if rc != 0 and not stdout.strip():
            clear_text(self.decrypt_output)
            self.sig_status_label.config(text="Decryption failed", fg=RED)
            self.sig_signer_label.config(text="")
            messagebox.showerror("Decryption Failed", friendly_error(stderr))
            return
        set_text(self.decrypt_output, stdout)
        status, color, signer = parse_sig_status(stderr)
        self.sig_status_label.config(text=f"Signature: {status}", fg=color)
        self.sig_signer_label.config(text=f"Signed by: {signer}" if signer else "", fg=FG2)

    def _clear_decrypt(self):
        clear_text(self.decrypt_input)
        clear_text(self.decrypt_output)
        self.sig_status_label.config(text="—", fg=FG2)
        self.sig_signer_label.config(text="")

    # ── File Encrypt Tab ──────────────────────────────────────────────────────

    def _build_file_tab(self, f):
        f.columnconfigure(0, weight=1)
        f.rowconfigure(6, weight=1)   # status output expands

        tk.Label(f, text="Encrypt or decrypt any file (PDF, image, zip, etc.)",
                 bg=BG2, fg=FG2, font=SANS_SM, anchor="w").grid(row=0, column=0, sticky="w", pady=(0, 8))

        section_label(f, "Encryption Method").grid(row=1, column=0, sticky="w", pady=(0, 2))
        self.file_method_var = tk.StringVar(value="Passphrase Only (Symmetric)")
        method_combo = make_combo(f, ["Passphrase Only (Symmetric)", "PGP Key (Recipient)"],
                                  textvariable=self.file_method_var, width=40)
        method_combo.grid(row=2, column=0, sticky="w", pady=(0, 6))
        method_combo.bind("<<ComboboxSelected>>", self._file_method_changed)

        self.file_pgp_frame = tk.Frame(f, bg=BG2)
        self.file_pgp_frame.columnconfigure(0, weight=1)
        section_label(self.file_pgp_frame, "Recipient").pack(fill="x", pady=(0, 2))
        self.file_to_var = tk.StringVar()
        self.file_to_combo = make_combo(self.file_pgp_frame, [], textvariable=self.file_to_var)
        self.file_to_combo.pack(fill="x", pady=(0, 8))

        section_label(f, "Select File").grid(row=3, column=0, sticky="w", pady=(0, 2))
        file_row = tk.Frame(f, bg=BG2)
        file_row.grid(row=4, column=0, sticky="ew", pady=(0, 8))
        make_button(file_row, "Choose File…", lambda: self._pick_file()).pack(side="left", padx=(0, 12))
        self._file_label = tk.Label(file_row, text="No file selected.", bg=BG2, fg=FG2, font=SANS_SM, anchor="w")
        self._file_label.pack(side="left")

        btn_row = tk.Frame(f, bg=BG2)
        btn_row.grid(row=5, column=0, sticky="ew", pady=(0, 8))
        make_button(btn_row, "Encrypt File → .gpg", lambda: self._encrypt_file(), "Accent.TButton").pack(side="left", padx=(0, 8))
        make_button(btn_row, "Decrypt .gpg File", lambda: self._decrypt_file(), "Accent.TButton").pack(side="left")

        section_label(f, "Status").grid(row=6, column=0, sticky="w", pady=(0, 2))
        c_status, self.file_encrypt_output = make_scrolled_textbox(f, height=6, mono=True)
        c_status.grid(row=7, column=0, sticky="nsew", pady=(0, 6))
        self.file_decrypt_status = self.file_encrypt_output

        tk.Label(f,
                 text="Output saved alongside original: filename.gpg for encrypt, filename for decrypt.",
                 bg=BG2, fg=FG2, font=SANS_SM, justify="left", anchor="w", wraplength=640
                 ).grid(row=8, column=0, sticky="w")

    def _file_method_changed(self, event=None):
        if self.file_method_var.get() == "PGP Key (Recipient)":
            self.file_pgp_frame.grid(row=3, column=0, sticky="ew", pady=(0, 6))
            # shift other rows down
            for w, r in [(self._file_label.master, 4), (self.file_encrypt_output.master.master, 7)]:
                try: w.grid(row=r+1)
                except: pass
        else:
            self.file_pgp_frame.grid_remove()

    def _pick_file(self):
        path = filedialog.askopenfilename(title="Select File to Encrypt or Decrypt")
        if not path:
            return
        self._file_path = path
        size = os.path.getsize(path)
        size_str = f"{size:,} bytes" if size < 1_000_000 else f"{size/1_048_576:.1f} MB"
        self._file_label.config(text=f"{os.path.basename(path)}  ({size_str})", fg=FG)
        _log(f"File selected: {os.path.basename(path)}")

    def _encrypt_file(self):
        if not self._file_path:
            messagebox.showwarning("No File", "Choose a file first.")
            return
        out_path = self._file_path + ".gpg"
        method = self.file_method_var.get()

        if method == "Passphrase Only (Symmetric)":
            args = ["--armor", "--symmetric", "--output", out_path, self._file_path]
        else:
            idx = self.file_to_combo.current()
            if idx < 0 or idx >= len(self.public_keys):
                messagebox.showwarning("No Recipient", "Select a recipient.")
                return
            key = self.public_keys[idx]
            rid = key["fingerprint"] or key["keyid"]
            args = ["--armor", "--encrypt", "--recipient", rid, "--output", out_path, self._file_path]

        try:
            result = subprocess.run(
                ["gpg"] + args,
                capture_output=True, text=True, env=get_env()
            )
            _log(f"File encrypt attempted: {os.path.basename(self._file_path)}")
            if result.returncode != 0:
                set_text(self.file_encrypt_output,
                         f"Encryption failed:\n{result.stderr.strip()}")
            else:
                set_text(self.file_encrypt_output,
                         f"✓ Encrypted successfully.\n\nOutput: {out_path}\n\n"
                         f"GPG output:\n{result.stderr.strip()}")
        except Exception as e:
            set_text(self.file_encrypt_output, f"Error: {e}")

    def _decrypt_file(self):
        if not self._file_path:
            messagebox.showwarning("No File", "Choose a .gpg file first.")
            return
        if not self._file_path.endswith(".gpg"):
            messagebox.showwarning("Not a .gpg File",
                                   "Select a file ending in .gpg to decrypt.")
            return
        out_path = self._file_path[:-4]  # strip .gpg

        # Handle existing output file entirely in Python before calling gpg.
        # We delete the file ourselves if the user confirms, then pass --yes so
        # gpg never tries to prompt interactively (which hangs in a GUI context).
        if os.path.exists(out_path):
            if not messagebox.askyesno("Overwrite?",
                                       f"{os.path.basename(out_path)} already exists. Overwrite?"):
                return
            try:
                os.remove(out_path)
            except Exception as e:
                messagebox.showerror("Cannot Overwrite",
                                     f"Could not remove existing file:\n{e}")
                return

        try:
            result = subprocess.run(
                ["gpg", "--yes", "--output", out_path, "--decrypt", self._file_path],
                capture_output=True, text=True, env=get_env()
            )
            _log(f"File decrypt attempted: {os.path.basename(self._file_path)}")
            if result.returncode != 0:
                set_text(self.file_encrypt_output,
                         f"Decryption failed:\n{result.stderr.strip()}")
            else:
                set_text(self.file_encrypt_output,
                         f"✓ Decrypted successfully.\n\nOutput: {out_path}\n\n"
                         f"GPG output:\n{result.stderr.strip()}")
        except Exception as e:
            set_text(self.file_encrypt_output, f"Error: {e}")

    # ── Contacts Tab ──────────────────────────────────────────────────────────

    def _build_contacts_tab(self, f):
        f.columnconfigure(0, weight=1)
        f.rowconfigure(1, weight=1)   # contacts list
        f.rowconfigure(6, weight=1)   # import box

        section_label(f, "Public keys / contacts").grid(row=0, column=0, sticky="w", pady=(0, 2))

        list_frame = tk.Frame(f, bg=BG3)
        list_frame.grid(row=1, column=0, sticky="nsew", pady=(0, 6))
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)
        self.contacts_list = tk.Listbox(
            list_frame, bg=BG3, fg=FG, selectbackground=ACCENT, selectforeground=BG,
            relief="flat", bd=0, font=MONO, activestyle="none")
        contacts_sb = ttk.Scrollbar(list_frame, orient="vertical", command=self.contacts_list.yview)
        self.contacts_list.configure(yscrollcommand=contacts_sb.set)
        self.contacts_list.grid(row=0, column=0, sticky="nsew")
        contacts_sb.grid(row=0, column=1, sticky="ns")

        btn_row = tk.Frame(f, bg=BG2)
        btn_row.grid(row=2, column=0, sticky="ew", pady=(0, 8))
        make_button(btn_row, "Show Fingerprint", lambda: self._show_contact_fp()).pack(side="left", padx=(0, 8))
        make_button(btn_row, "Refresh Keys", lambda: self._refresh_all_keys()).pack(side="left")

        ttk.Separator(f, orient="horizontal").grid(row=3, column=0, sticky="ew", pady=(0, 8))

        section_label(f, "Import public key").grid(row=4, column=0, sticky="w", pady=(0, 2))
        make_button(f, "Import Key", lambda: self._import_key(), "Accent.TButton").grid(row=5, column=0, sticky="w", pady=(0, 4))
        c_imp, self.import_input = make_scrolled_textbox(f, height=6, mono=True)
        c_imp.grid(row=6, column=0, sticky="nsew", pady=(0, 6))
        self.import_result = tk.Label(f, text="", bg=BG2, fg=GREEN, font=SANS_SM,
                                      anchor="w", wraplength=600, justify="left")
        self.import_result.grid(row=7, column=0, sticky="w")

    def _show_contact_fp(self):
        sel = self.contacts_list.curselection()
        if not sel:
            messagebox.showwarning("No Selection", "Select a contact first.")
            return
        key = self.public_keys[sel[0]]
        fp = format_fingerprint(key.get("fingerprint", "")) or "(not available)"
        uid = key["uids"][0] if key["uids"] else "(no UID)"
        _show_fp_dialog(self, uid, fp)

    def _import_key(self):
        pem = get_text(self.import_input)
        if not pem.strip():
            messagebox.showwarning("Empty", "Paste a public key block to import.")
            return
        stdout, stderr, rc = run_gpg("--import", input_data=pem)
        _log("Key import attempted.")
        if rc != 0:
            messagebox.showerror("Import Failed", friendly_error(stderr))
            return
        clear_text(self.import_input)
        self._refresh_all_keys()
        combined = (stdout + "\n" + stderr).strip()
        lines = [l for l in combined.splitlines() if l.strip()]
        self.import_result.config(
            text="\n".join(lines[:6]) +
                 "\n\n⚠  Verify the fingerprint with the person through a trusted channel before relying on this key.",
            fg=GREEN)

    # ── Identities Tab ────────────────────────────────────────────────────────

    def _build_identities_tab(self, f):
        f.columnconfigure(0, weight=1)
        f.rowconfigure(1, weight=1)

        section_label(f, "Your secret keys").grid(row=0, column=0, sticky="w", pady=(0, 2))

        list_frame = tk.Frame(f, bg=BG3)
        list_frame.grid(row=1, column=0, sticky="nsew", pady=(0, 6))
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)
        self.identities_list = tk.Listbox(
            list_frame, bg=BG3, fg=FG, selectbackground=ACCENT, selectforeground=BG,
            relief="flat", bd=0, font=MONO, activestyle="none")
        id_sb = ttk.Scrollbar(list_frame, orient="vertical", command=self.identities_list.yview)
        self.identities_list.configure(yscrollcommand=id_sb.set)
        self.identities_list.grid(row=0, column=0, sticky="nsew")
        id_sb.grid(row=0, column=1, sticky="ns")

        btn_row = tk.Frame(f, bg=BG2)
        btn_row.grid(row=2, column=0, sticky="ew", pady=(0, 12))
        make_button(btn_row, "Show Fingerprint", lambda: self._show_identity_fp()).pack(side="left", padx=(0, 8))
        make_button(btn_row, "Refresh Keys", lambda: self._refresh_all_keys()).pack(side="left")

        tk.Label(f, text=(
            "These are the private keys stored in your local GPG keyring.\n"
            "Select one as your 'From' identity in the Compose tab."
        ), bg=BG2, fg=FG2, font=SANS_SM, justify="left", anchor="w").grid(row=3, column=0, sticky="w")

    def _show_identity_fp(self):
        sel = self.identities_list.curselection()
        if not sel:
            messagebox.showwarning("No Selection", "Select an identity first.")
            return
        key = self.secret_keys[sel[0]]
        fp = format_fingerprint(key.get("fingerprint", "")) or "(not available)"
        uid = key["uids"][0] if key["uids"] else "(no UID)"
        _show_fp_dialog(self, uid, fp)

    # ── Cache Viewer Tab ──────────────────────────────────────────────────────

    def _build_cache_tab(self, f):
        f.columnconfigure(0, weight=1)
        f.rowconfigure(1, weight=2)   # session log
        f.rowconfigure(5, weight=2)   # shell history
        f.rowconfigure(8, weight=1)   # agent status

        section_label(f, "App Session Log (this run only)").grid(row=0, column=0, sticky="w", pady=(0, 2))

        c_slog, self.session_log_box = make_scrolled_textbox(f, height=6, mono=True)
        c_slog.grid(row=1, column=0, sticky="nsew", pady=(0, 4))

        br1 = tk.Frame(f, bg=BG2)
        br1.grid(row=2, column=0, sticky="ew", pady=(0, 8))
        make_button(br1, "Refresh", lambda: self._refresh_session_log()).pack(side="left", padx=(0, 8))
        make_button(br1, "Clear Log", lambda: self._clear_session_log()).pack(side="left")

        ttk.Separator(f, orient="horizontal").grid(row=3, column=0, sticky="ew", pady=(0, 8))

        section_label(f, "Shell History (read-only, gpg commands hidden)").grid(row=4, column=0, sticky="w", pady=(0, 2))
        c_shist, self.shell_history_box = make_scrolled_textbox(f, height=8, mono=True)
        c_shist.grid(row=5, column=0, sticky="nsew", pady=(0, 4))

        br2 = tk.Frame(f, bg=BG2)
        br2.grid(row=6, column=0, sticky="ew", pady=(0, 8))
        make_button(br2, "Load Shell History", lambda: self._load_shell_history()).pack(side="left", padx=(0, 8))
        make_button(br2, "Clear View", lambda: clear_text(self.shell_history_box)).pack(side="left")

        ttk.Separator(f, orient="horizontal").grid(row=7, column=0, sticky="ew", pady=(0, 8))

        section_label(f, "GPG Agent Status").grid(row=7, column=0, sticky="w", pady=(0, 2))
        c_agent, self.agent_info_box = make_scrolled_textbox(f, height=4, mono=True)
        c_agent.grid(row=8, column=0, sticky="nsew", pady=(0, 4))
        make_button(f, "Check Agent Status", lambda: self._check_agent_status()).grid(row=9, column=0, sticky="w")

        self._refresh_session_log()

    def _build_privacy_tab(self, f):
        f.columnconfigure(0, weight=1)

        section_label(f, "Application").grid(row=0, column=0, sticky="w", pady=(0, 6))
        make_button(f, "Clear All App Fields", lambda: self._clear_all_fields()).grid(row=1, column=0, sticky="w", pady=(0, 4))
        make_button(f, "Clear Clipboard", lambda: clear_clipboard(self)).grid(row=2, column=0, sticky="w", pady=(0, 12))

        ttk.Separator(f, orient="horizontal").grid(row=3, column=0, sticky="ew", pady=(0, 12))

        section_label(f, "GPG Agent").grid(row=4, column=0, sticky="w", pady=(0, 6))
        make_button(f, "Clear GPG Cache  (kills agent — prompts passphrase next use)",
                    self._kill_agent).grid(row=5, column=0, sticky="w", pady=(0, 4))
        make_button(f, "Reload GPG Agent",
                    lambda: self._reload_agent()).grid(row=6, column=0, sticky="w", pady=(0, 8))

        self.agent_status = tk.Label(f, text="", bg=BG2, fg=GREEN, font=SANS_SM, anchor="w")
        self.agent_status.grid(row=7, column=0, sticky="w", pady=(0, 12))

        ttk.Separator(f, orient="horizontal").grid(row=8, column=0, sticky="ew", pady=(0, 12))

        section_label(f, "Shell History  (advanced / destructive)").grid(row=9, column=0, sticky="w", pady=(0, 6))
        tk.Label(f,
                 text="Removes ~/.zsh_history and session history files. Permanently deletes your command history.",
                 bg=BG2, fg=YELLOW, font=SANS_SM, justify="left", anchor="w"
                 ).grid(row=10, column=0, sticky="w", pady=(0, 6))
        make_button(f, "Clear zsh History…", lambda: self._clear_shell_history(), "Danger.TButton"
                    ).grid(row=11, column=0, sticky="w", pady=(0, 12))

        ttk.Separator(f, orient="horizontal").grid(row=12, column=0, sticky="ew", pady=(0, 12))

        section_label(f, "Setup / Dependencies").grid(row=13, column=0, sticky="w", pady=(0, 6))
        make_button(f, "Re-run Dependency Check…", lambda: self._rerun_setup()).grid(row=14, column=0, sticky="w", pady=(0, 12))

        tk.Label(f,
                 text="If passphrase prompts fail, add this to ~/.zshrc:\n  export GPG_TTY=$(tty)",
                 bg=BG2, fg=FG2, font=MONO, justify="left", anchor="w"
                 ).grid(row=15, column=0, sticky="w")

    def _clear_all_fields(self):
        for attr in ("compose_input", "compose_output", "decrypt_input", "decrypt_output",
                     "import_input", "file_encrypt_output"):
            w = getattr(self, attr, None)
            if w:
                try:
                    clear_text(w)
                except Exception:
                    pass
        self.sig_status_label.config(text="—", fg=FG2)
        self.sig_signer_label.config(text="")
        if hasattr(self, "agent_status"):
            self.agent_status.config(text="")
        _log("All fields cleared.")

    # ── Cache Viewer ──────────────────────────────────────────────────────────

    def _refresh_session_log(self):
        log_text = "\n".join(_session_log) if _session_log else "(no activity yet this session)"
        set_text(self.session_log_box, log_text)

    def _clear_session_log(self):
        _session_log.clear()
        set_text(self.session_log_box, "(session log cleared)")

    def _load_shell_history(self):
        history_path = os.path.expanduser("~/.zsh_history")
        if not os.path.exists(history_path):
            set_text(self.shell_history_box, "~/.zsh_history not found.")
            return
        try:
            with open(history_path, "rb") as hf:
                raw = hf.read()
            text = raw.decode("utf-8", errors="replace")
            lines = text.splitlines()
            filtered = []
            for line in lines:
                ll = line.lower()
                if "gpg" in ll or "passphrase" in ll or "secret" in ll:
                    filtered.append("[gpg command — hidden for security]")
                else:
                    if line.startswith(": ") and ";" in line:
                        line = line.split(";", 1)[-1]
                    filtered.append(line)
            display = "\n".join(filtered[-200:])
            set_text(self.shell_history_box,
                     f"Last {min(200, len(filtered))} entries from ~/.zsh_history "
                     f"(gpg commands hidden):\n\n{display}")
        except Exception as e:
            set_text(self.shell_history_box, f"Error reading history: {e}")

    def _check_agent_status(self):
        try:
            result = subprocess.run(
                ["gpgconf", "--list-dirs"],
                capture_output=True, text=True, env=get_env()
            )
            set_text(self.agent_info_box, result.stdout or result.stderr or "(no output)")
        except Exception as e:
            set_text(self.agent_info_box, f"Error: {e}")

    def _kill_agent(self):
        try:
            subprocess.run(["gpgconf", "--kill", "gpg-agent"],
                           capture_output=True, env=get_env())
            self.agent_status.config(
                text="GPG agent killed. Passphrase will be re-prompted on next operation.", fg=GREEN)
            _log("GPG agent killed.")
        except Exception as e:
            self.agent_status.config(text=f"Error: {e}", fg=RED)

    def _reload_agent(self):
        try:
            subprocess.run(["gpgconf", "--reload", "gpg-agent"],
                           capture_output=True, env=get_env())
            self.agent_status.config(text="GPG agent reloaded.", fg=GREEN)
            _log("GPG agent reloaded.")
        except Exception as e:
            self.agent_status.config(text=f"Error: {e}", fg=RED)

    def _clear_shell_history(self):
        if platform.system() not in ("Darwin", "Linux"):
            messagebox.showinfo("Not Supported", "Shell history clearing is only supported on macOS/Linux.")
            return
        if not messagebox.askyesno("Clear Shell History",
                                   "This will remove ~/.zsh_history and any zsh session history files.\n\n"
                                   "This permanently deletes your shell command history. Continue?",
                                   icon="warning"):
            return
        home = os.path.expanduser("~")
        try:
            hf = os.path.join(home, ".zsh_history")
            if os.path.exists(hf):
                os.remove(hf)
            sd = os.path.join(home, ".zsh_sessions")
            if os.path.isdir(sd):
                for fn in os.listdir(sd):
                    if ".history" in fn:
                        os.remove(os.path.join(sd, fn))
            messagebox.showinfo("Done", "Shell history files removed.")
            _log("Shell history cleared.")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _rerun_setup(self):
        SetupWindow(self, lambda v=None: None)

    # ── Key Refresh ───────────────────────────────────────────────────────────

    def _refresh_all_keys(self):
        self.secret_keys = list_secret_keys()
        self.public_keys  = list_public_keys()

        sec_labels = [format_key_label(k) for k in self.secret_keys]
        pub_labels = [format_key_label(k) for k in self.public_keys]

        self.compose_from_combo["values"] = sec_labels
        self.compose_to_combo["values"]   = pub_labels
        if sec_labels: self.compose_from_combo.current(0)
        if pub_labels: self.compose_to_combo.current(0)

        self.contacts_list.delete(0, tk.END)
        for lbl in pub_labels:
            self.contacts_list.insert(tk.END, lbl)

        self.identities_list.delete(0, tk.END)
        for lbl in sec_labels:
            self.identities_list.insert(tk.END, lbl)

        self.file_to_combo["values"] = pub_labels
        if pub_labels:
            self.file_to_combo.current(0)

        _log(f"Keys refreshed: {len(self.secret_keys)} secret, {len(self.public_keys)} public.")


# ─── Fingerprint Dialog ───────────────────────────────────────────────────────

def _show_fp_dialog(parent, uid, fp_formatted):
    win = tk.Toplevel(parent)
    win.title("Key Fingerprint")
    win.configure(bg=BG)
    win.resizable(False, False)
    win.grab_set()

    tk.Label(win, text="Key Fingerprint", bg=BG, fg=ACCENT2,
             font=("Helvetica Neue", 13, "bold")).pack(padx=24, pady=(20, 4), anchor="w")
    tk.Label(win, text=uid, bg=BG, fg=FG, font=SANS).pack(padx=24, pady=(0, 12), anchor="w")

    fp_frame = tk.Frame(win, bg=BG3, padx=16, pady=12)
    fp_frame.pack(padx=24, pady=(0, 12), fill="x")
    tk.Label(fp_frame, text=fp_formatted, bg=BG3, fg=ACCENT2, font=(*MONO, "bold")).pack(anchor="w")

    tk.Label(win,
             text="Verify this fingerprint with the person through a trusted\n"
                  "channel (phone, in person, Signal) before relying on this key.",
             bg=BG, fg=FG2, font=SANS_SM, justify="left").pack(padx=24, pady=(0, 16), anchor="w")
    ttk.Button(win, text="Close", command=win.destroy).pack(padx=24, pady=(0, 20), anchor="e")


# ─── Entry Point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app = GPGApp()
    app.mainloop()
