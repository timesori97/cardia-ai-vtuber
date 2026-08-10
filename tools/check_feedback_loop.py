"""Do the lessons get judged on results, or just on sounding sensible?

Nothing used to check whether a rule helped. A plausible-but-harmful bullet
could survive every rewrite forever. Now each run is recorded against the
revision of the notes that was live during it, and the comparison goes back
into the distiller as evidence.

Run: python tools/check_feedback_loop.py   (throwaway vault, no game needed)
"""

import os
import shutil
import sys
import tempfile

sys.path.insert(0, "D:/ai-vtuber-kit")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from orchestrator import Orchestrator


def make(vault, rev):
    o = Orchestrator.__new__(Orchestrator)
    o.vault = vault
    o.lessons_rev = rev
    o.run_deck = "RED"
    o.notes = []
    o.note = o.notes.append
    return o


tmp = tempfile.mkdtemp(prefix="cardia-vault-")
try:
    print("\n[1] runs are tagged with the notes that were live")
    # r1 did badly, r2 did better
    for rev, antes in ((1, [1, 2, 1, 2]), (2, [3, 4, 3])):
        o = make(tmp, rev)
        for ante in antes:
            o._record_run_outcome({"ante": ante}, won=False)
    o = make(tmp, 2)
    rows = o._read_progress()
    print("    rows recorded : %d" % len(rows))
    print("    revisions seen: %s" % sorted({r for r, _, _ in rows}))

    print("\n[2] the verdict handed to the distiller")
    print("    " + o._performance_summary().replace("\n", "\n    "))

    print("\n[3] now make the newest revision WORSE and re-check")
    o3 = make(tmp, 3)
    for ante in (1, 1, 1):
        o3._record_run_outcome({"ante": ante}, won=False)
    verdict = make(tmp, 3)._performance_summary()
    print("    " + verdict.replace("\n", "\n    "))
    print("    -> %s" % ("told to revert (correct)"
                         if "MADE THINGS WORSE" in verdict else "NOT FLAGGED"))

    print("\n[4] does it reach the distiller prompt?")
    import brain as brain_mod

    seen = {}

    class Probe(brain_mod.Brain):
        def __init__(self):
            self.routes = {"lessons": {"model": "opus"}}

        def _call(self, route, task, **kw):
            seen["task"] = task
            return {"lessons": ["x"], "playbook": "y"}

    Probe().distill_lessons("a run", "old lessons", "old playbook",
                            game="Balatro", performance=verdict)
    task = seen["task"]
    print("    performance section present : %s"
          % ("HOW YOUR ADVICE HAS BEEN PERFORMING" in task))
    print("    told to weigh it over vibes : %s"
          % ("Weigh it above how sensible a rule sounds" in task))

    print("\n[5] no scoreboard yet (first ever run) — still safe?")
    blank = tempfile.mkdtemp(prefix="cardia-empty-")
    empty = make(blank, 0)
    print("    summary: %r" % empty._performance_summary())
    shutil.rmtree(blank, ignore_errors=True)
    Probe().distill_lessons("a run", "l", "p", game="Balatro",
                            performance=empty._performance_summary())
    print("    section omitted entirely   : %s"
          % ("HOW YOUR ADVICE" not in seen["task"]))

    print("\n[6] scoreboard stays bounded")
    o6 = make(tmp, 4)
    for _ in range(Orchestrator.KEEP_PROGRESS_ROWS + 15):
        o6._record_run_outcome({"ante": 2}, won=False)
    kept = len(o6._read_progress())
    print("    %d rows (cap %d)  %s"
          % (kept, Orchestrator.KEEP_PROGRESS_ROWS,
             "OK" if kept <= Orchestrator.KEEP_PROGRESS_ROWS else "UNBOUNDED"))
finally:
    shutil.rmtree(tmp, ignore_errors=True)
