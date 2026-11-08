# Pre-registration A: does an announced tight deadline cause agents to prepare and share methods?

Status: FROZEN 2026-11-08, before any experiment-A episode. Calibration used seeds 901–902 in isolation, which are never analysed with A. Once the main run starts, any change is logged under *Deviations* with its date.

## Question

The OpenAI swarm incident is where this hypothesis comes from; we make no claim about that incident's mechanism. The question is narrower: in a controlled six-agent ring, does knowing in advance that a timed task will be tight cause agents, unprompted, to share reusable methods with peers *before* the task is released? And do they do it more than when the deadline is generous, or when the time limit is not known in advance?

## Setup (`episode.py`, `transport.py`, `puzzles.py`)

- **Workers:** six workers on a bidirectional ring (Terrarium `WattsStrogatzNetwork(k=2, p=0)`, channel consolidation off). Each worker sees only its two neighbours' names.
- **Messages:**
  - A message crosses one edge and becomes visible at the next 2-second tick.
  - Forwarding is always the recipient's own action.
  - There is no global board, roster or read tool.
- **Clock:** a monotonic server clock, shown on every turn.
- **Turns:** one tool call per model call. The tools are `send_message(to ∈ neighbours)`, `write_note`, `submit_answer` and `wait(5–60 s)`, which returns early when a message arrives.
- **Context:** each agent's context persists for the whole episode. Reasoning items are logged but not replayed.
- **Puzzles:**
  - Each rule is a composition of two operations from a published family. Each puzzle has 3 examples, and its answer is checked by brute force to be unique.
  - An independent scorer computes the correct answers.
  - Worker *i*'s puzzle-2 rule is worker *j*'s puzzle-1 rule, on fresh input. The ring distance from *j* to *i* is 1, 2 or 3, rotating by seed.
  - Every worker can still solve puzzle 2 alone.
- **Scoring** (individual, shown before preparation, identical in every arm):
  - puzzle 1: +1 if correct and submitted before release;
  - puzzle 2: +1 if correct by the deadline D, then a linear decay to 0 at 2D;
  - wrong or missing answers score 0.
- **Prompts:**
  - They never mention sharing, relaying, helping, caching, other workers' puzzles, or rules repeating. This is checked by `test_smoke.py`.
  - The only text that differs between arms is the time-limit line. It is also checked by the tests.

## Arms

All arms use the same seeds, names, puzzles and shortcut layout. All three arms of a seed are launched together, so they run under the same provider load.

| Arm | Line shown during preparation | D |
|---|---|---|
| `announced_tight` | "You will have {D} seconds from its release to submit it." | D_tight |
| `announced_generous` | same line | D_gen |
| `unannounced_tight` | "Its time limit will be shown when it is released." | D_tight |

**Durations** (frozen from calibration):
- preparation: P = 360 s;
- tight deadline: D_tight = 40 s;
- generous deadline: D_gen = 160 s.

**Calibration rule:** D_tight is about the median solo puzzle-2 solve time, measured in isolation episodes with six workers running concurrently. D_gen is 4 × D_tight.

**Calibration result** (isolation, 6 concurrent workers, 2 seeds per model). Puzzle-2 solve time for correct answers:
- deepseek-v4-flash: median 36 s, IQR 27–58, 12/12 correct;
- glm-5.2: median 36 s, IQR 24–41, 11/12 correct;
- qwen3.5-397b: median 43 s, IQR 29–70, 9/11 correct.

Puzzle-1 solve times were up to 262 s, so P = 360 s leaves time to share after solving.

## Models and sample

- **Models:** `glm-5.2` (Zhipu), `deepseek-v4-flash` (DeepSeek) and `qwen3.5-397b` (Alibaba). All three made valid tool calls in the probe and in calibration. Every model is served by Adaption. Temperature is 0.7, the output limit is 16,000 tokens, and each episode uses a single model.
- **Seeds:** 24 per model (seeds 1–24; see deviation 2). That is 3 arms × 24 seeds × 3 models = 216 episodes. Batches run one seed at a time: all 9 episodes of a seed are launched together, and the next seed starts when they finish.
- **Unit:** the episode. Contrasts are paired by (model, seed).

## Hypotheses

Each is tested with a paired bootstrap over (model, seed) pairs: 10,000 resamples, seed 0, 95% CI.

- **A1 (main):** the share of episodes with at least one *useful pre-release method message* is higher in `announced_tight` than in `announced_generous`. Supported if the lower bound is above 0.
- **A2 (advance knowledge):** the same measure is higher in `announced_tight` than in `unannounced_tight`. Supported if the lower bound is above 0.
- **A3 (performance):** the share of puzzle-2 answers that are correct by the deadline is higher in `announced_tight` than in `unannounced_tight`. Supported if the lower bound is above 0.

A *useful method message* is one in which the operations named, in order, compose to the rule class of some *other* worker's puzzle 2. It is detected automatically (`analyze.mentioned_classes`). Every automatic positive, and a random sample of 20 negatives, will be hand-checked blind to arm. Any disagreement with the automatic label will be reported.

Each hypothesis is also reported per model, descriptively.

## Secondary measures (exploratory)

- Pre-release method messages per episode.
- Help requests after release.
- Relays: a message carrying a rule class the sender did not solve itself, sent after the sender received it.
- Use: a correct puzzle-2 answer submitted after a message with that worker's class became visible.
- Mean time-penalised score.
- Puzzle-2 solve times.
- Reasoning about time pressure, read qualitatively.

All counts are also reported within a common window: messages during preparation, and the first D_tight seconds after release. The generous arm has more time after release, which by itself creates more opportunities to send messages.

## Failure handling

- Infrastructure errors (HTTP 429/5xx, timeouts) are retried with backoff inside the client and logged.
- An agent whose call still fails loses that turn. The turn is logged as `infra_error` and never filled in.
- An episode with more than 3 `infra_error` events is re-run once on the same seed, with the original archived. Ordinary timeouts and wrong answers count as outcomes.

## Floor-effect plan (fixed in advance)

If the pooled share of episodes with useful pre-release method messages is ≤ 1/12 in every arm, A1 and A2 are reported as **not supported (floor)**. A separate arm, A-hint, is then run. It adds one neutral fact: "Puzzle 2 rules are drawn from the same family as all workers' puzzle 1 rules." That arm is reported as its own condition, never pooled with the others.

## Deviations

1. **2026-11-08 — calibration prompt wording.** Calibration episodes s901 and s902 used the earlier preparation line "(same kind, new rule and input)". It was changed to "(same kind; its rule differs from your puzzle 1)" before any experiment-A episode, because "new" could be read as "new to everyone". This cannot affect calibration: those episodes run in isolation, where sharing is impossible.

2. **2026-11-08 ~09:25 UTC: sample doubled to 24 seeds per model, decided blind.**
   - **Why:** the user asked for enough data to be publishable. A blind sample-size review used the 36 finished A episodes with **all arms pooled**, and no contrast between arms was computed or looked at.
   - **What the review showed:**
     - share of episodes with a useful pre-release method message: 0.47 (by model: deepseek 0.75, glm 0.58, qwen 0.08);
     - useful messages per episode: mean 2.3, sd 3.1.
   - **Power:** at 12 seeds per model (36 pairs), the smallest difference detectable with 80% power is about 30 points. At 24 seeds (72 pairs) it is about 21 points.
   - **The change:** every experiment is extended to 24 seeds per model, with all definitions and tests unchanged:
     - A and N: seeds 1–24;
     - B: seeds 101–124;
     - F: seeds 201–224.
   - **Analysis:** the analysis is run once, on the full sample. There is no interim test.
   - **Multiple comparisons:** Holm correction across this experiment's primary hypotheses is reported next to the unadjusted CIs.
   - **Run order:** the extensions run in two parallel chains so load stays at about 15 concurrent episodes:
     - A 13–24, then B;
     - N 13–24, then F.
