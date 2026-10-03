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
FINES_FILE = APP_DIR / "fines.csv"  # the fine jar: what you owe for skipping

IS_WINDOWS = sys.platform == "win32"

# Bump this every time a new Five.zip is sent, so "Update Five" knows it is newer
VERSION = "1.4"

# Files that "Update Five" may replace. Your actions.txt, config.txt and
# log.csv are never touched.
PROGRAM_FILES = ["five.py", "run.bat", "setup.bat", "README.md"]

DEFAULT_CONFIG = {
    "hotkey": "ctrl+alt+5",
    "countdown_seconds": "5",
    "close_browser": "false",
    "autostart": "true",
    "ask_task": "true",
    "schedule": "weekdays 21:00 Rutina de la noche",
    "default_tiny_step": "Just do the first 2 minutes. Nothing else.",
    "future_message": "",
    "fine_amount": "1000",
    "fine_currency": "CLP",
    "pay_link": "",
    "radar_sites": "youtube,instagram,tiktok,netflix,facebook,twitter,reddit",
    "radar_minutes": "10",
    "momentum_minutes": "10",
}

# The explanation written above each setting in config.txt
SETTING_HELP = {
    "hotkey": ["# Global hotkey. Examples: ctrl+alt+5, ctrl+shift+f, ctrl+alt+f9"],
    "countdown_seconds": ["# How many seconds the countdown lasts (5 = 5, 4, 3, 2, 1, GO)"],
    "close_browser": ["# true = close all Chrome and Edge windows at GO"],
    "autostart": ["# true = start Five automatically when Windows starts"],
    "ask_task": ["# true = ask you to type your task before the countdown",
                 "# (leave it empty and press Enter to get a random action from actions.txt)",
                 "# false = always pick a random action from actions.txt"],
    "schedule": ["# Automatic countdowns, no hotkey needed: DAYS TIME TASK",
                 "# DAYS: weekdays (Mon-Fri), weekends, daily, or a list like mon,wed,fri",
                 "# TIME: 24-hour clock, 21:00 = 9 pm. You can add more schedule= lines.",
                 "# If the computer was off or asleep, it still runs up to 30 minutes late.",
                 "# schedule=off turns it off."],
    "default_tiny_step": ["# The small line shown under your task at GO, when the task has no",
                          "# first step of its own. In actions.txt you can give each action its",
                          "# own first step after a | sign, like this:",
                          "#   Go to the gym | Put on your shoes. That's it."],
    "future_message": ["# A message from future you, shown under the numbers during the countdown.",
                       "# Example: future_message=Santi, you promised. Do it for future you.",
                       "# Leave it empty for no message. To also show a photo, use the tray",
                       "# icon > Set future photo (or put a future.png or future.jpg in this folder)."],
    "fine_amount": ["# Fine jar: every time you skip (Esc), this amount goes into your fine jar.",
                    "# Tray icon > Fine jar shows what you owe. 0 = fine jar off."],
    "fine_currency": ["# The currency shown next to the fine (just a label, e.g. CLP, USD, EUR)"],
    "pay_link": ["# Optional: a payment link of your own (Mercado Pago, PayPal, a donation page...).",
                 "# The Fine jar window then shows a 'Pay now' button that opens it in your browser.",
                 "# Five never asks for or stores your card. This only opens the link in your browser",
                 "# so you pay on that company's secure page. Leave it empty for no button.",
                 "# Example: pay_link=https://www.paypal.me/yourname"],
    "radar_sites": ["# Procrastination radar: words that mark a distracting window.",
                    "# If the title of the window you are using contains one of these words,",
                    "# Five counts it as distraction time. Separate the words with commas."],
    "radar_minutes": ["# Procrastination radar: after this many minutes on distracting windows,",
                      "# Five opens the countdown for you. 0 = radar off.",
                      "# The count starts over if you stay away from them for 2 minutes."],
    "momentum_minutes": ["# Momentum timer: after you press Done, a small box in the corner counts",
                         "# down this many minutes to help you keep going. 0 = off."],
}

WEEKDAY_NAMES = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
SCHEDULE_GRACE_MINUTES = 30

# Procrastination radar: how often the active window is checked, and how long
# you must stay away from distracting windows for the count to start over
RADAR_CHECK_MS = 5000
RADAR_RESET_SECONDS = 120
# A longer gap between two checks (sleep, a frozen app) never counts as more than this
RADAR_MAX_STEP_SECONDS = 30

DEFAULT_ACTIONS = [
    "Close the laptop and walk the dog | Close the laptop lid. Just that.",
    "Text Tito | Open the chat with Tito. Nothing else.",
    "Go to the gym | Put on your shoes. That's it.",
    "Open the BancoEstado folder | Just double-click the folder. Nothing else.",
]

# The photo for "future you" is the first of these files found in APP_DIR
FUTURE_PHOTO_NAMES = ["future.png", "future.jpg", "future.jpeg"]

LOG_HEADER = ["date", "time", "result", "action"]
FINES_HEADER = ["date", "time", "kind", "amount", "note"]

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
    """Create config.txt and actions.txt if missing, and add any new settings
    to an existing config.txt (your values are never changed)."""
    if not CONFIG_FILE.exists():
        lines = ["# Five settings. Change the value after the = sign and save.",
                 "# hotkey and autostart need a restart of Five (tray > Quit, then run.bat).",
                 "# Lines that start with # are ignored."]
        for key, value in DEFAULT_CONFIG.items():
            lines += [""] + SETTING_HELP[key] + [f"{key}={value}"]
        CONFIG_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    else:
        text = CONFIG_FILE.read_text(encoding="utf-8-sig")
        present = {l.split("=", 1)[0].strip().lower() for l in text.splitlines()
                   if "=" in l and not l.strip().startswith("#")}
        missing = [k for k in DEFAULT_CONFIG if k not in present]
        if missing:
            add = []
            for key in missing:
                add += [""] + SETTING_HELP[key] + [f"{key}={DEFAULT_CONFIG[key]}"]
            if not text.endswith("\n"):
                text += "\n"
            CONFIG_FILE.write_text(text + "\n".join(add) + "\n", encoding="utf-8")
    if not ACTIONS_FILE.exists():
        ACTIONS_FILE.write_text("\n".join(DEFAULT_ACTIONS) + "\n", encoding="utf-8")


def load_config():
    config = dict(DEFAULT_CONFIG)
    schedules = []
    try:
        # utf-8-sig also accepts files saved by Notepad with a BOM
        for line in CONFIG_FILE.read_text(encoding="utf-8-sig").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip().lower()
            if key == "schedule":  # may appear several times
                schedules.append(value.strip())
            else:
                config[key] = value.strip()
    except OSError:
        pass
    if not schedules:
        schedules = [DEFAULT_CONFIG["schedule"]]
    config["schedules"] = [x for x in schedules if x.lower() not in ("", "off", "none", "false")]
    return config


def parse_schedule(text):
    """'weekdays 21:00 Rutina de la noche' -> ({0,1,2,3,4}, 21, 0, 'Rutina de la noche')"""
    parts = text.split(None, 2)
    if len(parts) < 2:
        return None
    days_text, time_text = parts[0].lower(), parts[1]
    task = parts[2].strip() if len(parts) > 2 else ""
    named = {"weekdays": {0, 1, 2, 3, 4}, "weekends": {5, 6}, "daily": set(range(7)),
             "everyday": set(range(7))}
    if days_text in named:
        days = named[days_text]
    else:
        days = set()
        for chunk in days_text.split(","):
            if "-" in chunk:  # a range like mon-fri
                a, b = chunk.split("-", 1)
                if a not in WEEKDAY_NAMES or b not in WEEKDAY_NAMES:
                    return None
                i, j = WEEKDAY_NAMES.index(a), WEEKDAY_NAMES.index(b)
                days |= set(range(i, j + 1)) if i <= j else set(range(i, 7)) | set(range(0, j + 1))
            elif chunk in WEEKDAY_NAMES:
                days.add(WEEKDAY_NAMES.index(chunk))
            else:
                return None
    try:
        hour, minute = (int(x) for x in time_text.split(":"))
        dt.time(hour, minute)
    except ValueError:
        return None
    return days, hour, minute, task


def due_schedules(schedules, now, already_fired):
    """Schedules that should run now (on time or up to 30 minutes late) and
    have not run today. Returns a list of (fired_key, task)."""
    due = []
    for text in schedules:
        parsed = parse_schedule(text)
        if parsed is None:
            continue
        days, hour, minute, task = parsed
        if now.weekday() not in days:
            continue
        start = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        key = (now.date(), text)
        if start <= now < start + dt.timedelta(minutes=SCHEDULE_GRACE_MINUTES) and key not in already_fired:
            due.append((key, task))
    return due


def config_bool(config, key):
    return config.get(key, "").strip().lower() in ("true", "yes", "1", "si", "sí")


def config_seconds(config):
    try:
        return max(1, min(60, int(config.get("countdown_seconds", "5"))))
    except ValueError:
        return 5


def split_action(line):
    """'Go to the gym | Put on your shoes.' -> ('Go to the gym', 'Put on your shoes.')
    A line without | gives (line, '')."""
    action, _, step = line.partition("|")
    return action.strip(), step.strip()


def read_action_entries():
    """[(action, tiny_step), ...] from actions.txt (tiny_step may be '')."""
    try:
        text = ACTIONS_FILE.read_text(encoding="utf-8-sig")
    except OSError:
        text = ""
    entries = []
    for l in text.splitlines():
        if not l.strip() or l.strip().startswith("#"):
            continue
        action, step = split_action(l)
        if action:
            entries.append((action, step))
    return entries


def read_actions():
    """Just the action names (the part before | on each line)."""
    return [action for action, _ in read_action_entries()]


def tiny_step_for(action, config=None):
    """The first tiny step for `action`: from actions.txt if that line has
    '| step', otherwise the default_tiny_step setting."""
    try:
        for name, step in read_action_entries():
            if step and name.lower() == action.strip().lower():
                return step
    except Exception:
        log_error("tiny_step_for failed:\n" + traceback.format_exc())
    config = config or load_config()
    return config.get("default_tiny_step", "").strip()


def load_actions():
    return read_actions() or ["Add your actions to actions.txt"]


def add_action(action):
    action = action.strip()  # may be 'task | first step'
    if not split_action(action)[0] or split_action(action)[0] in read_actions():
        return
    try:
        old = ACTIONS_FILE.read_text(encoding="utf-8-sig")
    except OSError:
        old = ""
    if old and not old.endswith("\n"):
        old += "\n"
    ACTIONS_FILE.write_text(old + action + "\n", encoding="utf-8")


def remove_action(action):
    """Delete the first line that matches `action`; comments stay as they are."""
    lines = ACTIONS_FILE.read_text(encoding="utf-8-sig").splitlines()
    for i, line in enumerate(lines):
        if not line.strip().startswith("#") and split_action(line)[0] == action.strip():
            del lines[i]
            break
    ACTIONS_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")


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
# Fine jar: fines.csv (kind "fine" on each skip, "paid" when you pay)
# --------------------------------------------------------------------------

def parse_amount(text):
    """'1000', '1,000', ' 2.5 ' -> a number. Anything invalid or negative -> 0."""
    try:
        value = float(str(text).replace(",", "").replace(" ", "").replace("_", ""))
    except ValueError:
        return 0
    if value != value or value <= 0 or value == float("inf"):  # NaN, inf, not positive
        return 0
    return int(value) if value.is_integer() else value


def config_fine(config):
    return parse_amount(config.get("fine_amount", "0"))


def format_money(amount, currency=""):
    """1000 -> '1,000', 2.5 -> '2.50'. Adds the currency label if given."""
    amount = float(amount)
    text = f"{int(amount):,}" if amount.is_integer() else f"{amount:,.2f}"
    return f"{text} {currency}".strip()


def append_fine(kind, amount, note="", when=None):
    """Add one line to fines.csv. The amount is saved as it is now, so
    changing fine_amount later never changes old fines."""
    when = when or dt.datetime.now()
    is_new = not FINES_FILE.exists() or FINES_FILE.stat().st_size == 0
    with open(FINES_FILE, "a", encoding="utf-8", newline="") as f:
        if is_new:
            f.write("﻿")  # same BOM as log.csv, for Excel
        writer = csv.writer(f)
        if is_new:
            writer.writerow(FINES_HEADER)
        writer.writerow([when.strftime("%Y-%m-%d"), when.strftime("%H:%M:%S"), kind,
                         format_money(amount).replace(",", ""), note])


def read_fines():
    """List of (date, kind, amount) from fines.csv. Bad lines are skipped."""
    rows = []
    if not FINES_FILE.exists():
        return rows
    with open(FINES_FILE, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            try:
                day = dt.date.fromisoformat(row["date"])
            except (KeyError, TypeError, ValueError):
                continue
            kind = (row.get("kind") or "").strip().lower()
            if kind in ("fine", "paid"):
                rows.append((day, kind, parse_amount(row.get("amount"))))
    return rows


def fine_summary(rows, today=None):
    """Owed = all fines - all payments, never below 0. Also counts the fines
    (= skips) this week (since Monday) and this month."""
    today = today or dt.date.today()
    week_start = today - dt.timedelta(days=today.weekday())
    fined = sum(a for _, k, a in rows if k == "fine")
    paid = sum(a for _, k, a in rows if k == "paid")
    owed = max(0, fined - paid)
    if isinstance(owed, float):
        owed = round(owed, 2)
        if owed.is_integer():
            owed = int(owed)
    return {
        "owed": owed,
        "skips_week": sum(1 for d, k, _ in rows if k == "fine" and week_start <= d <= today),
        "skips_month": sum(1 for d, k, _ in rows if k == "fine" and d <= today
                           and (d.year, d.month) == (today.year, today.month)),
    }


def safe_pay_link(link):
    """Only plain web links are opened. 'mpago.la/abc' becomes 'https://mpago.la/abc'."""
    link = (link or "").strip()
    if not link:
        return ""
    if "://" not in link:
        link = "https://" + link
    return link if link.lower().startswith(("https://", "http://")) else ""


def open_pay_link(link):
    """Open your own payment link in the default browser. Five itself never
    sees or stores any card or payment details."""
    import webbrowser
    link = safe_pay_link(link)
    if not link:
        return False
    return webbrowser.open(link)


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
    try:
        f = fine_summary(read_fines())
        currency = load_config().get("fine_currency", "")
        print(f"  Fine jar: {format_money(f['owed'], currency)} owed "
              f"({f['skips_week']} skips this week)")
    except Exception:
        log_error("Fine jar stats failed:\n" + traceback.format_exc())
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


# --------------------------------------------------------------------------
# Procrastination radar: notices long stretches on distracting windows
# --------------------------------------------------------------------------

def foreground_window_title():
    """Title of the window you are using right now ('' if unknown)."""
    if IS_WINDOWS:
        import ctypes
        user32 = ctypes.windll.user32
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return ""
        length = user32.GetWindowTextLengthW(hwnd)
        if length <= 0:
            return ""
        buffer = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buffer, length + 1)
        return buffer.value
    import shutil
    if not shutil.which("xdotool"):
        return ""
    # getactivewindow needs a window manager; getwindowfocus works without one
    for how in ("getactivewindow", "getwindowfocus"):
        try:
            out = subprocess.run(["xdotool", how, "getwindowname"], capture_output=True,
                                 text=True, timeout=2)
        except (OSError, subprocess.SubprocessError):
            return ""
        if out.returncode == 0:
            return out.stdout.strip()
    return ""


def parse_radar_sites(text):
    return [w.strip().lower() for w in (text or "").split(",") if w.strip()]


def config_minutes(config, key):
    """A number of minutes from config.txt; 0 (= off) if missing or invalid."""
    try:
        return max(0.0, float(config.get(key, "0").replace(",", ".")))
    except ValueError:
        return 0.0


def format_minutes(minutes):
    text = f"{minutes:g}"
    return f"{text} minute" if text == "1" else f"{text} minutes"


class DistractionRadar:
    """Adds up time spent on distracting windows. Pure logic (no tkinter, no
    clock of its own), so it can be tested with made-up timestamps."""

    def __init__(self):
        self.reset()

    def reset(self):
        self.seconds = 0.0
        self.last_check = None
        self.last_distracted = None

    def update(self, now, title, sites, limit_seconds, paused=False):
        """Call every few seconds with now = time in seconds. Returns the
        matched word when the limit is reached (and starts over), else None."""
        last, self.last_check = self.last_check, now
        if limit_seconds <= 0:
            self.reset()
            return None
        if paused:  # Five's own window is open: don't count anything
            return None
        title = (title or "").lower()
        word = next((w for w in sites if w and w in title), None)
        if word is None:
            if self.last_distracted is not None and now - self.last_distracted >= RADAR_RESET_SECONDS:
                self.seconds = 0.0
                self.last_distracted = None
            return None
        if last is not None:
            self.seconds += max(0.0, min(now - last, RADAR_MAX_STEP_SECONDS))
        self.last_distracted = now
        if self.seconds >= limit_seconds:
            self.reset()
            self.last_check = now
            return word
        return None


# --------------------------------------------------------------------------
# Updating from a Five.zip in the Downloads folder (no internet needed)
# --------------------------------------------------------------------------

def downloads_folders():
    folders = []
    if IS_WINDOWS:
        try:  # the real Downloads folder, even if it was moved (e.g. to OneDrive)
            import ctypes
            from ctypes import wintypes
            from uuid import UUID

            class GUID(ctypes.Structure):
                _fields_ = [("Data1", wintypes.DWORD), ("Data2", wintypes.WORD),
                            ("Data3", wintypes.WORD), ("Data4", ctypes.c_ubyte * 8)]

            u = UUID("374DE290-123F-4565-9164-39C4925E467B")  # FOLDERID_Downloads
            guid = GUID(u.fields[0], u.fields[1], u.fields[2],
                        (ctypes.c_ubyte * 8)(*u.bytes[8:]))
            path = ctypes.c_wchar_p()
            if ctypes.windll.shell32.SHGetKnownFolderPath(ctypes.byref(guid), 0, None,
                                                          ctypes.byref(path)) == 0:
                folders.append(Path(path.value))
                ctypes.windll.ole32.CoTaskMemFree(path)
        except Exception:
            pass
    home = Path.home()
    folders += [home / "Downloads", home / "Descargas", home / "OneDrive" / "Downloads",
                APP_DIR.parent]
    return [f for f in dict.fromkeys(folders) if f.is_dir()]


def version_tuple(text):
    try:
        return tuple(int(x) for x in text.split("."))
    except (AttributeError, ValueError):
        return (0,)


def find_update_zip():
    """Newest Five*.zip in Downloads. Browsers rename copies to 'Five (1).zip'."""
    zips = []
    for folder in downloads_folders():
        zips += [z for z in folder.glob("*.zip") if z.name.lower().startswith("five")]
    return max(zips, key=lambda z: z.stat().st_mtime) if zips else None


def install_update():
    """Copy the program files from the newest Five.zip over this folder.
    Returns (updated, message)."""
    import re
    import shutil
    import zipfile

    zip_path = find_update_zip()
    if zip_path is None:
        return False, ("I couldn't find a Five.zip in your Downloads folder.\n\n"
                       "Download the new Five.zip first, then try again.")
    try:
        with zipfile.ZipFile(zip_path) as z:
            # The files may be inside a "five/" folder in the zip, or at the top
            names = {Path(n).name: n for n in z.namelist() if Path(n).name in PROGRAM_FILES}
            if "five.py" not in names:
                return False, f"{zip_path.name} doesn't look like a Five update (no five.py inside)."
            new_code = z.read(names["five.py"])
            compile(new_code, "five.py", "exec")  # refuse a broken file
            found = re.search(rb'^VERSION = "([0-9.]+)"', new_code, re.M)
            new_version = found.group(1).decode() if found else "0"
            if version_tuple(new_version) <= version_tuple(VERSION):
                return False, (f"You already have the newest version ({VERSION}).\n\n"
                               f"({zip_path.name} has version {new_version}.)")
            shutil.copy2(APP_DIR / "five.py", APP_DIR / "five.py.bak")  # just in case
            for name, member in names.items():
                (APP_DIR / name).write_bytes(z.read(member))
    except (zipfile.BadZipFile, SyntaxError, OSError) as exc:
        log_error("Update failed:\n" + traceback.format_exc())
        return False, f"The update failed, nothing was changed.\n\n{exc}"
    return True, f"Five was updated from version {VERSION} to {new_version}.\n\nIt will restart now."


def restart_five():
    args = [str(pythonw_path()), str(Path(__file__).resolve()), "--after-update"]
    flags = subprocess.DETACHED_PROCESS if IS_WINDOWS else 0
    subprocess.Popen(args, creationflags=flags, close_fds=True)


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


def acquire_single_instance(wait_seconds=0):
    """True if no other Five is running. After an update, wait for the old
    copy to finish closing."""
    import time
    deadline = time.time() + wait_seconds
    while True:
        if _try_lock():
            return True
        if time.time() >= deadline:
            return False
        time.sleep(0.3)


def _try_lock():
    global _instance_lock
    if IS_WINDOWS:
        import ctypes
        handle = ctypes.windll.kernel32.CreateMutexW(None, False, "Local\\FiveApp5SecondRule")
        if ctypes.windll.kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
            ctypes.windll.kernel32.CloseHandle(handle)
            return False
        _instance_lock = handle
        return True
    import fcntl
    import tempfile
    lock_file = open(Path(tempfile.gettempdir()) / "five_app.lock", "w")
    try:
        fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        lock_file.close()
        return False
    _instance_lock = lock_file
    return True


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
        pystray.MenuItem("Set future photo", lambda: events.put("future_photo")),
        pystray.MenuItem("Fine jar", lambda: events.put("finejar")),
        pystray.MenuItem("Update Five", lambda: events.put("update")),
        pystray.MenuItem("Quit", lambda: events.put("quit")),
    )
    icon = pystray.Icon("Five", make_icon_image(), "Five - Ctrl+Alt+5", menu)
    icon.run_detached()
    return icon


# --------------------------------------------------------------------------
# "Future you": an optional photo shown during the countdown
# --------------------------------------------------------------------------

def find_future_photo():
    for name in FUTURE_PHOTO_NAMES:
        path = APP_DIR / name
        if path.is_file():
            return path
    return None


def load_future_photo(max_width, max_height):
    """The future-you photo as a Tk image that fits in max_width x max_height,
    or None if there is no photo (or it can't be read)."""
    path = find_future_photo()
    if path is None:
        return None
    try:
        from PIL import Image, ImageOps, ImageTk
        with Image.open(path) as img:
            img = ImageOps.exif_transpose(img)  # phone photos may be stored sideways
            img = img.convert("RGBA" if "A" in img.getbands() else "RGB")
            scale = min(max_width / img.width, max_height / img.height)
            size = (max(1, int(img.width * scale)), max(1, int(img.height * scale)))
            img = img.resize(size, Image.LANCZOS)
            return ImageTk.PhotoImage(img)
    except Exception:
        log_error(f"Could not load the future photo {path.name}:\n" + traceback.format_exc())
        return None


def install_future_photo(source):
    """Copy the chosen image to APP_DIR/future.<ext>, replacing any older one.
    Returns the new file's path."""
    import shutil
    from PIL import Image
    source = Path(source)
    with Image.open(source) as img:  # make sure it really is an image
        img.load()
        ext = source.suffix.lower()
        old = [APP_DIR / n for n in FUTURE_PHOTO_NAMES] + \
              [APP_DIR / f"future{e}" for e in (".gif", ".bmp", ".webp")]
        for path in old:
            if path.exists() and path.resolve() != source.resolve():
                path.unlink()
        if ext in (".png", ".jpg", ".jpeg"):
            target = APP_DIR / f"future{ext}"
            if target.resolve() != source.resolve():
                shutil.copyfile(source, target)
        else:  # other formats are saved as PNG so they are found next time
            target = APP_DIR / "future.png"
            img.save(target, "PNG")
    return target


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
        self.fired_schedules = set()
        self.pending_task = None
        self.finejar_window = None
        self.toast = None
        self.radar = DistractionRadar()
        self.momentum = None  # the small "Keep going" box, if it is open

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
        self.root.after(2000, self._check_schedules)
        self.root.after(RADAR_CHECK_MS, self._check_radar)
        self.root.mainloop()

    def _check_radar(self):
        if self.root is None:
            return
        try:
            import time
            config = load_config()
            minutes = config_minutes(config, "radar_minutes")
            open_now = self.window is not None
            title = foreground_window_title() if minutes > 0 and not open_now else ""
            word = self.radar.update(time.monotonic(), title, parse_radar_sites(config.get("radar_sites")),
                                     minutes * 60, paused=open_now)
            if word and self.window is None:
                self.show(reason=f"You've been on {word.capitalize()} for {format_minutes(minutes)}.")
        except Exception:
            log_error("Procrastination radar failed:\n" + traceback.format_exc())
        self.root.after(RADAR_CHECK_MS, self._check_radar)

    def _check_schedules(self):
        if self.root is None:
            return
        try:
            schedules = load_config()["schedules"]
            for key, task in due_schedules(schedules, dt.datetime.now(), self.fired_schedules):
                self.fired_schedules.add(key)
                self.pending_task = task or None
                self.pending_scheduled = True
            if getattr(self, "pending_scheduled", False) and self.window is None:
                self.pending_scheduled = False
                self.show(task=self.pending_task or "")
        except Exception:
            log_error(traceback.format_exc())
        self.root.after(15000, self._check_schedules)

    def _poll(self):
        try:
            while True:
                event = self.events.get_nowait()
                if event == "show":
                    self.show()
                elif event == "stats":
                    open_stats_window()
                elif event == "update":
                    self.update()
                    if self.root is None:
                        return
                elif event == "edit":
                    open_file(ACTIONS_FILE)
                elif event == "future_photo":
                    self.set_future_photo()
                elif event == "finejar":
                    self.show_fine_jar()
                elif event == "quit":
                    self.quit()
                    return
        except queue.Empty:
            pass
        except Exception:
            log_error(traceback.format_exc())
        self.root.after(50, self._poll)

    def update(self):
        from tkinter import messagebox
        self.root.attributes("-topmost", True)  # so the message isn't hidden
        updated, message = install_update()
        if not updated:
            messagebox.showinfo("Five", message, parent=self.root)
            return
        messagebox.showinfo("Five", message, parent=self.root)
        restart_five()  # the new copy waits until this one has closed
        self.quit()

    def set_future_photo(self):
        """Tray > Set future photo: pick an image, copy it as future.<ext>."""
        from tkinter import filedialog, messagebox
        self.root.attributes("-topmost", True)  # so the dialog isn't hidden
        path = filedialog.askopenfilename(
            parent=self.root, title="Choose a photo of future you",
            filetypes=[("Images", "*.png *.jpg *.jpeg *.gif *.bmp *.webp"),
                       ("PNG", "*.png"), ("JPEG", "*.jpg *.jpeg")])
        if not path:  # cancelled
            return
        try:
            target = install_future_photo(path)
        except Exception as exc:
            log_error("Set future photo failed:\n" + traceback.format_exc())
            messagebox.showerror("Five", f"That photo could not be used.\n\n{exc}", parent=self.root)
            return
        messagebox.showinfo("Five", f"Done! Your future-you photo is saved as {target.name}.\n\n"
                                    "You will see it during the countdown.", parent=self.root)

    def quit(self):
        if self.hotkey:
            self.hotkey.stop()
        if self.tray:
            self.tray.stop()
        self.root.destroy()
        self.root = None

    def show(self, task=None, reason=None):
        """task=None: normal hotkey flow. task='...': scheduled, starts the
        countdown right away with that task ('' = random from your list).
        reason='...': a short line shown at the top (e.g. from the radar)."""
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
        self.step_label = tk.Label(w, text="", font=(FONT, 22), fg="#b3b3b3", bg=BG,
                                   wraplength=int(w.winfo_screenwidth() * 0.7), justify="center")
        self.future_image = None  # keep a reference, or Tk forgets the picture
        self.future_photo_label = tk.Label(w, bg=BG, bd=0)
        self.future_message_label = tk.Label(w, text="", font=(FONT, 26, "italic"), fg=ACCENT, bg=BG,
                                             wraplength=int(w.winfo_screenwidth() * 0.8), justify="center")

        w.bind("<Escape>", lambda e: self.finish("skipped"))
        w.bind("<Return>", lambda e: self.finish_done())
        w.bind("<KP_Enter>", lambda e: self.finish_done())
        w.protocol("WM_DELETE_WINDOW", lambda: self.finish("skipped"))
        if reason:
            tk.Label(w, text=reason, font=(FONT, 18), fg=ACCENT, bg=BG).place(relx=0.5, rely=0.04, anchor="n")

        self._grab_focus()
        if task is not None:
            self.typed_task = task
            self.start_countdown()
        elif config_bool(self.config, "ask_task"):
            self.ask_task()
        else:
            self.start_countdown()

    def ask_task(self):
        """First screen: type your task, roll a random one, or pick from your list."""
        tk = self.tk
        self.asking = True
        self.ask_frame = tk.Frame(self.window, bg=BG)
        self.ask_frame.place(relx=0.5, rely=0.45, anchor="center")
        f = self.ask_frame

        tk.Label(f, text="What do you need to do?", font=(FONT, 40, "bold"),
                 fg=FG, bg=BG).pack(pady=(0, 20))
        self.entry = tk.Entry(f, font=(FONT, 30), width=36, justify="center",
                              fg=FG, bg="#1f1f1f", insertbackground=FG, relief="flat")
        self.entry.pack(ipady=12)
        self.entry.bind("<Return>", self.task_entered)
        self.entry.bind("<KP_Enter>", self.task_entered)

        buttons = tk.Frame(f, bg=BG)
        buttons.pack(pady=18)
        self._button(buttons, "Start  ⏎", self.task_entered, primary=True).pack(side="left", padx=8)
        self._button(buttons, "⚄  Random", self.pick_random).pack(side="left", padx=8)
        self._button(buttons, "+  Save to my list", self.save_typed).pack(side="left", padx=8)

        tk.Label(f, text="MY LIST  (click one to start it)", font=(FONT, 13, "bold"),
                 fg="#888888", bg=BG).pack(pady=(18, 6))
        self.list_frame = tk.Frame(f, bg=BG)
        self.list_frame.pack()
        self.draw_list()

        tk.Label(f, text="Enter = start     empty = random     Esc = cancel",
                 font=(FONT, 12), fg="#555555", bg=BG).pack(pady=(18, 0))

        self.entry.focus_force()
        self.window.after(200, lambda: self.window is not None and self.asking and self.entry.focus_force())

    def _button(self, parent, text, command, primary=False, small=False):
        return self.tk.Button(parent, text=text, command=command, relief="flat", cursor="hand2",
                              font=(FONT, 12 if small else 16, "bold" if primary else "normal"),
                              fg=BG if primary else FG, bg=ACCENT if primary else "#262626",
                              activebackground=FG, activeforeground=BG,
                              padx=8 if small else 18, pady=2 if small else 8)

    MAX_SHOWN = 10

    def draw_list(self):
        tk = self.tk
        for widget in self.list_frame.winfo_children():
            widget.destroy()
        actions = read_actions()
        if not actions:
            tk.Label(self.list_frame, text="Your list is empty. Type something and press  + Save to my list",
                     font=(FONT, 13), fg="#666666", bg=BG).pack()
            return
        for action in actions[:self.MAX_SHOWN]:
            row = tk.Frame(self.list_frame, bg=BG)
            row.pack(fill="x", pady=2)
            self.tk.Button(row, text=action, anchor="w", width=40, relief="flat", cursor="hand2",
                           font=(FONT, 14), fg=FG, bg="#1a1a1a", activebackground=ACCENT,
                           activeforeground=BG, padx=12, pady=4,
                           command=lambda a=action: self.start_with(a)).pack(side="left")
            self._button(row, "✕", lambda a=action: self.delete_from_list(a), small=True).pack(side="left", padx=(6, 0))
        if len(actions) > self.MAX_SHOWN:
            tk.Label(self.list_frame, text=f"+ {len(actions) - self.MAX_SHOWN} more (Random can pick them too)",
                     font=(FONT, 12), fg="#666666", bg=BG).pack(pady=(4, 0))

    def save_typed(self):
        add_action(self.entry.get())
        self.entry.delete(0, "end")
        self.draw_list()
        self.entry.focus_set()

    def delete_from_list(self, action):
        remove_action(action)
        self.draw_list()
        self.entry.focus_set()

    def pick_random(self):
        self.start_with("")

    def start_with(self, task):
        self.entry.delete(0, "end")
        self.entry.insert(0, task)
        self.task_entered()

    def task_entered(self, event=None):
        if not self.asking:
            return "break"
        self.typed_task = self.entry.get().strip()
        self.asking = False
        self.ask_frame.destroy()
        self.window.focus_force()
        self.start_countdown()
        return "break"  # don't let this Enter also press "Done"

    def start_countdown(self):
        self.asking = False
        self.show_future_you()
        self.tick(config_seconds(self.config))

    def show_future_you(self):
        """Photo and/or message from future you under the countdown number."""
        try:
            w = self.window
            sw, sh = w.winfo_screenwidth(), w.winfo_screenheight()
            message = self.config.get("future_message", "").strip()
            self.future_image = load_future_photo(int(sw * 0.5), int(sh * 0.4))
            if self.future_image is not None:
                # Smaller number, higher up, so the photo and message fit below
                self.big.config(font=(FONT, 150, "bold"))
                self.big.place(relx=0.5, rely=0.2, anchor="center")
                self.future_photo_label.config(image=self.future_image)
                self.future_photo_label.place(relx=0.5, rely=0.6, anchor="center")
                message_y = 0.87
            else:
                message_y = 0.75
            if message:
                self.future_message_label.config(text=message)
                self.future_message_label.place(relx=0.5, rely=message_y, anchor="center")
        except Exception:
            log_error("show_future_you failed:\n" + traceback.format_exc())

    def hide_future_you(self):
        try:
            self.future_photo_label.place_forget()
            self.future_message_label.place_forget()
            self.future_photo_label.config(image="")
            self.future_image = None
        except Exception:
            log_error("hide_future_you failed:\n" + traceback.format_exc())

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
        self.hide_future_you()
        self.big.config(text="GO", fg=ACCENT, font=(FONT, 160, "bold"))
        self.big.place(relx=0.5, rely=0.25, anchor="center")
        self.window.update_idletasks()
        if config_bool(self.config, "close_browser"):
            close_browsers()
            self._grab_focus()
        self.action = self.typed_task or random.choice(load_actions())
        # A typed 'task | first step' also works
        self.action, typed_step = split_action(self.action)
        self.action = self.action or "Add your actions to actions.txt"
        step = typed_step or tiny_step_for(self.action, self.config)
        self.action_label.config(text=self.action)
        self.action_label.place(relx=0.5, rely=0.47, anchor="center")
        if step:
            self.step_label.config(text="First tiny step: " + step)
            # right under the action, however many lines the action takes
            self.step_label.place(in_=self.action_label, relx=0.5, rely=1.0, y=18, anchor="n")
        self.done_button.place(relx=0.5, rely=0.78, anchor="center")
        self.hint.place(relx=0.5, rely=0.92, anchor="center")
        self._fit_go_layout(bool(step))
        self.done_button.focus_set()

    def _fit_go_layout(self, has_step):
        """A long task can take several lines: push things apart so the
        task, tiny step, Done button and hint never overlap."""
        try:
            import tkinter.font as tkfont
            w = self.window
            w.update_idletasks()
            sh = w.winfo_screenheight()
            # bottom of the letters G O (the label box also has room for descenders)
            big_font = tkfont.Font(font=self.big.cget("font"))
            go_bottom = (self.big.winfo_y() + (self.big.winfo_height() - big_font.metrics("linespace")) // 2
                         + big_font.metrics("ascent"))
            a = self.action_label
            if a.winfo_y() < go_bottom + 10:
                a.place(relx=0.5, rely=0, y=go_bottom + 10, anchor="n")
                w.update_idletasks()
            text_bottom = a.winfo_y() + a.winfo_height()
            if has_step:
                s = self.step_label
                text_bottom = s.winfo_y() + s.winfo_height()
            done_h = self.done_button.winfo_reqheight()
            done_y = max(int(sh * 0.78), text_bottom + 24 + done_h // 2)
            hint_h = self.hint.winfo_reqheight()
            hint_y = min(max(int(sh * 0.92), done_y + done_h // 2 + 12 + hint_h // 2), sh - hint_h // 2)
            self.done_button.place(relx=0.5, rely=0, y=done_y, anchor="center")
            self.hint.place(relx=0.5, rely=0, y=hint_y, anchor="center")
        except Exception:
            log_error("GO layout failed:\n" + traceback.format_exc())

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
        if result == "skipped":
            self.add_fine(self.action or self.typed_task or "(closed during countdown)")
        if result == "done":
            self.start_momentum()

    # ---------------------------------------------------------------- fine jar

    def add_fine(self, note):
        """A skip puts fine_amount into the jar and shows a short toast."""
        try:
            config = load_config()
            amount = config_fine(config)
            if not amount:
                return
            append_fine("fine", amount, note)
            currency = config.get("fine_currency", "")
            owed = fine_summary(read_fines())["owed"]
            self.show_toast(f"-{format_money(amount, currency)} to the fine jar  "
                            f"(total owed: {format_money(owed, currency)})")
            if self.finejar_window is not None:
                self.draw_fine_jar()
        except Exception:
            log_error("Fine jar failed:\n" + traceback.format_exc())

    def show_toast(self, text, ms=3000):
        """Small dark box in the bottom-right corner. It never takes the focus."""
        tk = self.tk
        if self.toast is not None:
            try:
                self.toast.destroy()
            except Exception:
                pass
        t = tk.Toplevel(self.root, bg=ACCENT)
        self.toast = t
        t.withdraw()
        t.overrideredirect(True)  # no title bar or border
        t.attributes("-topmost", True)
        tk.Label(t, text=text, font=(FONT, 13, "bold"), fg=ACCENT, bg="#1a1a1a",
                 padx=18, pady=12).pack(padx=2, pady=2)
        t.update_idletasks()
        x = t.winfo_screenwidth() - t.winfo_reqwidth() - 24
        y = t.winfo_screenheight() - t.winfo_reqheight() - 64  # above the taskbar
        t.geometry(f"+{x}+{y}")
        if IS_WINDOWS:
            try:  # WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW: no focus, no taskbar button
                import ctypes
                hwnd = ctypes.windll.user32.GetParent(t.winfo_id()) or t.winfo_id()
                style = ctypes.windll.user32.GetWindowLongW(hwnd, -20)
                ctypes.windll.user32.SetWindowLongW(hwnd, -20, style | 0x08000000 | 0x00000080)
            except Exception:
                pass
        t.deiconify()

        def close():
            try:
                t.destroy()
            except Exception:
                pass
            if self.toast is t:
                self.toast = None
        t.after(ms, close)

    def show_fine_jar(self):
        """Tray > Fine jar: what you owe, Pay now, I paid it."""
        if self.finejar_window is not None:
            self.finejar_window.deiconify()
            self.finejar_window.lift()
            self.finejar_window.focus_force()
            return
        tk = self.tk
        w = tk.Toplevel(self.root, bg=BG)
        self.finejar_window = w
        w.title("Five - Fine jar")
        width, height = 520, 360
        x = (w.winfo_screenwidth() - width) // 2
        y = (w.winfo_screenheight() - height) // 2
        w.geometry(f"{width}x{height}+{x}+{y}")
        w.resizable(False, False)
        w.attributes("-topmost", True)
        w.protocol("WM_DELETE_WINDOW", self.close_fine_jar)
        w.bind("<Escape>", lambda e: self.close_fine_jar())
        self.draw_fine_jar()
        w.focus_force()

    def close_fine_jar(self):
        if self.finejar_window is not None:
            self.finejar_window.destroy()
            self.finejar_window = None

    def draw_fine_jar(self):
        tk = self.tk
        w = self.finejar_window
        if w is None:
            return
        for widget in w.winfo_children():
            widget.destroy()
        config = load_config()
        currency = config.get("fine_currency", "")
        fine = config_fine(config)
        link = safe_pay_link(config.get("pay_link", ""))
        s = fine_summary(read_fines())

        tk.Label(w, text="FINE JAR", font=(FONT, 13, "bold"), fg="#888888", bg=BG).pack(pady=(22, 0))
        tk.Label(w, text=format_money(s["owed"], currency), font=(FONT, 40, "bold"),
                 fg=ACCENT, bg=BG).pack()
        tk.Label(w, text="owed", font=(FONT, 13), fg="#888888", bg=BG).pack()
        skips = s["skips_month"]
        tk.Label(w, text=f"{skips} skip{'' if skips == 1 else 's'} this month", font=(FONT, 15),
                 fg=FG, bg=BG).pack(pady=(14, 0))
        rule = (f"Each skip adds {format_money(fine, currency)}" if fine
                else "Fine jar is off (fine_amount=0 in config.txt)")
        tk.Label(w, text=rule, font=(FONT, 11), fg="#666666", bg=BG).pack(pady=(2, 0))

        buttons = tk.Frame(w, bg=BG)
        buttons.pack(pady=(18, 0))
        pay = self._button(buttons, "Pay now", lambda: self.pay_now(link), primary=True)
        if not link:
            pay.config(state="disabled", bg="#3a3a3a", disabledforeground="#777777", cursor="arrow")
        pay.pack(side="left", padx=6)
        self._button(buttons, "I paid it", self.mark_paid).pack(side="left", padx=6)
        self._button(buttons, "Close", self.close_fine_jar).pack(side="left", padx=6)
        if not link:
            tk.Label(w, text="Set pay_link in config.txt to get a Pay now button",
                     font=(FONT, 11), fg="#666666", bg=BG).pack(pady=(12, 0))

    def pay_now(self, link):
        try:
            open_pay_link(link)
        except Exception:
            log_error("Pay now failed:\n" + traceback.format_exc())

    def mark_paid(self):
        from tkinter import messagebox
        w = self.finejar_window
        try:
            currency = load_config().get("fine_currency", "")
            owed = fine_summary(read_fines())["owed"]
            if not owed:
                messagebox.showinfo("Five", "Nothing to pay. Your fine jar is empty.", parent=w)
                return
            if not messagebox.askyesno("Five", f"Did you pay {format_money(owed, currency)}?\n\n"
                                       "This empties your fine jar.", parent=w):
                return
            append_fine("paid", owed, "marked as paid")
        except Exception:
            log_error("I paid it failed:\n" + traceback.format_exc())
        self.draw_fine_jar()

    # ----- Momentum timer: a small "Keep going" box after Done -----

    def start_momentum(self):
        try:
            import time
            minutes = config_minutes(load_config(), "momentum_minutes")
            self.close_momentum()  # only one at a time
            if minutes <= 0:
                return
            tk = self.tk
            m = tk.Toplevel(self.root, bg=BG, highlightthickness=1, highlightbackground=ACCENT)
            self.momentum = m
            m.overrideredirect(True)  # no title bar
            m.attributes("-topmost", True)
            width, height = 260, 90
            x = m.winfo_screenwidth() - width - 16
            y = m.winfo_screenheight() - height - 56  # stay above the taskbar
            m.geometry(f"{width}x{height}+{x}+{y}")
            m.momentum_label = tk.Label(m, text="", font=(FONT, 15, "bold"), fg=FG, bg=BG)
            m.momentum_label.place(relx=0.5, rely=0.55, anchor="center")
            tk.Button(m, text="✕", command=self.close_momentum, relief="flat", cursor="hand2",
                      font=(FONT, 10), fg="#888888", bg=BG, activebackground="#262626",
                      activeforeground=FG, bd=0, padx=6, pady=0).place(relx=1.0, x=-4, y=4, anchor="ne")
            m.momentum_end = time.monotonic() + minutes * 60
            if IS_WINDOWS:
                self._momentum_no_activate(m)
            self._momentum_tick(m)
        except Exception:
            log_error("Momentum timer failed:\n" + traceback.format_exc())

    def _momentum_no_activate(self, m):
        """Windows: clicking the box must not take the focus from your other apps."""
        try:
            import ctypes
            m.update_idletasks()
            hwnd = int(m.wm_frame(), 16)
            GWL_EXSTYLE, WS_EX_NOACTIVATE, WS_EX_TOOLWINDOW = -20, 0x08000000, 0x00000080
            style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE,
                                                style | WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW)
        except Exception:
            log_error("Momentum no-activate failed:\n" + traceback.format_exc())

    def _momentum_tick(self, m):
        if self.momentum is not m:  # closed or replaced by a newer one
            return
        try:
            import time
            left = int(round(m.momentum_end - time.monotonic()))
            if left > 0:
                m.momentum_label.config(text=f"Keep going: {left // 60}:{left % 60:02d}")
                m.after(1000, self._momentum_tick, m)
            else:
                m.momentum_label.config(text="★ You kept going!", fg=ACCENT)
                m.after(4000, lambda: self.momentum is m and self.close_momentum())
        except Exception:
            log_error("Momentum timer failed:\n" + traceback.format_exc())
            self.close_momentum()

    def close_momentum(self):
        m, self.momentum = self.momentum, None
        if m is not None:
            try:
                m.destroy()
            except Exception:
                pass


# --------------------------------------------------------------------------

def main():
    ensure_files()
    if "--stats" in sys.argv:
        print_stats(pause="--pause" in sys.argv)
        return
    if not acquire_single_instance(wait_seconds=15 if "--after-update" in sys.argv else 0):
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
