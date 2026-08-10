"""Remove notes that make the brain worse, and keep the vault bounded.

The vault feeds every in-game decision, so bad entries compound. Two kinds
were found in practice:

  - dossiers for blinds that are NOT bosses. Dying to a Small Blind with an
    empty board got filed as a boss defeat, and the distilled lessons then
    described the easiest blind in the game as the deadliest enemy.
  - run reports from a much older, more broken version of the bot (it could
    not see shop effects at all), which are misleading evidence now.

Run: python tools/clean_vault.py            show what would change
     python tools/clean_vault.py --apply    actually change it
"""

import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import vault as vault_cfg

VAULT = vault_cfg.vault_dir()      # from .env, never hardcoded
KEEP_RUNS = 30

BLIND_NOTES_DIR = "Boss blinds"
# Only the ante's third blind carries a rule worth notes; a Small or Big
# Blind filed in here is a plain loss that got mistaken for a threat.
NOT_A_BOSS_BLIND = re.compile(r"^(small|big)\s+blind$", re.I)


def is_uninformative(path):
    """Same test the orchestrator uses before distilling: a loss with no
    jokers, no levelled hands and no recorded choices taught nothing."""
    try:
        text = open(path, encoding="utf-8").read()
    except OSError:
        return False
    if re.search(r"^result:\s*won", text, re.M):
        return False
    # [ \t]* not \s* — \s crosses newlines, so an empty field would swallow
    # the blank line after it and capture whatever came next as its value.
    ante = re.search(r"^ante:[ \t]*(\d+)", text, re.M)
    if ante and int(ante.group(1)) > 1:
        return False
    jokers = re.search(r"^- jokers:[ \t]*(.*)$", text, re.M)
    if jokers and jokers.group(1).strip() not in ("", "[[none]]", "none"):
        return False
    levels = re.search(r"^- levelled hands:[ \t]*(.*)$", text, re.M)
    if levels and levels.group(1).strip():
        return False
    return not re.search(r"^- A\d+ ", text, re.M)


def main():
    apply = "--apply" in sys.argv
    print("\nvault: %s   (%s)\n" % (VAULT, "APPLYING" if apply else "dry run"))

    bosses = os.path.join(VAULT, BLIND_NOTES_DIR)
    if os.path.isdir(bosses):
        print("%s/ — notes filed for blinds that carry no rule:" % BLIND_NOTES_DIR)
        found = False
        for name in sorted(os.listdir(bosses)):
            if not name.endswith(".md"):
                continue
            if NOT_A_BOSS_BLIND.match(name[:-3]):
                found = True
                path = os.path.join(bosses, name)
                entries = sum(1 for ln in open(path, encoding="utf-8")
                              if ln.startswith("- "))
                print("   remove %-22s (%d bogus 'defeat' entries)" % (name, entries))
                if apply:
                    os.remove(path)
        if not found:
            print("   (none — clean)")

    runs = os.path.join(VAULT, "Cardia runs")
    if os.path.isdir(runs):
        names = sorted(f for f in os.listdir(runs) if f.endswith(".md"))
        print("\nCardia runs/ — %d reports:" % len(names))

        # A loss with no jokers, nothing levelled and no recorded choices has
        # exactly one lesson in it ("get a scorer") and it is already written
        # down. Most of these are from before the bot could even see what
        # shop cards did, so they are misleading evidence now.
        empty = [n for n in names if is_uninformative(os.path.join(runs, n))]
        if empty:
            print("   %d reports with nothing to learn from:" % len(empty))
            for name in empty:
                print("      remove %s" % name)
                if apply:
                    os.remove(os.path.join(runs, name))
            names = [n for n in names if n not in empty]
        else:
            print("   (every report has decisions in it)")

        extra = names[:-KEEP_RUNS] if len(names) > KEEP_RUNS else []
        if extra:
            print("   over the %d cap — removing %d oldest" % (KEEP_RUNS, len(extra)))
            for old in extra:
                if apply:
                    os.remove(os.path.join(runs, old))
        else:
            print("   %d kept (cap %d)" % (len(names), KEEP_RUNS))

    print("\nNotes that mention a non-boss blind as a threat:")
    hits = 0
    for note in ("Cardia lessons.md", "Joker playbook.md"):
        path = os.path.join(VAULT, note)
        if not os.path.exists(path):
            continue
        for i, line in enumerate(open(path, encoding="utf-8"), 1):
            if re.search(r"\[\[(Small|Big) Blind\]\]", line):
                hits += 1
                print("   %s:%d  %s" % (note, i, line.strip()[:88]))
    if hits:
        print("\n   These are rewritten wholesale after the next run, and the"
              "\n   distiller is now told to delete exactly this kind of line."
              "\n   Left alone on purpose — the AI curates its own notes.")
    else:
        print("   (none)")


if __name__ == "__main__":
    main()
