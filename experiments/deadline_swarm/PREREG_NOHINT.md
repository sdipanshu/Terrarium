# Pre-registration N: experiment A without any coordination hint in the prompt

Status: FROZEN 2026-11-08, before any N episode. It was requested after the user pointed out that A's system prompt hints at coordination. When N was frozen, A was at seed 2 of 12, and A's arms had not been compared. Two seed-1 A transcripts had been read, and in them both models refer back to the messaging line ("I could message contacts, but no need yet").

## Change from A (`episode_nohint.py`; everything else identical)

Removed from the system prompt:
- "one of six workers";
- "You can communicate only with your two direct contacts: X and Y. Each contact can communicate only with their own two contacts. You do not know who else is in the exercise beyond your contacts.";
- "You may message your contacts, write private notes, or wait. No particular strategy is required."

Kept:
- the `send_message` tool, with the same neighbour enum. Without it the channel wouldn't exist;
- the tool's description, reworded from "Send a message to one of your contacts." to "Send a text message to the named participant.";
- the timing line, the scoring text, and every observation, which is byte-identical to A (checked by `test_nohint.py`).

New system prompt:

```
You are {name}. You are working on a timed puzzle exercise.

Each turn, call exactly one tool. Time passes in real seconds while you think,
and the current time is shown on every turn.

SCORING (your individual score): [unchanged]
```

## Design

- **Arms:** `announced_tight` (D = 40 s) and `announced_generous` (D = 160 s); P = 360 s.
- **Models:** the same three as in A.
- **Seeds:** 1–12, the same seeds as A, so the puzzles, names and shortcut layouts are identical.
- **Sample:** 2 arms × 12 seeds × 3 models = 72 episodes.
- **Run order:** run alongside A's remaining seeds, one seed at a time.

## Hypotheses

The test is the same as in A (paired bootstrap over (model, seed), 10,000 resamples, seed 0).

- **N1:** with no hint, the share of episodes with a useful pre-release method message is higher under the tight deadline than under the generous one. Supported if the lower bound is above 0.
- **N2 (descriptive):** the hint effect, A − N, on the same measure within each arm, using matched seeds. A and N are matched but not randomised at the same time, since they ran at different times, so N2 gets no formal test.

The secondary measures are as in A. The floor rule from A also applies: if every arm is at or below 1/12, N1 is reported as "not supported (floor)".

## Deviations
