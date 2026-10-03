"""
Five - an interrupt tool based on Mel Robbins' 5-second rule.

Press Ctrl+Alt+5 anywhere. Type the task you are avoiding (or leave it empty
for a random one). A full-screen window counts 5, 4, 3, 2, 1, GO
and then shows your task.

    Done / Enter  -> closes the window and logs "done" in log.csv
    Escape        -> closes the window and logs "skipped" in log.csv

Run "python five.py --stats" to see your stats in the terminal.

Everything stays on this computer: the app never uses the internet.
"""

import csv
import datetime as dt
import os
import queue
import random
import subprocess
import sys
import threading
import traceback
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
ACTIONS_FILE = APP_DIR / "actions.txt"
CONFIG_FILE = APP_DIR / "config.txt"
LOG_FILE = APP_DIR / "log.csv"
ERROR_FILE = APP_DIR / "five_error.log"

IS_WINDOWS = sys.platform == "win32"

DEFAULT_CONFIG = {
    "hotkey": "ctrl+alt+5",
    "countdown_seconds": "5",
    "close_browser": "false",
    "autostart": "true",
    "ask_task": "true",
}

DEFAULT_ACTIONS = [
    "Close the laptop and walk the dog",
    "Text Tito",
    "Go to the gym",
    "Open the BancoEstado folder",
]

LOG_HEADER = ["date", "time", "result", "action"]

# Colors and fonts for the full-screen window
BG = "#0d0d0d"
FG = "#f2f2f2"
ACCENT = "#ffb000"
FONT = "Segoe UI"


# --------------------------------------------------------------------------
# Files: config.txt, actions.txt, log.csv
# --------------------------------------------------------------------------

def log_error(message):
    """pythonw has no console, so errors are written to five_error.log."""
    with open(ERROR_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{dt.datetime.now():%Y-%m-%d %H:%M:%S}] {message}\n")


def ensure_files():
    """Create config.txt and actions.txt with examples if they are missing."""
    if not CONFIG_FILE.exists():
        lines = [
            "# Five settings. Change the value after the = sign and restart Five.",
            "# Lines that start with # are ignored.",
            "",
            "# Global hotkey. Examples: ctrl+alt+5, ctrl+shift+f, ctrl+alt+f9",
            f"hotkey={DEFAULT_CONFIG['hotkey']}",
            "",
            "# How many seconds the countdown lasts (5 = 5, 4, 3, 2, 1, GO)",
            f"countdown_seconds={DEFAULT_CONFIG['countdown_seconds']}",
            "",
            "# true = close all Chrome and Edge windows at GO",
            f"close_browser={DEFAULT_CONFIG['close_browser']}",
            "",
            "# true = start Five automatically when Windows starts",
            f"autostart={DEFAULT_CONFIG['autostart']}",
            "",
            "# true = ask you to type your task before the countdown",
            "# (leave it empty and press Enter to get a random action from actions.txt)",
            "# false = always pick a random action from actions.txt",
            f"ask_task={DEFAULT_CONFIG['ask_task']}",
        ]
        CONFIG_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    if not ACTIONS_FILE.exists():
        ACTIONS_FILE.write_text("\n".join(DEFAULT_ACTIONS) + "\n", encoding="utf-8")


def load_config():
    config = dict(DEFAULT_CONFIG)
    try:
        # utf-8-sig also accepts files saved by Notepad with a BOM
        for line in CONFIG_FILE.read_text(encoding="utf-8-sig").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            config[key.strip().lower()] = value.strip()
    except OSError:
        pass
    return config


def config_bool(config, key):
    return config.get(key, "").strip().lower() in ("true", "yes", "1", "si", "sí")


def config_seconds(config):
    try:
        return max(1, min(60, int(config.get("countdown_seconds", "5"))))
    except ValueError:
        return 5


def load_actions():
    try:
        text = ACTIONS_FILE.read_text(encoding="utf-8-sig")
    except OSError:
        text = ""
    actions = [l.strip() for l in text.splitlines() if l.strip() and not l.strip().startswith("#")]
    return actions or ["Add your actions to actions.txt"]


def append_log(result, action, when=None):
    when = when or dt.datetime.now()
    is_new = not LOG_FILE.exists() or LOG_FILE.stat().st_size == 0
    # The BOM at the start of a new file lets Excel show accents correctly
    with open(LOG_FILE, "a", encoding="utf-8", newline="") as f:
        if is_new:
            f.write("﻿")
        writer = csv.writer(f)
        if is_new:
            writer.writerow(LOG_HEADER)
        writer.writerow([when.strftime("%Y-%m-%d"), when.strftime("%H:%M:%S"), result, action])


def read_log():
    rows = []
    if not LOG_FILE.exists():
        return rows
    with open(LOG_FILE, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            try:
                day = dt.date.fromisoformat(row["date"])
            except (KeyError, TypeError, ValueError):
                continue
            rows.append((day, (row.get("result") or "").strip().lower()))
    return rows


# --------------------------------------------------------------------------
# Stats (--stats)
# --------------------------------------------------------------------------

def compute_stats(rows, today=None):
    today = today or dt.date.today()
    week_start = today - dt.timedelta(days=today.weekday())  # Monday
    this_week = [r for d, r in rows if week_start <= d <= today]
    done_days = {d for d, r in rows if r == "done"}

    # Streak: days in a row with at least one "done". If today has no
    # "done" yet, the streak is still alive and counts from yesterday.
    day = today if today in done_days else today - dt.timedelta(days=1)
    streak = 0
    while day in done_days:
        streak += 1
        day -= dt.timedelta(days=1)

    return {
        "week_start": week_start,
        "uses": len(this_week),
        "done": this_week.count("done"),
        "skipped": this_week.count("skipped"),
        "streak": streak,
        "total": len(rows),
    }


def print_stats(pause=False):
    s = compute_stats(read_log())
    print()
    print("  FIVE - stats")
    print("  ------------------------------------------")
    print(f"  This week (since Monday {s['week_start']:%Y-%m-%d}):")
    print(f"    Times used : {s['uses']}")
    print(f"    Done       : {s['done']}")
    print(f"    Skipped    : {s['skipped']}")
    print()
    print(f"  Current streak : {s['streak']} day(s) in a row with a 'Done'")
    print(f"  All-time uses  : {s['total']}")
    print()
    if pause:
        input("  Press Enter to close this window...")


# --------------------------------------------------------------------------
# Windows helpers: autostart, closing browsers, opening files
# --------------------------------------------------------------------------

def pythonw_path():
    exe = Path(sys.executable)
    candidate = exe.with_name("pythonw.exe")
    return candidate if candidate.exists() else exe


def python_console_path():
    exe = Path(sys.executable)
    candidate = exe.with_name("python.exe")
    return candidate if candidate.exists() else exe


def set_autostart(enabled):
    """Add or remove Five from 'Start with Windows' (current user only)."""
    if not IS_WINDOWS:
        return
    import winreg
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as key:
        if enabled:
            command = f'"{pythonw_path()}" "{Path(__file__).resolve()}"'
            winreg.SetValueEx(key, "Five", 0, winreg.REG_SZ, command)
        else:
            try:
                winreg.DeleteValue(key, "Five")
            except FileNotFoundError:
                pass


def close_browsers():
    """Politely close every Chrome and Edge window."""
    if IS_WINDOWS:
        cmd = ["taskkill", "/IM", "chrome.exe", "/IM", "msedge.exe"]
        flags = subprocess.CREATE_NO_WINDOW
    else:
        cmd = ["pkill", "-x", "chrome|msedge|google-chrome|microsoft-edge"]
        flags = 0
    try:
        subprocess.run(cmd, capture_output=True, timeout=10, creationflags=flags)
    except Exception as exc:  # never let this break the countdown
        log_error(f"close_browsers failed: {exc}")


def open_file(path):
    if IS_WINDOWS:
        os.startfile(str(path))
    else:
        subprocess.Popen(["xdg-open", str(path)])


def open_stats_window():
    args = [str(python_console_path()), str(Path(__file__).resolve()), "--stats", "--pause"]
    if IS_WINDOWS:
        subprocess.Popen(args, creationflags=subprocess.CREATE_NEW_CONSOLE)
    else:
        subprocess.Popen(["x-terminal-emulator", "-e"] + args)


# --------------------------------------------------------------------------
# Only one copy of Five may run at a time
# --------------------------------------------------------------------------

_instance_lock = None


def acquire_single_instance():
    global _instance_lock
    if IS_WINDOWS:
        import ctypes
        _instance_lock = ctypes.windll.kernel32.CreateMutexW(None, False, "Local\\FiveApp5SecondRule")
        return ctypes.windll.kernel32.GetLastError() != 183  # ERROR_ALREADY_EXISTS
    import fcntl
    import tempfile
    _instance_lock = open(Path(tempfile.gettempdir()) / "five_app.lock", "w")
    try:
        fcntl.flock(_instance_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return True
    except OSError:
        return False


# --------------------------------------------------------------------------
# Global hotkey (works even when another app is focused)
# --------------------------------------------------------------------------

class GlobalHotkey:
    """
    Listens to the whole keyboard with pynput and calls `callback` when the
    combination from config.txt is pressed. The key is matched by its
    character AND by its key code, because Windows often reports no
    character while Ctrl is held down.
    """

    MODIFIERS = {"ctrl", "alt", "shift", "win"}

    def __init__(self, combo, callback):
        from pynput import keyboard
        self.kb = keyboard
        self.callback = callback
        parts = [p.strip().lower() for p in combo.split("+") if p.strip()]
        self.required = {p for p in parts if p in self.MODIFIERS}
        keys = [p for p in parts if p not in self.MODIFIERS]
        if len(keys) != 1:
            raise ValueError(f"Invalid hotkey '{combo}'. Use something like ctrl+alt+5")
        self.target = keys[0]
        self.held = set()
        self.listener = keyboard.Listener(on_press=self._on_press, on_release=self._on_release)

    def start(self):
        self.listener.start()

    def stop(self):
        self.listener.stop()

    def _modifier_names(self, key):
        K = self.kb.Key
        names = {
            K.ctrl: {"ctrl"}, K.ctrl_l: {"ctrl"}, K.ctrl_r: {"ctrl"},
            K.alt: {"alt"}, K.alt_l: {"alt"}, K.alt_r: {"alt"},
            K.alt_gr: {"ctrl", "alt"},  # AltGr = Ctrl+Alt on Windows
            K.shift: {"shift"}, K.shift_l: {"shift"}, K.shift_r: {"shift"},
            K.cmd: {"win"}, K.cmd_l: {"win"}, K.cmd_r: {"win"},
        }
        return names.get(key, set())

    def _is_target(self, key):
        t = self.target
        if len(t) > 1:  # named key such as f9
            return key == getattr(self.kb.Key, t, None)
        char = getattr(key, "char", None)
        if char and char.lower() == t:
            return True
        vk = getattr(key, "vk", None)
        if vk is None:
            return False
        if IS_WINDOWS:
            codes = {ord(t.upper())}
            if t.isdigit():
                codes.add(0x60 + int(t))  # numeric keypad
            return vk in codes
        return vk == ord(t)

    def _on_press(self, key):
        try:
            mods = self._modifier_names(key)
            if mods:
                self.held |= {(m, key) for m in mods}
                return
            if self._is_target(key) and self.required == {m for m, _ in self.held}:
                self.callback()
        except Exception:
            log_error(traceback.format_exc())

    def _on_release(self, key):
        self.held = {(m, k) for m, k in self.held if k != key}


# --------------------------------------------------------------------------
# System tray icon
# --------------------------------------------------------------------------

def make_icon_image():
    from PIL import Image, ImageDraw, ImageFont
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse((2, 2, 62, 62), fill=(13, 13, 13, 255), outline=(255, 176, 0, 255), width=4)
    try:
        font = ImageFont.truetype("arialbd.ttf" if IS_WINDOWS else "DejaVuSans-Bold.ttf", 40)
    except OSError:
        font = ImageFont.load_default()
    d.text((32, 33), "5", fill=(255, 176, 0, 255), font=font, anchor="mm")
    return img


def start_tray(events):
    import pystray
    menu = pystray.Menu(
        pystray.MenuItem("Open stats", lambda: events.put("stats")),
        pystray.MenuItem("Edit actions", lambda: events.put("edit")),
        pystray.MenuItem("Quit", lambda: events.put("quit")),
    )
    icon = pystray.Icon("Five", make_icon_image(), "Five - Ctrl+Alt+5", menu)
    icon.run_detached()
    return icon


# --------------------------------------------------------------------------
# The full-screen countdown window
# --------------------------------------------------------------------------

class FiveApp:
    def __init__(self):
        import tkinter as tk
        self.tk = tk
        self.config = load_config()
        self.events = queue.Queue()
        self.window = None
        self.root = tk.Tk()
        self.root.withdraw()  # the main Tk window stays hidden
        self.root.title("Five")
        self.tray = None
        self.hotkey = None

    # Called from the keyboard thread: never touch tkinter here
    def request_show(self):
        self.events.put("show")

    def run(self):
        self.hotkey = GlobalHotkey(self.config.get("hotkey", "ctrl+alt+5"), self.request_show)
        self.hotkey.start()
        try:
            self.tray = start_tray(self.events)
        except Exception:
            log_error("Tray icon could not start:\n" + traceback.format_exc())
        try:
            set_autostart(config_bool(self.config, "autostart"))
        except Exception:
            log_error("Autostart setting failed:\n" + traceback.format_exc())
        if "--now" in sys.argv:  # show the countdown right away (handy for testing)
            self.events.put("show")
        self.root.after(50, self._poll)
        self.root.mainloop()

    def _poll(self):
        try:
            while True:
                event = self.events.get_nowait()
                if event == "show":
                    self.show()
                elif event == "stats":
                    open_stats_window()
                elif event == "edit":
                    open_file(ACTIONS_FILE)
                elif event == "quit":
                    self.quit()
                    return
        except queue.Empty:
            pass
        except Exception:
            log_error(traceback.format_exc())
        self.root.after(50, self._poll)

    def quit(self):
        if self.hotkey:
            self.hotkey.stop()
        if self.tray:
            self.tray.stop()
        self.root.destroy()

    def show(self):
        if self.window is not None:  # already on screen
            return
        tk = self.tk
        self.config = load_config()  # pick up edits without restarting
        self.action = None
        self.typed_task = ""
        self.closed = False

        w = tk.Toplevel(self.root, bg=BG)
        self.window = w
        w.title("Five")
        w.geometry(f"{w.winfo_screenwidth()}x{w.winfo_screenheight()}+0+0")
        w.attributes("-fullscreen", True)
        w.attributes("-topmost", True)
        w.configure(cursor="arrow")

        self.big = tk.Label(w, text="", font=(FONT, 220, "bold"), fg=FG, bg=BG)
        self.big.place(relx=0.5, rely=0.42, anchor="center")
        self.action_label = tk.Label(w, text="", font=(FONT, 44, "bold"), fg=FG, bg=BG,
                                     wraplength=int(w.winfo_screenwidth() * 0.8), justify="center")
        self.done_button = tk.Button(w, text="Done", font=(FONT, 28, "bold"), fg=BG, bg=ACCENT,
                                     activebackground=FG, activeforeground=BG, relief="flat",
                                     padx=60, pady=14, cursor="hand2", command=self.finish_done)
        self.hint = tk.Label(w, text="Enter = Done     Esc = skip", font=(FONT, 14), fg="#666666", bg=BG)

        w.bind("<Escape>", lambda e: self.finish("skipped"))
        w.bind("<Return>", lambda e: self.finish_done())
        w.bind("<KP_Enter>", lambda e: self.finish_done())
        w.protocol("WM_DELETE_WINDOW", lambda: self.finish("skipped"))

        self._grab_focus()
        if config_bool(self.config, "ask_task"):
            self.ask_task()
        else:
            self.start_countdown()

    def ask_task(self):
        """First screen: you type the task you are avoiding."""
        tk = self.tk
        self.asking = True
        self.question = tk.Label(self.window, text="What do you need to do?",
                                 font=(FONT, 40, "bold"), fg=FG, bg=BG)
        self.question.place(relx=0.5, rely=0.35, anchor="center")
        self.entry = tk.Entry(self.window, font=(FONT, 32), width=36, justify="center",
                              fg=FG, bg="#1f1f1f", insertbackground=FG, relief="flat")
        self.entry.place(relx=0.5, rely=0.5, anchor="center", height=70)
        self.ask_hint = tk.Label(self.window,
                                 text="Type it and press Enter     (empty = random action)     Esc = cancel",
                                 font=(FONT, 14), fg="#666666", bg=BG)
        self.ask_hint.place(relx=0.5, rely=0.62, anchor="center")
        self.entry.bind("<Return>", self.task_entered)
        self.entry.bind("<KP_Enter>", self.task_entered)
        self.entry.focus_force()
        self.window.after(200, lambda: self.window is not None and self.asking and self.entry.focus_force())

    def task_entered(self, event=None):
        self.typed_task = self.entry.get().strip()
        self.asking = False
        for widget in (self.question, self.entry, self.ask_hint):
            widget.destroy()
        self.window.focus_force()
        self.start_countdown()
        return "break"  # don't let this Enter also press "Done"

    def start_countdown(self):
        self.asking = False
        self.tick(config_seconds(self.config))

    def _grab_focus(self):
        w = self.window
        if w is None:
            return
        w.deiconify()
        w.lift()
        w.attributes("-topmost", True)
        w.focus_force()
        # Windows sometimes refuses the first focus request; ask again shortly
        w.after(150, lambda: self.window is w and w.focus_force())

    def tick(self, n):
        if self.window is None:
            return
        if n > 0:
            self.big.config(text=str(n), fg=FG)
            self.window.after(1000, self.tick, n - 1)
        else:
            self.go()

    def go(self):
        self.big.config(text="GO", fg=ACCENT, font=(FONT, 160, "bold"))
        self.big.place(relx=0.5, rely=0.25, anchor="center")
        self.window.update_idletasks()
        if config_bool(self.config, "close_browser"):
            close_browsers()
            self._grab_focus()
        self.action = self.typed_task or random.choice(load_actions())
        self.action_label.config(text=self.action)
        self.action_label.place(relx=0.5, rely=0.55, anchor="center")
        self.done_button.place(relx=0.5, rely=0.78, anchor="center")
        self.hint.place(relx=0.5, rely=0.92, anchor="center")
        self.done_button.focus_set()

    def finish_done(self):
        if self.action is None:  # Enter during the countdown does nothing
            return
        self.finish("done")

    def finish(self, result):
        if self.window is None or self.closed:
            return
        self.closed = True
        if getattr(self, "asking", False):  # cancelled before starting: nothing to log
            self.window.destroy()
            self.window = None
            return
        # Escape during the countdown still logs which action was skipped: none yet
        append_log(result, self.action or "(closed during countdown)")
        self.window.destroy()
        self.window = None


# --------------------------------------------------------------------------

def main():
    ensure_files()
    if "--stats" in sys.argv:
        print_stats(pause="--pause" in sys.argv)
        return
    if not acquire_single_instance():
        try:
            import tkinter as tk
            from tkinter import messagebox
            r = tk.Tk()
            r.withdraw()
            messagebox.showinfo("Five", "Five is already running.\nLook for the '5' icon next to the clock.")
            r.destroy()
        except Exception:
            pass
        return
    try:
        FiveApp().run()
    except Exception:
        log_error(traceback.format_exc())
        raise


if __name__ == "__main__":
    main()
