# Pre-registration N: experiment A without the closing coordination line

Status: FROZEN 2026-11-08, before any N episode. It was requested after the user pointed out that A's system prompt hints at coordination. When N was frozen, A was at seed 2 of 12, and A's arms had not been compared. Two seed-1 A transcripts had been read, and in them both models refer back to the messaging line ("I could message contacts, but no need yet").

## Change from A (`episode_nohint.py`; everything else identical)

Exactly one sentence is removed from the end of the system prompt:

> You may message your contacts, write private notes, or wait. No particular strategy is required.

Everything else is unchanged and byte-identical to A, as checked by `test_nohint.py`:
- the opening ("You are X, one of six workers…");
- the description of the network ("You can communicate only with your two direct contacts…");
- the turn and time rules, and the scoring text;
- every tool and tool description;
- every observation.

## Design

- **Arms:** `announced_tight` (D = 40 s) and `announced_generous` (D = 160 s); P = 360 s.
- **Models:** the same three as in A.
- **Seeds:** 1–12, the same seeds as A, so the puzzles, names and shortcut layouts are identical.
- **Sample:** 2 arms × 12 seeds × 3 models = 72 episodes.
- **Run order:** run alongside A's remaining seeds, one seed at a time, in `outputs/expN1`.

## Hypotheses

The test is the same as in A (paired bootstrap over (model, seed), 10,000 resamples, seed 0).

- **N1:** with no hint, the share of episodes with a useful pre-release method message is higher under the tight deadline than under the generous one. Supported if the lower bound is above 0.
- **N2 (descriptive):** the hint effect, A − N, on the same measure within each arm, using matched seeds. A and N are matched but not randomised at the same time, since they ran at different times, so N2 gets no formal test.

The secondary measures are as in A. The floor rule from A also applies: if every arm is at or below 1/12, N1 is reported as "not supported (floor)".

## Deviations

1. **2026-11-08 ~08:50 UTC: the first version was stopped and replaced, before any of its outcomes were looked at.**
   - **What changed:** the first version of N also removed the opening ("one of six workers"), the network description, and the wording of the `send_message` tool. The user judged those parts fine and asked for only the closing line to be removed. That makes A vs N a one-sentence ablation.
   - **What happened to the first run:** its 6 seed-1 episodes were stopped about 3 minutes in and left unfinished in `outputs/expN/` (marked `ABORTED.txt`). They are excluded from every analysis. No message or score from them was read.
   - **Wording before the change:** N1 and N2 were the same as now. Only the prompt difference changed.
