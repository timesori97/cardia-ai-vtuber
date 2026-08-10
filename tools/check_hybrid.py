"""Which model handles which situation? (hybrid routing sanity check)"""

import sys

sys.path.insert(0, "D:/ai-vtuber-kit")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from orchestrator import Orchestrator

o = Orchestrator(game_link=False, use_twitch=False, use_tts=False)
o.game_model = None

DEFAULT = o.brain.routes["game_decision"]["model"]
FAST = o.brain.routes["game_decision"]["fast_model"]


def combat(hp, dmg, hits=1, room="MonsterRoom"):
    return {"game_state": {"screen_type": "NONE", "room_type": room,
                           "current_hp": hp,
                           "combat_state": {"turn": 2, "player": {"current_hp": hp},
                                            "monsters": [{"move_adjusted_damage": dmg,
                                                          "move_hits": hits,
                                                          "is_gone": False}]}}}


def screen(name):
    return {"game_state": {"screen_type": name, "floor": 8}}


cases = [
    ("일반 전투 턴 (안전)", combat(70, 8)),
    ("위험한 턴 (피해 40%+)", combat(30, 9, 2)),
    ("엘리트 전투", combat(70, 8, room="MonsterRoomElite")),
    ("보스 전투", combat(70, 8, room="MonsterRoomBoss")),
    ("카드 보상", screen("CARD_REWARD")),
    ("상점", screen("SHOP_SCREEN")),
    ("휴식/강화", screen("REST")),
    ("맵 경로", screen("MAP")),
    ("이벤트", screen("EVENT")),
]

print("기본=%s / 빠른=%s\n" % (DEFAULT, FAST))
opus_n = 0
for label, st in cases:
    think = o.think_budget(st)
    picked = o.pick_game_model(st, think)
    name = DEFAULT if picked is None else picked
    if name == DEFAULT:
        opus_n += 1
    print("  %-20s think=%-4d -> %s" % (label, think, name.upper()))

print("\n%d/%d 상황이 %s" % (opus_n, len(cases), DEFAULT.upper()))

o.game_model = FAST
st = screen("CARD_REWARD")
print("적응형 다운그레이드 후 카드보상:",
      o.pick_game_model(st, o.think_budget(st)))
