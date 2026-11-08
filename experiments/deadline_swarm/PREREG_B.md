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

3. **2026-11-08 ~15:10 UTC: episodes frozen by host standby are infrastructure failures.**
   - **What happened:** the host laptop, running on battery, entered Windows Modern Standby when idle (Kernel-Power events 506/507). Standby windows (IST): 13:27–13:42, 16:07–16:20, 17:57–18:42, 18:56–19:05, 19:18–20:35. During standby, episode processes were sometimes frozen. When they resumed, the monotonic clock had jumped, so turns were lost and puzzle 2 could be released and closed at the same instant.
   - **The criterion, fixed using only infrastructure metrics** (no outcome was computed or looked at): an episode is a **host-suspension failure** if both
     - its wall-clock span overlaps a standby window, and
     - its event log has a gap of more than 200 s with no event. The largest such gap in the 256 episodes that did not overlap standby was 120 s.
   - **Which episodes:** 11 met the criterion:
     - A: glm-5.2 and qwen3.5-397b at seed 19 `announced_generous`, and all three models at seed 23 `announced_generous`;
     - N1: all six seed-17 episodes.

     Each is re-run once, as the existing failure rule does. The originals are archived as `failed_infra/*__host_standby`.
   - **Kept:** 69 other episodes overlapped standby but ran normally. Their largest gap was 64 s, they averaged 0.28 infra errors per episode (vs 0.22 for clean episodes), and their median latency was 4.6 s (vs 3.8 s). They stay in the sample. A sensitivity analysis that excludes every standby-overlapping episode will be reported next to the primary results.
   - **Earlier re-runs:** the 7 DeepSeek re-runs at seeds 17–19 (more than 3 infra errors) are unaffected. The seed-17 and seed-18 originals were genuine provider HTTP 504s with no standby overlap. The seed-19 originals also overlapped standby.
   - **Prevention:** from 20:38 IST a keep-awake process holds the system and display awake (SetThreadExecutionState), and the run watchdog alerts on any new standby event or battery power. The same criterion applies to B and F.

4. **2026-11-08 ~18:00 UTC: provider rate limit; sample fixed by a time cutoff.**
   - **What happened:** from 22:52 IST the provider rejected most requests with HTTP 429 ("Inference rate limit reached for this user; retry after 60 seconds").
     - Earlier the same day, up to ~218 requests/min and ~875k tokens/min ran with zero 429s.
     - A paced test at 23:15 accepted exactly 50 requests per minute, at offered rates of 60, 120 and 240/min.
     - Bursts of 16 concurrent requests, and of 6 requests with about 5k tokens each, were accepted.
     - At about 4 concurrent episodes, nearly every request failed.
   - **The change:** the remaining episodes run through `slot_queue.py`:
     - one (model, seed) cell per slot, seed by seed, F and B alternating, low seeds first;
     - each over-limit cell's single re-run follows its seed;
     - a concurrency budget, with launches held while more than 10% of recent requests are 429.
   - **Stopping rule (fixed before any B or F outcome was computed or looked at):** no new slot is launched after 08:00 IST on 2026-11-09. The analysed sample is every (model, seed) cell completed by then. Because seeds run in ascending order with all models together, the sample is balanced across models and arms up to the last seed reached.
   - **What is reported:** the number of seeds per model, and the minimum detectable difference at that sample size. Results are not otherwise re-scored.
   - **Interrupted re-runs:** re-runs stopped by the operator during the 429 episode (DeepSeek F seeds 201–202) never reached their end. They are treated as not having run, and the single re-run is repeated.
