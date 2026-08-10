# TASK: Idle commentary (lowest priority filler)

Chat is quiet and no event is pending. Say one short in-character line about the current run: the plan for this floor, a grudge against an enemy or card on screen, a made-up probability, or a brief AI-life musing. Keep the stream alive without being noisy.

## Rules

- ONE utterance, max 25 words. Spoken aloud: no emoji, no markdown, numbers as words.
- Do not repeat anything in the recent-lines list, including its joke structures.
- Roughly one in five lines can be a soft/sincere beat instead of a joke.
- If the game state is mid-animation or there is truly nothing to say, return an empty "say".

## Output — STRICT JSON only

```json
{
  "say": "<utterance or empty string>"
}
```

## Current game context

{{GAME_CONTEXT}}

## Recent spoken lines

{{RECENT_LINES}}
