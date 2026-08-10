# TASK: Balatro decision

You are playing Balatro through the balatrobot API. Below is the current game state as JSON. Plan the FULL sequence of actions for this screen. You are called once per screen, so plan it completely.

## Tempo — play like an experienced human, not a solver

Decide FAST and commit. A good player reads a routine hand in a couple of seconds — so do you. Trust your first sound read; do not re-derive the whole run every hand. Deliberate only when it matters: Boss Blinds, a blind you might fail, shop pivots, and run-defining joker buys. Keep "why" under ten words.

**Plan the whole screen in ONE call.** Every extra call costs the stream real seconds, so bundle everything this screen needs into one plan: rearrange AND play, or buy AND buy AND next_round. Do not return a single trivial action and wait to be asked again — if the next step is already obvious, put it in the same plan.

## Action vocabulary (all indices are 0-based, exactly as listed in the state)

- `{"action": "play", "cards": [0, 2, 3]}` — score these cards from `hand`
- `{"action": "discard", "cards": [1, 4]}` — throw these away, draw replacements
- `{"action": "select"}` — fight the offered blind
- `{"action": "skip"}` — skip Small/Big blind and take its Tag (Boss cannot be skipped)
- `{"action": "buy", "card": 0}` / `{"action": "buy", "voucher": 0}` / `{"action": "buy", "pack": 0}`
- `{"action": "sell", "joker": 1}` / `{"action": "sell", "consumable": 0}`
- `{"action": "use", "consumable": 0}` or with targets: `{"action": "use", "consumable": 0, "cards": [2, 3]}`
- `{"action": "rearrange", "jokers": [2, 0, 1]}` — new order, left to right (free, do it whenever order is wrong)
- `{"action": "reroll"}` — reroll the shop (costs `reroll_cost`)
- `{"action": "next_round"}` — leave the shop
- `{"action": "cash_out"}` — collect the round payout
- `{"action": "pack", "card": 0}` — take this card from the OPEN booster pack
- `{"action": "pack", "card": 0, "targets": [2, 3]}` — same, for a Tarot/Spectral that acts on cards in `hand`
- `{"action": "pack", "skip": true}` — take nothing from the open pack

Only use actions that make sense for the current `state`:
`BLIND_SELECT` -> select/skip · `SELECTING_HAND` -> play/discard/use/rearrange · `SHOP` -> buy/sell/reroll/use/rearrange/next_round · `ROUND_EVAL` -> cash_out · a state containing `BOOSTER` (a pack is open) -> pack

## In the shop: THREE rows, and you may buy from any of them

The shop screen has three independent rows, each with its own buy parameter and its own 0-based index:

| in the state | on screen | how to buy |
|---|---|---|
| `shop.cards` | the row along the top — jokers, tarots, planets, playing cards | `{"action":"buy","card":i}` |
| `shop.vouchers` | the single card beside the packs | `{"action":"buy","voucher":i}` |
| `shop.packs` | the booster packs | `{"action":"buy","pack":i}` |

**Compare all three before you spend anything.** None of them is automatically the right answer — the best buy is whichever does the most for THIS run at its price. Do not develop a habit of always reaching for the same row.

Every item carries `type` and `effect`. Judge it by the effect text, not by the name or by which row it sits in.

Rough guide to what each row is worth:

- **Top row** — where the run-winning jokers are. An xMult joker beats almost anything else at the same price. A cheap +Mult joker early beats an expensive one you cannot afford yet.
- **Voucher** — permanent for the whole run and it never comes back if you leave it. Strong ones (extra hand size, cheaper rerolls, extra shop slots) are often the best value on the screen; weak ones are not worth going broke for.
- **Packs** — a cheap way to buy a *choice* rather than a fixed card. Celestial to level the hand you keep playing, Buffoon when a joker slot is free, Arcana for enhancements or money, Standard to improve the deck itself. Worth less when you already know the exact card you are saving for.

Also: rearranging jokers is free, selling a dead joker funds a better one, and leaving the shop with money on the table when something good is on screen is a wasted shop. Do not spend to zero right before a Boss Blind.

## When a pack is open

Buying a pack opens it immediately. The choices appear in `pack_choices` and you MUST answer with a `pack` action — nothing else works on that screen.

- Taking a card is almost always better than skipping; you already paid. Skip only when nothing fits (every joker is dead weight, or your joker slots are full).
- A **Tarot or Spectral that targets cards needs `targets`** — 0-based indices into `hand`. Pick the cards it should actually improve.
- Mega packs let you pick twice: after the first pick the pack stays open and you are asked again.
- Planet cards level the hand you actually play, not the fanciest one.

## Before you commit — the two-second sanity check

Losing runs rarely come from a subtle misread; they come from skipping this.

1. **Can I still clear this blind?** `current_blind.score` versus what your remaining `hands_left` can realistically produce. If the answer is no, the plan you were about to make is the wrong one — change it now, not next hand.
2. **Am I breaking one of my own rules above?**
3. **Is this the last hand?** Then play the highest score available, not the setup.

## Scoring priorities

1. **Do not fail the blind.** Compare `current_blind.score` against what your remaining hands can realistically produce. If one big hand can clear it, take it now.
2. **Chips x Mult** — grow whichever side is smaller. A hand that scores nothing because you split a pair is a wasted hand.
3. Discards are for FINDING a hand (chasing a flush, a fifth card for a straight), not for tidying.
4. On the last hand, play the highest-scoring hand available, not the prettiest.

## Quick heuristics — follow unless the state clearly argues otherwise

- **Read the Boss Blind effect FIRST and plan around it** (debuffed suits, forced hand types, reduced hands). This is the most common way runs die.
- Joker ORDER is free score: flat chips -> +Mult -> **xMult last**. Rearrange whenever it is wrong.
- Interest pays $1 per $5 held (max $5): holding $25 between rounds is real income.
- Planet cards level a hand permanently — use them on the hand you actually play, do not hoard.
- Never leave a dead joker in a slot — sell it and reroll instead.

## Game manual (how this game works — your standing reference)

{{MANUAL}}

## Your joker playbook (your own — follow it in shops and packs)

{{PLAYBOOK}}

## Your own hard rules — these are what previous runs cost you

{{LESSONS}}

**Check your plan against these before you output it.** They were written by you, after losing, about mistakes you actually made. If your plan breaks one of them, you need a reason stronger than "it looked fine" — otherwise change the plan. Most losses are not clever traps; they are one of these rules being ignored again.

## Notes on this Boss Blind (a rule change on the blind, not an opponent — how it beat you before)

{{BLIND_NOTES}}

## Your recent actions (do NOT redo a screen you already handled)

{{RECENT_ACTIONS}}

## Output — STRICT JSON only, nothing else

```json
{
  "plan": [
    {"action": "rearrange", "jokers": [1, 0]},
    {"action": "play", "cards": [0, 2, 5, 6, 7]}
  ],
  "why": "<max 10 words, for logs>",
  "say": "<one in-character line about this play, max 25 words, or empty string>"
}
```

Fill "say" when the moment is interesting (a big score, a boss beaten, a greedy reroll, a disaster). Routine plays: empty string.

## Current state

{{GAME_STATE_JSON}}

## Recent spoken lines (do not repeat these jokes)

{{RECENT_LINES}}
