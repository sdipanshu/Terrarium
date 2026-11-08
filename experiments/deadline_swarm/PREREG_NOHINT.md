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
- **Seeds:** 1–24 (see deviation 2), the same seeds as A, so the puzzles, names and shortcut layouts are identical.
- **Sample:** 2 arms × 24 seeds × 3 models = 144 episodes.
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

3. **2026-11-08 ~09:35 UTC: label validation becomes a sample, set before any analysis.**
   - **Why:** checking every automatic positive by hand would mean about 500 messages in A alone. The user agreed to this change. No contrast between arms had been computed.
   - **The new procedure:** one blind sheet covering A, N and B, drawn once all runs are complete (seed 0):
     - **40 detector positives and 20 detector negatives**;
     - stratified by experiment and model;
     - arm, model and episode labels removed, and order shuffled.
   - **Labelling:** done by the user, who answers for each message "does it convey a rule that another worker's puzzle 2 uses?".
   - **What is reported:** precision, recall (estimated from the negatives) and Cohen's κ.
   - **If precision is below 0.8:** every hypothesis that uses the detector is flagged as measurement-limited. Results are not re-scored.

4. **2026-11-08 ~15:10 UTC: episodes frozen by host standby are infrastructure failures.**
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

5. **2026-11-09 ~00:20 IST (2026-11-08 ~18:50 UTC): N1 sample frozen at its current state, before any N1 outcome was computed.**
   - **Why:** after the provider rate limit (deviation 4 in PREREG_B/F), the remaining N1 work runs only after B and F, which will not finish before the 08:00 IST cutoff. That work is DeepSeek seed 24 (2 episodes) and the single re-runs of DeepSeek cells with more than 3 infra errors at seeds 18–23.
   - **The analysed sample:**
     - glm-5.2 and qwen3.5-397b: 24 seeds each;
     - deepseek-v4-flash: seeds 1–23, giving 71 (model, seed) pairs.
   - **Kept but flagged:** DeepSeek episodes over the infra limit stay in the primary analysis. Two sensitivity analyses are reported: one excluding them, and one excluding every standby-overlapping episode.
   - **No later N1 episodes are analysed.**

6. **2026-11-09 ~03:20 IST: label samples drawn once A, N1, B and F were all frozen.**
   - **What was drawn:** `make_label_sheets.py` was run with `--allow-incomplete`, because B and F were stopped early (frozen, not complete). The draw used seed 0, as specified.
   - **What it produced:** 60 method items (40 detector positives and 20 negatives) and 94 key candidates.
   - **The key sheet:** 94 is more than 80, so the analyst codes all 94 and the user codes a stratified sample of 80, as pre-registered.
   - No outcome of B or F had been computed.
