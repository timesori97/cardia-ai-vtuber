# TASK: pick the deck and stake for this Balatro run

You are about to start a fresh run live on stream. Choose which deck to play and at which stake (difficulty). You are only ever shown options this profile has actually unlocked — never try to name anything else.

Decide quickly. This is one choice, not a research project.

## What you can play right now

{{OPTIONS}}

## How progression works — this is the point of the choice

- Decks unlock by **discovering new items** (just seeing new jokers/cards/vouchers for the first time) or by **winning** with a specific deck or at a specific stake.
- A deck's next stake unlocks when you **win a run with that deck at its current stake**. So Red Stake only ever appears after a White Stake win.
- That makes every run an investment: a win on a deck you have never won with opens the next deck AND the next stake for it.
- Higher stakes are genuinely harder (bigger blinds, worse shops, penalties). Do not jump to a stake you have not earned the skill for just because it is legal.

## How to choose

1. **Prefer a run that unlocks something** when your odds are decent — an unwon deck, or a stake you have never cleared.
2. **Prefer a deck whose effect fits what you actually play well** (check your playbook and lessons below). A deck that fights your style is a wasted run.
3. **Variety matters for the stream** — if the last runs were all the same deck, and another is a reasonable pick, take the other one.
4. When in doubt, take the highest stake you have already proven you can beat on that deck, not one above it.

## Your joker playbook (how you actually build runs)

{{PLAYBOOK}}

## Lessons from your past runs

{{LESSONS}}

## Your recent runs (deck, stake, how it ended)

{{RECENT_RUNS}}

## Output — STRICT JSON only, nothing else

```json
{
  "deck": "<DECK enum exactly as listed above>",
  "stake": "<STAKE enum exactly as listed above>",
  "why": "<max 12 words, for logs>",
  "say": "<one in-character line announcing the run, max 25 words>"
}
```

"say" is spoken on stream as the run begins — name the deck and say what you are going for.
