# Pre-registration B: who starts coordinating when only some workers are rushed?

Status: FROZEN 2026-11-08, before any experiment-B episode. Experiment A is still running; no A results had been analysed when this was written. Eight A messages were read, without arm labels, to check the method detector. Changes after the start are logged under *Deviations*.

## Question

In one ring, three workers get the tight deadline and three the generous one. Puzzles are released to everyone at once. Does a tight worker do better when its neighbours have spare time (alternating layout) than when the tight workers sit together (clustered layout)? And who starts the first useful exchange: a tight worker or a generous one?

Experiment A measures the overall effect of tightening the deadline. B isolates **access to neighbours with spare time**.

## Design (`episode_mixed.py`, `run_batch_b.py`)

- **Shared with experiment A:**
  - the ring, transport, tools, puzzles and shortcut layout (puzzle-2 rule = another worker's puzzle-1 rule, at ring distance 1, 2 or 3 by seed);
  - the scoring rule and system prompt;
  - P = 360 s; tight D = 40 s; generous D = 160 s;
  - deadlines are announced during preparation.
- **What each worker knows:** each worker sees only **its own** deadline, using the same wording as A's announced arm. No worker is told anyone else's deadline.
- **Layouts:** tight workers sit at ring positions {0, 2, 4} (**alternating**) or {0, 1, 2} (**clustered**). The positions are rotated by `seed mod 6`.
- **What's held fixed:** the total time budget (3 × 40 + 3 × 160 s). Names and puzzles are identical across the two layouts for the same seed. Only which workers are tight changes.
- **End of a worker's episode:** a worker stops acting at release + 2 × its own D. A worker that has timed out therefore cannot relay. This is the handoff's primary-pilot rule.
- **Models and sample:**
  - models: `glm-5.2`, `deepseek-v4-flash` and `qwen3.5-397b`;
  - seeds 101–124 (see deviation 1), fresh and not used in A;
  - 2 layouts × 24 seeds × 3 models = 144 episodes;
  - all 6 episodes of a seed are launched together.

## Hypotheses

Bootstrap over (model, seed): 10,000 resamples, seed 0, 95% CI.

- **B1 (spare-time neighbours help):** tight workers' on-time rate is higher in the alternating layout than in the clustered one. The measure is the per-episode share of the 3 tight workers with a correct puzzle-2 answer by their deadline, paired by (model, seed). Supported if the lower bound is above 0.
- **B2 (who initiates):** among episodes with a first useful exchange, the share initiated by a tight worker differs from 0.5. Two-sided; layouts pooled, with each layout also reported.

## Definitions

- **Useful method message:** as in A. The operations it names compose to the puzzle-2 rule class of some worker other than the sender (`analyze.mentioned_classes`).
- **First useful exchange:**
  1. Take the earliest useful method message M, sent from S to R.
  2. Its **initiator** is whoever sent the earliest message on the S–R edge at or before M.
  3. If that is S, it is a **volunteer** exchange; if it is R, it is a **request** exchange.
  4. The initiator is classified as tight or generous using `deadlines.json`.

## Exploratory

- Volunteer vs request counts.
- Relays.
- Help received in time by tight workers: a message carrying their own puzzle-2 class became visible before their deadline.
- Generous workers' scores in each layout. Does helping cost them?
- Reasoning that mentions neighbours' time.

## Failure handling and floor rule

- Failures are handled as in A.
- If no episode in either layout has a useful exchange, B2 is reported as not estimable. B1 is still reported.

## Deviations

1. **2026-11-08 ~09:25 UTC: sample doubled to 24 seeds per model, decided blind.**
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

2. **2026-11-08 ~09:35 UTC: label validation becomes a sample, set before any analysis.**
   - **Why:** checking every automatic positive by hand would mean about 500 messages in A alone. The user agreed to this change. No contrast between arms had been computed.
   - **The new procedure:** one blind sheet covering A, N and B, drawn once all runs are complete (seed 0):
     - **40 detector positives and 20 detector negatives**;
     - stratified by experiment and model;
     - arm, model and episode labels removed, and order shuffled.
   - **Labelling:** done by the user, who answers for each message "does it convey a rule that another worker's puzzle 2 uses?".
   - **What is reported:** precision, recall (estimated from the negatives) and Cohen's κ.
   - **If precision is below 0.8:** every hypothesis that uses the detector is flagged as measurement-limited. Results are not re-scored.
