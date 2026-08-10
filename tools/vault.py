"""Where the Balatro notes live, according to .env — never hardcoded.

The vault path moved once already (D:\\balatro -> D:\\cardia balatro) and every
tool that had it baked in broke. Read it from the same place the orchestrator
does, and tolerate files that do not exist yet: a freshly wiped vault has no
lessons or playbook, and that is a normal state, not an error.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from twitch_chat import load_env


def vault_dir(game="balatro"):
    key = "BALATRO_VAULT" if game == "balatro" else "OBSIDIAN_VAULT"
    return (load_env().get(key) or "").strip()


def read(name, game="balatro"):
    """Contents of one note, or '' when the vault has not grown it yet."""
    base = vault_dir(game)
    if not base:
        return ""
    try:
        with open(os.path.join(base, name), encoding="utf-8") as f:
            return f.read()
    except OSError:
        return ""


def manual(game="balatro"):
    return read("Game manual.md", game)


def playbook(game="balatro"):
    return read("Joker playbook.md", game) or read("Deck playbook.md", game)


def lessons(game="balatro"):
    return read("Cardia lessons.md", game)
