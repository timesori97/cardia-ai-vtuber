"""How fast does a live stream burn brain calls? Counts real calls per hour
from logs/brain.jsonl so the Opus budget can be estimated from data.
"""

import json
import sys
from collections import defaultdict
from datetime import datetime

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PATH = "D:/ai-vtuber-kit/logs/brain.jsonl"
buckets = defaultdict(lambda: defaultdict(int))
tokens = defaultdict(list)
latency = defaultdict(list)

with open(PATH, encoding="utf-8") as f:
    for line in f:
        try:
            e = json.loads(line)
            t = datetime.strptime(e["ts"], "%Y-%m-%d %H:%M:%S")
        except (ValueError, KeyError, json.JSONDecodeError):
            continue
        hour = t.strftime("%Y-%m-%d %H")
        buckets[hour][e.get("route", "?")] += 1
        if e.get("out_tokens"):
            tokens[e.get("route")].append(e["out_tokens"])
        if e.get("latency_ms"):
            latency[e.get("route")].append(e["latency_ms"])

busy = sorted(buckets.items(), key=lambda kv: -sum(kv[1].values()))[:6]
print("=== 시간대별 호출 수 (활동 많은 순 6개) ===")
for hour, routes in busy:
    total = sum(routes.values())
    detail = ", ".join("%s:%d" % (r, n) for r, n in
                       sorted(routes.items(), key=lambda kv: -kv[1]))
    print("  %s시  총 %3d회  | %s" % (hour, total, detail))

print("\n=== 라우트별 평균 (전체 기간) ===")
for route in sorted(set(list(tokens) + list(latency))):
    tk = tokens.get(route) or [0]
    lt = latency.get(route) or [0]
    print("  %-18s 호출 %4d회  출력토큰 평균 %5d  지연 평균 %5.1fs"
          % (route, len(lt), sum(tk) / len(tk), sum(lt) / len(lt) / 1000))

game_hours = [sum(r.values()) for h, r in buckets.items() if r.get("game_decision")]
gd = [r.get("game_decision", 0) for h, r in buckets.items() if r.get("game_decision")]
if gd:
    gd_sorted = sorted(gd)
    print("\n=== 게임 판단 시간당 호출 (실측) ===")
    print("  중앙값 %d회/시간, 최대 %d회/시간, 표본 %d시간"
          % (gd_sorted[len(gd_sorted) // 2], max(gd), len(gd)))
