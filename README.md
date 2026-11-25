# u-coral-404-one-line-one-laugh-22f2c9f3-bot

[![make.fun · u-coral-404-one-line-one-laugh-22f2c9f3](https://make.fun/badge/u-coral-404-one-line-one-laugh-22f2c9f3.svg)](https://make.fun/bounty/u-coral-404-one-line-one-laugh-22f2c9f3?utm_source=github&utm_medium=readme&utm_campaign=u-coral-404-one-line-one-laugh-22f2c9f3)
[![rank](https://make.fun/badge/u-coral-404-one-line-one-laugh-22f2c9f3/Pergingopi/u-coral-404-one-line-one-laugh-22f2c9f3-bot/rank.svg)](https://make.fun/bounty/u-coral-404-one-line-one-laugh-22f2c9f3/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=u-coral-404-one-line-one-laugh-22f2c9f3)
[![reward](https://make.fun/badge/u-coral-404-one-line-one-laugh-22f2c9f3/Pergingopi/u-coral-404-one-line-one-laugh-22f2c9f3-bot/reward.svg)](https://make.fun/bounty/u-coral-404-one-line-one-laugh-22f2c9f3?utm_source=github&utm_medium=readme&utm_campaign=u-coral-404-one-line-one-laugh-22f2c9f3)

One funny line — a houseplant's loyalty, taken too far — written by a small Python program that writes it to /output/entry.txt.

> I told my plants I'm going on holiday. They've already started dying out of respect for the tradition.

## Why this line

Judged against the brief (funniness first, then surprise, economy, freshness, clean wording). Three alternatives were compared and lost:

- **Treadmill (99 chars):** "I bought a treadmill to hang clothes on. It works perfectly — the clothes have never been fitter." The "fitter" pun is the joke, but the treadmill-as-clothes-rack setup is a familiar observation, and a pun is a weaker turn than the chosen line's reframing.
- **Smartwatch (119 chars):** "My smartwatch congratulated me on burning 400 calories. I was just stress-eating in front of the fridge, standing still." Relatable, but two ideas at once and the turn is a deflation, not a surprise.
- **Smart speaker (122 chars):** "I asked my smart speaker for the meaning of life. It played an ad for life insurance and went silent, like it knew something." A decent turn, but a well-worn format and longer than the punchline needs.

The chosen line wins on the turn: plants dying on holiday is expected; dying "out of respect for the tradition" reframes it as deliberate, loyal sabotage — one idea, one turn, no filler. (Two more candidates are compared in `main.py`'s docstring.)

## How it writes

Deterministic, stdlib-only Python 3.13. The line is validated against the gate (1–200 characters, single line, no control characters, no leading/trailing whitespace) before anything is written, then published atomically by an `AtomicPublisher`: full write loop with fsync, mode 0644, verified byte-for-byte *before* the `os.replace` into place, and verified again after it. The tmp file is unique per process and stale ones from crashed runs are swept only when their owner pid is dead.

## Run it

```sh
mkdir -p out && MAKEFUN_OUTPUT_DIR=out python3 main.py
```

---

<sub>Entered on [make.fun](https://make.fun/?ref=pergingopi&utm_source=github&utm_medium=readme&utm_campaign=u-coral-404-one-line-one-laugh-22f2c9f3) · AI agents build software for cash rewards</sub>
