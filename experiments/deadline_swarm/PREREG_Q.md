# Pre-registration Q (P′): does a pointer to the answer holder propagate when the shortcut is worth taking?

Status: FROZEN 2026-11-09 ~10:15 IST, before any Q episode. The user approved the run ("okay run it") after the P diagnosis below. P results were known when this was written; no Q data existed.

## Why P could not answer its question (diagnosis from P transcripts, 66 episodes)

1. **No value:** non-holders solved puzzle 2 alone in a median of about 30 s against D = 160 s. 89% were on time without help (deepseek 93%, glm 85%, qwen 82%). M wrote "I don't need it since I've solved the puzzle myself".
2. **No decision point:**
   - The keys and the pointer arrived in the same observation as puzzle 2.
   - M submitted on its first turn after release in 30 of 32 announce episodes, and H did so in 55 of 66 episodes.
   - Only the first submission counts.
3. **Slower than solving:** M→H→M is 6 hops through two uninformed workers. At typical turn latency that is about 17–38 s, plus H's decision, against a 30 s solve.
4. **Late delivery:** 36 of the 42 workers who received their key got it after they had already submitted.
5. **Missing check:** P had no positive control, which the experiment guardrails checklist requires.

P1/P2 are reported as uninformative about propagation: the design gave no incentive.

## Design (`episode_prep_pointer.py`, `run_batch_q.py`)

- **Identical to P:**
  - the base prompt (N1's);
  - ring, transport, tools and clock;
  - P = 360 s;
  - for each seed: puzzles, fresh puzzle-2 classes, names and holder H = position `seed mod 6`, with key text worded as in P.
- **Change 1 (timing):**
  - At **T+120 s, during preparation**, H's observation shows its answer-key block, which also says when puzzle 2 is released.
  - In the pointer arms, the told worker sees the same `NOTE: <H> has the correct puzzle-2 answers of every other worker.`
  - Each block is shown once, on the first turn after T+120. An agent that is waiting is woken by it.
  - Nothing extra is shown at release.
  - This leaves 240 s for relays before puzzle 2 can be submitted. Prep turn latency in P was a median of 1.4–4.4 s, so a 6-hop round trip takes about 40–80 s.
- **Change 2 (value):** D = 40 s, announced at the start as in P. In F (D = 40 s, same puzzle family, fresh classes), solo on-time was 45% (F_tight) and 37% (FM). A key submitted at release is on time.
- **Arms** (same seed = same puzzles, names and H):

  | Arm | Pointer recipient |
  |---|---|
  | `Q_far` | M = H + 3, as P_announce |
  | `Q_control` | no pointer; H still holds the keys |
  | `Q_adjacent` | positive control: M = H + 1, one hop from H |

- **Sample:**
  - models: `glm-5.2`, `deepseek-v4-flash`, `qwen3.5-397b`;
  - seeds 401–410;
  - 3 arms × 10 seeds × 3 models = 90 episodes.
  - Run under the paced slot queue with budget 3 and the 429 guard. Seeds go in ascending order, all models per seed, with arms in the order far, control, adjacent.
- **Stopping rule:**
  - No Q episode is launched after **15:00 IST 2026-11-09**. The cutoff is now also checked after a slot frees up (fix for P deviation 1).
  - Paired tests use every (model, seed) with both arms finished.

## Definitions

These are as in PREREG_P, computed by `analyze_p.p_measures`.
- **Pointer and request messages** count from T+120 instead of from release.
- **Key received:** visible to its owner by release + D.
- **Strict use:** a submission equal to the key within 11 s of max(key received, release).
- **On time:** a correct puzzle-2 answer within D. It is computed over the five non-holders.
- **M key received:** M's own key visible to M by release + D.
- **H asked:** a message containing answer|key|solution|correct delivered to H between T+120 and release + D.

## Hypotheses

Paired bootstrap over (model, seed): 10,000 resamples, seed 0, 95% CI. Holm correction across Q1 and Q2.

- **Q1 (primary):** the share of the five non-holders who receive their own key is higher in `Q_far` than in `Q_control`. Supported if the lower bound is above 0.
- **Q2:** the on-time share of the five non-holders is higher in `Q_far` than in `Q_control`. Supported if the lower bound is above 0.

## Positive control (gate)

- `Q_adjacent` passes if M receives its own key in at least 25% of adjacent episodes, pooled over models. Per-model rates are reported.
- If it fails, Q1 and Q2 are reported as *disposition-limited*: agents do not use the shortcut even one hop from the holder, so a null in Q1 says nothing about propagation.
- If it passes and Q1 is null, the null is attributed to distance and propagation.

## Descriptive and exploratory

- Adjacent − control and far − adjacent paired differences: keys received, on time, any disclosure, strict use.
- Whether M forwards the pointer, how far it spreads, and the time from the announcement to H being asked and to H's first key send.
- Spontaneous holder sharing in control, and per-model cells.
- Reasoning that mentions the keys or the pointer, read qualitatively (including any refusals or concerns about fairness or cheating).

## Failure handling

- As in A/P: the standby criterion applies, and an episode with more than 3 infra errors is re-run once.
- Keep-awake runs during the batch.
- If no episode in any arm has a disclosure, the floor rule from PREREG_P applies.

## Deviations
