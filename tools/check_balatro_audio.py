"""Will the game actually make sound on the next stream?

Three things have to line up, and only the first one really decides it:
  1. the launcher sets BALATROBOT_AUDIO=1  (else the mod mutes the game and
     turns the sound thread off entirely, whatever the game settings say)
  2. the mod's configure_audio() is at the level the owner wants
  3. settings.jkr agrees, for when the game is opened without the bot mod

Run: python tools/check_balatro_audio.py
"""

import os
import re
import sys
import zlib

sys.path.insert(0, "D:/ai-vtuber-kit")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from orchestrator import Orchestrator

WANT = Orchestrator.BALATRO_VOLUME
ok = True

print("\n[1] launcher enables audio?")
launcher = open("D:/ai-vtuber-kit/start_balatro.ps1", encoding="utf-8-sig").read()
has = re.search(r"BALATROBOT_AUDIO\s*=\s*'1'", launcher) is not None
print("    BALATROBOT_AUDIO=1 in start_balatro.ps1 : %s" % ("yes" if has else "NO"))
ok &= has

print("\n[2] what the mod forces at startup")
mod = os.path.join(os.environ["APPDATA"], "Balatro", "Mods", "balatrobot",
                   "src", "lua", "settings.lua")
text = open(mod, encoding="utf-8").read()
audio = re.search(r"local function configure_audio\(\).*?\nend", text, re.S)
if audio:
    master = re.search(r"G\.SETTINGS\.SOUND\.volume\s*=\s*(\d+)", audio.group(0))
    mute = re.search(r"G\.F_MUTE\s*=\s*(\w+)", audio.group(0))
    thread = re.search(r"G\.F_SOUND_THREAD\s*=\s*(\w+)", audio.group(0))
    print("    master volume : %s (want %d)" % (master.group(1), WANT))
    print("    F_MUTE        : %s" % mute.group(1))
    print("    sound thread  : %s" % thread.group(1))
    ok &= master.group(1) == str(WANT) and mute.group(1) == "false"
else:
    print("    configure_audio() not found - mod changed")
    ok = False

muted = re.search(r"local function configure_settings\(\).*?\nend", text, re.S)
if muted and "G.F_MUTE = true" in muted.group(0):
    print("    (mute path still present for when AUDIO is off - expected)")

print("\n[3] settings.jkr (only used without the bot mod)")
sett = os.path.join(os.environ["APPDATA"], "Balatro", "settings.jkr")
raw = zlib.decompress(open(sett, "rb").read(), -15).decode("utf-8", "replace")
vols = dict(re.findall(r'\["(volume|music_volume|game_sounds_volume)"\]=([\d.]+)', raw))
print("    %s" % vols)

print("\n  => %s" % ("game audio will play at %d%%" % WANT if ok
                     else "SOMETHING IS OFF - see the NO/mismatch above"))
