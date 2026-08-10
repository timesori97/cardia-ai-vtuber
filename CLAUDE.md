# Project: AI VTuber Streaming System ("Cardia")

You (Claude Code) are building a fully automated AI VTuber that plays **Slay the Spire** live on Twitch, talks with a TTS voice through a veadotube avatar, and reacts to chat and donations. The owner (박성준) is a junior developer; explain what you do in Korean, keep code comments in English.

## Hard constraints — read first

- **Hardware**: Windows, Intel Celeron 6305 (2C/2T, 1.8GHz), 16GB RAM, Intel UHD integrated graphics.
  - NO local LLMs, NO heavy vision models, NO video processing in Python.
  - OBS must use **QSV hardware encoding**, 1280x720 @ 30fps.
  - Piper TTS is the ONLY local ML allowed (it runs on Raspberry-Pi-class hardware).
- **Budget**: zero additional spend. The brain is `claude -p` headless calls using the owner's existing subscription. No API keys.
- **Game state comes as TEXT, never screenshots.** Slay the Spire → Communication Mod → JSON over stdin/stdout. Never build a screen-capture/vision pipeline.
- **Secrets**: the Twitch **stream key lives only inside OBS**, entered by the owner by hand. Scripts never see it. Chat reading uses anonymous IRC (no token). Never write any credential into a file, log, or chat message. If a task seems to need a secret, stop and ask the owner to do that step manually.
- **Admin installs** (VB-Cable driver, OBS, Steam Workshop mods): do not attempt silently. Point the owner to the matching item in `USER_TODO.md` and wait.

## Low-spec survival rules (2-core CPU — every cycle counts)

- Slay the Spire: **windowed 1280x720, all graphics options lowest**, V-Sync on (caps GPU load).
- OBS: QSV encoder, 720p30, bitrate 2500–3500 kbps, bilinear downscale filter, **disable the preview while live** (right-click preview → disable), no extra filters/plugins.
- Piper: use a `-medium` quality voice; if TTS stutters during gameplay, drop to `-low`.
- During streams: browsers and other heavy apps closed. The orchestrator logs CPU% every 30s and prints a warning above eighty-five percent.
- Dropped-frames fallback ladder, in order: 720p30 → 864x486 → 640x480, then lower game window size. Test each for ten minutes before going further.

## Guided setup mode — you lead every USER_TODO step

The owner is a beginner. USER_TODO steps are NOT "wait until the owner figures it out" — you drive each one interactively:

- Do everything automatable yourself: download installers (PowerShell), extract, launch them (the UAC prompt is the owner's single click), open exact URLs with the connected browser integration, write config files directly.
- Verify programmatically after each step: audio devices via `sounddevice` (look for "CABLE"), Workshop mods via `steamapps\workshop\content\646570\<mod_id>` folders, OBS config presence, bandwidth via `speedtest-cli`.
- When the owner's hands are needed, give ONE click-level instruction at a time, in Korean, and confirm success before continuing.
- **Never ask for, accept, or type: passwords, verification codes, CAPTCHA answers, stream keys, payment info.** If the owner pastes one into chat, tell them to reset/change it and enter it only in the target app themselves. Browser integration is for opening pages and guiding clicks — never for credential fields.

## Architecture

```
Slay the Spire ──CommunicationMod(JSON stdio)──▶ orchestrator.py
Twitch chat ────anonymous IRC (justinfan)──────▶ orchestrator.py
                                                    │
                             ┌── event queue (priority: donation > chat > commentary)
                             │
                             ├──▶ brain.py ── `claude -p --model <route>` ──▶ JSON {command|say}
                             │         (persona.md + prompts/<task>.md + input data)
                             │
                             ├──▶ game command ──▶ CommunicationMod stdin
                             └──▶ say text ──▶ tts.py (Piper) ──▶ WAV ──▶ "CABLE Input" device
                                                                             │
                                              veadotube mini (mic: CABLE Output) → lip sync
                                              OBS (audio source: CABLE Output + game capture) → Twitch
```

## Model routing (see `config/models.yaml`)

| Task | Model | Why |
|---|---|---|
| Game decisions (`prompts/game_decision.md`) | `sonnet` | needs real reasoning |
| Chat reactions (`prompts/chat_react.md`) | `haiku` | high frequency, cheap+fast |
| Donation reactions (`prompts/donation_react.md`) | `haiku` | fast; must feel instant |
| Idle commentary (`prompts/idle_commentary.md`) | `haiku` | filler, cheapest |
| Borderline-message safety check (`safety.md` layer 1) | `haiku` | classifier only |

Brain call pattern (adjust after checking `claude --help` on the installed version):

```
claude -p "<assembled prompt>" --model haiku --output-format json --max-turns 1
```

- Runtime brain calls are **pure text generation**: no tools needed. Do not grant `--allowedTools` beyond nothing; keep `--max-turns 1`.
- Check whether the installed CLI supports a system-prompt flag (`claude --help`). If yes, pass `persona.md` there; if not, prepend it to the prompt.
- Every prompt file declares a strict JSON output contract. Parse defensively: on malformed output, retry once, then drop the utterance (never crash the stream loop).
- Subscription usage limits are real. Batch chat every 20–30s, cap commentary cadence, and warn the owner to start with 1–2 hour streams.

## Build phases — do them in order, verify each, ask before moving on

**Phase 0 — Environment audit.** Check: Python 3.10+, pip, git, `claude auth status` (exit 0), Steam + Slay the Spire install path, upload bandwidth note. Report findings in Korean.

**Phase 1 — Game link.** Lead the owner through USER_TODO #4 in guided mode first: open the three Workshop pages, owner clicks Subscribe, then verify the mod folders exist. Install `spirecomm` (pip; if the PyPI build is stale, clone github.com/ForgottenArbiter/spirecomm). Configure Communication Mod (`%LOCALAPPDATA%\ModTheSpire\CommunicationMod\config.properties`) so `command=` launches our `orchestrator.py` in game-link mode. ✅ Test: launch StS with mods, orchestrator logs a `game_state` JSON to console.

**Phase 2 — Brain.** Write `brain.py`: loads `persona.md` + task prompt + input, calls `claude -p` per routing table, parses JSON, one retry on parse failure, logs latency per call. ✅ Test: feed a canned StS state JSON → valid `{"command": ...}`; feed a fake chat batch → valid `{"say": ...}`.

**Phase 3 — Voice.** Lead the owner through USER_TODO #2 in guided mode first: download+extract+launch the installer yourself, owner clicks UAC and reboots, then verify CABLE devices via sounddevice. Download Piper Windows release from GitHub + one en_US female voice (try `en_US-amy-medium`; offer alternatives). Write `tts.py`: text → WAV → play on the audio device whose name contains "CABLE Input" (use `sounddevice`; list devices, match by substring). Strip characters that TTS mangles (emoji, markdown, asterisks). ✅ Test: a sentence plays audibly through VB-Cable monitoring.

**Phase 4 — Avatar assets.** Generate 4 placeholder PNGs (512×512, transparent) into `avatar/` with PIL: flat vector-style card-dealer girl, palette deep red `#C1121F` / navy `#003049` / cream `#FDF0D5`, playing-card hair ornament. States: `idle_closed.png`, `idle_open.png` (mouth open), `blink_closed.png`, `blink_open.png`. Crude is fine — it's a placeholder until commissioned art. Then lead USER_TODO #3 in guided mode: download and launch veadotube yourself, and walk the owner through registering the PNGs and setting mic to CABLE Output, one click at a time. ✅ Test: owner confirms mouth moves when Phase 3 test audio plays.

**Phase 5 — Twitch chat.** Write `twitch_chat.py`: anonymous IRC (`irc.chat.twitch.tv:6667`, nick `justinfan<random>`, `CAP REQ :twitch.tv/tags twitch.tv/commands`), join `#<TWITCH_CHANNEL>` from `.env`. Parse: PRIVMSG (+ `bits=` tag), USERNOTICE (subs/gift subs/raids). Read-only; the bot never sends chat messages. ✅ Test: live messages from the owner's channel print to console.

**Phase 6 — Orchestrator.** `orchestrator.py` ties it together: priority event queue (donation > filtered chat > idle commentary), separate speech queue (never interrupt an utterance mid-playback; drop stale chat older than 60s; dedupe), game loop runs independently of speech. Implement the full filter pipeline from `safety.md` BEFORE any chat text reaches the brain. Kill switch: global hotkey Ctrl+F12 clears the speech queue and mutes TTS. Include `--dry-run` mode (console I/O, no Twitch needed). ✅ Test: dry-run a full fake session: game state + fake chat + fake bits event → correct priority order, speech text logged.

**Phase 7 — OBS + go live.** Install OBS via `winget install OBSProject.OBSStudio` (ask first). Pre-write a Scene Collection JSON and profile (QSV, 720p30, sources: game capture + veadotube window w/ chroma key + audio: CABLE Output) into %APPDATA%\obs-studio so the owner builds nothing by hand; verify settings after OBS first launch. The owner's only manual action: pasting the stream key into Settings->Stream (USER_TODO #1). Run speedtest-cli for the bandwidth check. ✅ Test: 10-minute unlisted/test stream; watch CPU% and dropped frames; if CPU >80%, drop to 480p or lower game settings.

## Roadmap after v1 (do not build now)

- Balatro module: same brain, swap Phase 1 for a balatrobot-style state mod when the owner buys the game.
- Korean-lesson segment + TikTok Live module (planned "gift → Korean phrase" format).
- Commissioned Live2D upgrade path.
