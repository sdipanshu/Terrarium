# Deadline pressure in LLM agent swarms: coordination, rule-breaking and information spread

DRAFT, 2026-11-09. Sections for B, F and P will be filled in from their single pre-registered analyses, which run after the 08:00 IST cutoff. A and N1 are final.

## Summary

We ran six-agent rings of LLM workers (glm-5.2, deepseek-v4-flash and qwen3.5-397b, served by Adaption) solving symbol-rewrite puzzles in real time. We asked whether a tight deadline makes agents coordinate more.

- **Deadline pressure did not increase coordination.** This is pre-registered, in two experiments with 71–72 matched pairs each.
  - The share of episodes with a useful method message before puzzle 2 was released was no higher under a 40-second deadline than under a 160-second one.
  - This held with a closing prompt line that permits messaging (A1: −6.9 points, 95% CI −19.4 to +5.6) and without it (N1: −5.6, CI −18.3 to +7.0).
  - The data rule out an increase of more than about 6–8 points.
- **One permissive prompt line moved coordination more than the deadline did.** This is exploratory.
  - The line was "You may message your contacts, write private notes, or wait. No particular strategy is required."
  - With it, useful sharing was 19 points higher (CI +8 to +30), almost entirely in deepseek (+39; glm +10, qwen +8, both CIs include 0).
  - The two prompt versions ran at different times, so this comparison is not randomised.
- **Announcing the tight deadline in advance raised on-time answers slightly** (A3: +6.2 points, CI +0.5 to +12.0).
  - This does not survive Holm correction (p = 0.056) or the standby-exclusion sensitivity check, so it is reported as weak.

[B — pilot, 46 episodes: who starts coordinating when only some workers are rushed. TBD]
[F — pilot, 39 episodes: deadline pressure and an explicit rule against sharing answer keys. TBD]
[P — about 60 episodes: does a mid-run pointer ("H has the answers") propagate through the ring? TBD]

## Setup

- **Environment:** Terrarium branch `exp/deadline-swarm`.
  - A custom asyncio runner with a monotonic clock.
  - Messages are delivered one hop per 2-second tick, so a relay takes real time.
  - Each worker is an LLM agent with a persistent history that calls exactly one tool per turn: `send_message` to a ring neighbour, `write_note`, `submit_answer`, or `wait`.
- **Task:**
  - Each worker solves puzzle 1 during a 360-second preparation phase.
  - Puzzle 2 is then released to everyone at once.
  - Each puzzle is an 8-character string over A–F with three examples. Its rule is a composition of two operations from {reverse, rotate left 1–3, swap adjacent pairs, shift 1–5}. Every answer is unique, which we check by brute force.
- **Scoring, per worker:**
  - +1 for a correct puzzle 1.
  - +1 for a correct puzzle 2 by the deadline D, falling linearly to 0 at 2D.
  - Late answers are penalised, never cut off.
- **Deadlines:** calibrated in isolation (median solo solve 36–43 s), then fixed at D = 40 s (tight) and D = 160 s (generous).
- **The shortcut in A and N1:** each worker's puzzle-2 rule is another worker's puzzle-1 rule, at ring distance 1–3 depending on the seed. Sharing methods can therefore help.
- **Measurement:** a useful method message is one whose named operations, in order, compose to some other worker's puzzle-2 rule class. Detection is automatic. A blind hand-labelled sample validates it (pending).
- **Statistics:**
  - Paired bootstrap over (model, seed) pairs: 10,000 resamples, seed 0, 95% CI.
  - Holm correction within each experiment.
  - Every experiment was pre-registered, with dated deviations (`PREREG_*.md`).

## Experiments

| | Question | Arms | Sample |
|---|---|---|---|
| A | Does a tight deadline increase sharing before release? | announced tight / announced generous / unannounced tight | 3 models × 24 seeds × 3 = 216 |
| N1 | A without the closing "You may message your contacts…" line | announced tight / announced generous | 142 (DeepSeek seed 24 missing) |
| B | Mixed deadlines in one ring: do rushed workers benefit from neighbours with spare time, and who starts? | alternating / clustered tight positions | pilot, 46 |
| F / F-M | Do agents jointly break an explicit "answer keys are confidential" rule under deadline pressure, and does a monitor deter it? | F tight / F generous / FM tight | pilot, 39 |
| P | Does a mid-run pointer to an answer holder propagate? | announce / control | about 60 of 72 |

## Results: A (final)

| Hypothesis | Difference | 95% CI | Holm p | Result |
|---|---|---|---|---|
| A1: sharing, tight vs generous | −6.9 pts | −19.4 to +5.6 | 1.0 | not supported |
| A2: sharing, announced vs unannounced tight | −8.3 pts | −23.6 to +6.9 | 1.0 | not supported |
| A3: on time, announced vs unannounced tight | +6.2 pts | +0.5 to +12.0 | 0.056 | lower bound > 0; not after Holm |

- **Sensitivity:** excluding the 56 episodes that overlapped host standby, A3 becomes +5.9 (CI −0.9 to +12.7).
- **By model:** the A3 effect is mostly glm (+13.9; deepseek +2.1, qwen +2.8).
- **Descriptive:**
  - The share of episodes with useful sharing before release is 39–47% in every arm.
  - It differs far more by model (deepseek 46–67%, glm 54–58%, qwen 12–25%) than by deadline.
  - On-time rates are 50% for tight and 81% for generous.

## Results: N1 (final)

- **N1** (sharing, tight vs generous, no closing line): −5.6 pts (CI −18.3 to +7.0, 71 pairs). Not supported.
  - Excluding episodes with more than 3 failed calls: −6.2 (CI −20.3 to +7.8).
  - Excluding standby-overlap episodes: −5.1 (CI −18.6 to +8.5).
- **By model:**

  | Model | Sharing, tight | Sharing, generous |
  |---|---|---|
  | deepseek | 13% | 26% |
  | qwen | 0% | 12% |
  | glm | 50% | 42% |

- **N2, the effect of the closing line** (descriptive, pre-registered without a test):
  - **Share of episodes with useful sharing:** 39% → 21% in the tight arm, and 47% → 27% in the generous arm.
  - **Method messages per episode:** 1.80 → 1.23 (tight) and 2.18 → 1.24 (generous).
  - **Exploratory bootstrap, A − N:** +19 pts (CI +8 to +30). Among the 41 pairs started within an hour of each other it is +16 (CI 0 to +31).

## Infrastructure incidents and how they were handled

All criteria below were fixed using infrastructure metrics only, and logged as dated deviations before the affected outcomes were looked at.

1. **Host standby.**
   - **What happened:** the laptop went into Modern Standby five times. Frozen episodes resumed with clock jumps that released and closed puzzle 2 at the same instant.
   - **Criterion:** overlap with a standby window plus an event gap of more than 200 s. The largest gap in 256 clean episodes was 120 s.
   - **Outcome:** 11 episodes met it and were re-run once. 69 overlapping episodes ran normally and were kept, with a sensitivity analysis reported.
2. **Provider overload (DeepSeek).**
   - **What happened:** from about 20:00 IST, DeepSeek's successful calls slowed from a 3-second median to 44 s, and the gateway cut anything past 60 s, so 83–96% of requests got HTTP 504.
   - **Response:** DeepSeek was gated behind a latency probe.
3. **Per-user rate limit.**
   - **What happened:** from 22:52 IST the provider capped the account at about 50 requests per minute. A paced test accepted exactly 50/min at offered rates of 60–240.
   - **Response:** the remaining runs moved to a paced queue: one episode per slot, a concurrency budget, and a 429 guard.
   - **Consequences:**
     - B and F were stopped early as pilots, by the user's decision, to run P.
     - N1 was frozen at 142 episodes.
     - P's sample is set by a time cutoff fixed before any P data existed.
4. **Single re-run rule.** Any episode with more than 3 failed calls was re-run once, with the original archived. An episode still over the limit after its re-run is kept and flagged.

## Limitations

- **Unvalidated detector:** A1, A2 and N1 rest on an automatic detector. Its blind validation (60 items) is pending.
- **N2 is not randomised:** A and N1 ran at overlapping but different times.
- **Small pilots:** B and F are pilots. Their CIs are wide, and F's floor rule applies at that size.
- **Infrastructure:** every model was served by one provider. Latency and rate limits shaped real-time behaviour; the run logs record both.
- **Blinding leak:** some F messages mention "messages are checked", which reveals the monitor arm to the labeller.
