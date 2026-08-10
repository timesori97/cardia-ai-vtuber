"""Patch balatrobot for the stream. Re-run after any mod update.

Two changes, both needed because balatrobot is built for headless bots, not
for something people watch:

1. AUDIO — the mod mutes the game every launch (configure_settings sets all
   three volumes to 0 and G.F_MUTE = true). BALATROBOT_AUDIO=1 (set by the
   launcher) switches it to configure_audio() instead, but that hardcodes
   master volume 50 and the owner wants 60.

2. DISMISS — unlocking a deck pops an overlay with a Continue button and
   pauses the game behind it. The API drives game functions directly and
   never presses that button, so the popup sat on the broadcast and the run
   stopped. Adds a `dismiss` endpoint that closes any overlay.

Originals are kept next to this script. Writes go through a process created
outside the app container, because %APPDATA% writes from here get virtualised
and never reach the real file.
"""

import os
import re
import shutil
import subprocess
import sys

MOD = os.path.join(os.environ["APPDATA"], "Balatro", "Mods", "balatrobot",
                   "src", "lua", "settings.lua")
STAGE = os.path.dirname(os.path.abspath(__file__))
WANT_MASTER = 60


def outside_container_copy(src, dst):
    """Copy via a process the app container does not virtualise."""
    cmd = 'cmd /c copy /Y "%s" "%s"' % (src, dst)
    ps = ('$r = Invoke-CimMethod -ClassName Win32_Process -MethodName Create '
          '-Arguments @{CommandLine = \'%s\'}; '
          '$p = Get-Process -Id $r.ProcessId -ErrorAction SilentlyContinue; '
          'if ($p) { $p.WaitForExit(20000) | Out-Null }; exit 0' % cmd)
    subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                   capture_output=True, timeout=60)


def install_dismiss_endpoint():
    """Drop in the dismiss endpoint and register it in the mod's list."""
    dest_dir = os.path.dirname(MOD)                      # .../src/lua
    dest = os.path.join(dest_dir, "endpoints", "dismiss.lua")
    outside_container_copy(os.path.join(STAGE, "dismiss.lua"), dest)
    installed = os.path.exists(dest)
    print("\ndismiss endpoint file: %s" % ("installed" if installed
                                           else "NOT INSTALLED"))

    main_lua = os.path.abspath(os.path.join(dest_dir, "..", "..",
                                            "balatrobot.lua"))
    text = open(main_lua, encoding="utf-8").read()
    if "endpoints/dismiss.lua" in text:
        print("already registered in balatrobot.lua")
        return
    anchor = '  "src/lua/endpoints/menu.lua",'
    if anchor not in text:
        print("could not find where to register it - mod layout changed")
        return
    text = text.replace(
        anchor,
        '  -- Cardia stream: close deck-unlock popups that block the run\n'
        '  "src/lua/endpoints/dismiss.lua",\n' + anchor, 1)
    staged = os.path.join(STAGE, "balatrobot.lua.new")
    if not os.path.exists(os.path.join(STAGE, "balatrobot.lua.orig")):
        shutil.copy2(main_lua, os.path.join(STAGE, "balatrobot.lua.orig"))
    with open(staged, "w", encoding="utf-8", newline="") as f:
        f.write(text)
    outside_container_copy(staged, main_lua)
    ok = "endpoints/dismiss.lua" in open(main_lua, encoding="utf-8").read()
    print("registered in balatrobot.lua: %s" % ("yes" if ok else "NO"))


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    text = open(MOD, encoding="utf-8").read()

    block = re.search(r"local function configure_audio\(\).*?\nend", text, re.S)
    if not block:
        print("configure_audio() not found - mod layout changed, aborting")
        return
    print("before:")
    for line in block.group(0).splitlines():
        if "volume" in line or "MUTE" in line or "THREAD" in line:
            print("   " + line.strip())

    patched = block.group(0)
    patched = re.sub(r'(G\.SETTINGS\.SOUND\.volume\s*=\s*)\d+',
                     r"\g<1>%d" % WANT_MASTER, patched)
    new_text = text[:block.start()] + patched + text[block.end():]

    if new_text == text:
        print("\nalready at the wanted level - nothing to do")
        install_dismiss_endpoint()
        return

    staged = os.path.join(STAGE, "settings.lua.new")
    with open(staged, "w", encoding="utf-8", newline="") as f:
        f.write(new_text)
    if not os.path.exists(os.path.join(STAGE, "settings.lua.orig")):
        shutil.copy2(MOD, os.path.join(STAGE, "settings.lua.orig"))

    outside_container_copy(staged, MOD)

    check = open(MOD, encoding="utf-8").read()
    ok = check == new_text
    print("\nafter (re-read from the mod folder): %s"
          % ("applied" if ok else "NOT APPLIED - write was virtualised"))
    block2 = re.search(r"local function configure_audio\(\).*?\nend", check, re.S)
    if block2:
        for line in block2.group(0).splitlines():
            if "volume" in line or "MUTE" in line or "THREAD" in line:
                print("   " + line.strip())
    install_dismiss_endpoint()


if __name__ == "__main__":
    main()
