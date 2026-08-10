"""The dismiss endpoint exists, but is it called on a timer? It must not be.

It was originally swept every 2 seconds to click through deck-unlock popups.
That was wrong twice over: unlocks use notify_alert(), a toast that blocks
nothing, while G.OVERLAY_MENU is the game's real menus — so the sweep closed
legitimate menus (four times in four minutes on a live run) and force-unpaused
the game, which crashed it inside pack.lua. The endpoint stays for stuck
recovery; nothing may call it on a schedule.

Run: python tools/check_popup.py
"""

import os
import sys

sys.path.insert(0, "D:/ai-vtuber-kit")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

print("\n[1] is the endpoint installed in the mod?")
mods = os.path.join(os.environ["APPDATA"], "Balatro", "Mods", "balatrobot")
endpoint = os.path.join(mods, "src", "lua", "endpoints", "dismiss.lua")
main_lua = os.path.join(mods, "balatrobot.lua")
print("    dismiss.lua present   : %s" % os.path.exists(endpoint))
print("    registered in mod list: %s"
      % ("endpoints/dismiss.lua" in open(main_lua, encoding="utf-8").read()))

print("\n[2] does it still force-unpause the game? (it must not)")
lua = open(endpoint, encoding="utf-8").read()
touches_pause = "SETTINGS.paused = false" in lua
print("    writes G.SETTINGS.paused: %s  -> %s"
      % (touches_pause,
         "BUG — this is what crashed pack.lua" if touches_pause else "no"))

print("\n[3] is anything calling it on a timer?")
loop = open("D:/ai-vtuber-kit/orchestrator.py", encoding="utf-8").read()
swept = "link.dismiss()" in loop
print("    orchestrator calls dismiss(): %s  -> %s"
      % (swept, "STILL SWEEPING — remove it" if swept else "no periodic sweep"))

print("\n[4] does the escape hatch re-check the screen before acting?")
esc = loop.split("def _balatro_escape")[1].split("\n    def ")[0]
rechecks = "link.state()" in esc.split("fallback =")[0]
print("    re-reads state first: %s" % rechecks)
print("    -> a stale screen is how a pack action hit a pack that was already")
print("       gone, which is the crash the owner hit")

ok = (not touches_pause) and (not swept) and rechecks
print("\n  => %s" % ("safe" if ok else "NOT SAFE — see the lines above"))
