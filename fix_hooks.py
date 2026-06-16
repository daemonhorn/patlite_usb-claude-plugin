#!/usr/bin/env python3
"""
Repairs USB LED plugin hooks in ~/.claude/settings.json.

Run this if the hook fires with a mangled path (common when hooks are
added via the /hooks dialog on Windows, because bash eats backslashes
in the command string). This script replaces backslash paths with
forward-slash paths and migrates any hooks still pointing at the old
patlite.py script name.

    python fix_hooks.py
"""
import sys, os, json, shutil, platform
from pathlib import Path, PurePosixPath

INSTALL_DIR = Path.home() / ".claude" / "plugins" / "usb_led"
VENV_DIR = INSTALL_DIR / ".venv"
SETTINGS_PATH = Path.home() / ".claude" / "settings.json"

HOOK_EVENTS = {
    "Notification": "notification",
    "Stop": "stop",
    "UserPromptSubmit": "working",
    "PreToolUse": "pre_tool",
    "PostToolUse": "post_tool",
    "SessionEnd": "idle",
}


def as_posix(p: Path) -> str:
    """Return a path string using forward slashes (works on all platforms)."""
    return p.as_posix()


def _get_python_exe() -> str:
    """Return the Python that has the plugin's packages: venv if it exists, else sys.executable."""
    is_windows = platform.system() == "Windows"
    venv_python = VENV_DIR / ("Scripts/python.exe" if is_windows else "bin/python3")
    if venv_python.exists():
        return as_posix(venv_python)
    return as_posix(Path(sys.executable))


def make_hook(cmd_arg: str) -> dict:
    python_exe = _get_python_exe()
    script = as_posix(INSTALL_DIR / "usb_led.py")
    return {
        "matcher": ".*",
        "hooks": [{"type": "command",
                   "command": f"{python_exe} {script} {cmd_arg}",
                   "timeout": 5,
                   "allowFailure": True}]
    }


def contains_plugin_hook(entry: dict) -> bool:
    return any(
        "usb_led" in h.get("command", "") or "patlite" in h.get("command", "")
        for h in entry.get("hooks", [])
    )


def main():
    if not SETTINGS_PATH.exists():
        print("~/.claude/settings.json not found — nothing to fix")
        sys.exit(0)

    with open(SETTINGS_PATH, encoding="utf-8") as f:
        cfg = json.load(f)

    hooks = cfg.setdefault("hooks", {})
    removed = 0

    # Strip ALL existing plugin hooks (bad and good)
    for event in list(HOOK_EVENTS):
        before = hooks.get(event, [])
        after = [e for e in before if not contains_plugin_hook(e)]
        removed += len(before) - len(after)
        if after:
            hooks[event] = after
        else:
            hooks.pop(event, None)

    # Re-add with forward-slash paths
    for event, arg in HOOK_EVENTS.items():
        hooks.setdefault(event, []).append(make_hook(arg))

    backup = SETTINGS_PATH.with_suffix(".json.bak")
    shutil.copy2(SETTINGS_PATH, backup)

    with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)

    print(f"Fixed {removed} malformed hook(s).")
    print(f"Python executable : {as_posix(Path(sys.executable))}")
    print(f"Plugin script     : {as_posix(INSTALL_DIR / 'usb_led.py')}")
    print(f"Backup saved to   : {backup}")
    print()
    print("Restart Claude Code to apply the new hooks.")


if __name__ == "__main__":
    main()
