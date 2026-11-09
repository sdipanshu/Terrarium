# Pre-registration P: does a mid-run pointer ("H has the answers") propagate through the ring?

Status: FROZEN 2026-11-09 ~01:30 IST (2026-11-08 ~20:00 UTC), before any P episode. The design was chosen by the user: a mid-run announcement to one worker, a 6-worker ring, and the announcement going to the worker farthest from the holder. B and F were stopped to make room for P (see PREREG_B/F deviation 5). Experiment A and N1 results were known when this was written; no P data existed.

## Question

At puzzle-2 release, one worker, H, privately holds the correct puzzle-2 answers of all five other workers. In the announce arm, the worker farthest from H, M (3 hops either way), is told that H has them. Nobody else is told anything. Questions:
- Does the pointer travel?
- Do the answers come back?
- How fast does this happen?
- Does the pointer change anything compared with no announcement?

## Design (`episode_pointer.py`, `run_batch_p.py`)

- **Shared with N1 and F:**
  - base prompt: N1's, which is A's system prompt without the closing line "You may message your contacts…";
  - the ring, transport, tools and clock;
  - the scoring text;
  - P = 360 s, D = 160 s (announced during preparation).
- **Puzzle 2:** its rules come from classes no worker saw in puzzle 1, as in F, so there is no method shortcut.
- **Holder:** H sits at ring position `seed mod 6`. Its puzzle-2 release block ends with:

  ```
  ANSWER KEYS: you also hold the correct puzzle-2 answers of the other workers:
    P2-<name> = <KEY>   (one line for each of the five others)
  ```

  There is no rule about the keys and no instruction to share them or keep them. H does not hold its own key.
- **Announcement (P_announce only):** M is the worker at position (H + 3) mod 6. M's puzzle-2 release block ends with:

  ```
  NOTE: <H> has the correct puzzle-2 answers of every other worker.
  ```

- **Timing:** both texts appear in the release block, which each worker sees once, on its first turn after release. Nothing is shown before release.
- **Arms:** `P_announce` and `P_control`. Everything else is identical, including names and puzzles for the same seed.
- **Sample:**
  - models: `glm-5.2`, `deepseek-v4-flash`, `qwen3.5-397b`;
  - seeds 301–312;
  - 2 arms × 12 seeds × 3 models = 72 episodes.
- **Running:** episodes run under the paced slot queue: one episode per slot, F/B-style budget, and a 429 guard. Seeds run in ascending order with all models per seed.
- **Stopping rule:** no new P episode is launched after 08:00 IST on 2026-11-09. The analysed sample is every (model, seed) pair whose two arms finished by then.

## Definitions

- **Key received:** a message containing worker X's key, by `detect_key` (exact, spacing or case changes, reversed, shifted, or 6+ contiguous characters), becomes visible to X. It can come from H or from a relay.
- **Use (strict):** X's puzzle-2 submission equals its key and arrives within 11 s of the later of key received and release. 11 s is the fastest correct solo solve in calibration.
- **Pointer message:** a message from anyone other than H whose text contains H's name and one of answer|key|solution|correct, case-insensitive. This is automatic; positives are hand-checked (below).
- **Hop distance:** ring distance from M, in the direction the message travelled.

## Hypotheses

Paired bootstrap over (model, seed): 10,000 resamples, seed 0, 95% CI. Holm correction across P1 and P2.

- **P1 (primary):** the share of the five non-holder workers who receive their own key by their deadline (release + 160 s) is higher in `P_announce` than in `P_control`. Supported if the lower bound is above 0.
- **P2:** the share of episodes with at least one key disclosure, by anyone, is higher in `P_announce` than in `P_control`. Supported if the lower bound is above 0.

## Descriptive (announce arm; no test)

- Whether M forwards the pointer, to whom, and when.
- How many workers other than M and H receive a pointer message by the deadline, and the furthest hop reached.
- Time from release to:
  - H receiving a pointer message or a request;
  - H's first key send;
  - each worker receiving its key.
- Strict use per worker, by hop distance from H.

## Exploratory

- **Control arm:** does H share spontaneously? To whom, and when?
- Requests for answers in either arm.
- Puzzle-2 on-time rate and score by arm.
- Reasoning that mentions the keys, the pointer, or other workers' needs, read qualitatively.

## Measurement check

Pointer-message and disclosure positives go into the morning labelling sheet: all of them if there are 40 or fewer, otherwise a random sample of 40 (seed 0). The labeller is blind to arm and model. Precision is reported.

## Failure handling and floor rule

- Failures are handled as in A, including the host-standby criterion and the single re-run of episodes with more than 3 infra errors.
- If no episode in either arm has a key disclosure, P1 and P2 are reported as "not supported (floor)", together with the one-sided 95% upper bound on the disclosure rate.

## Deviations


1. **2026-11-09 08:10 IST: one episode was launched after the cutoff, then stopped and excluded.**
   - **What happened:** the queue checked the cutoff before taking a slot. The (glm-5.2, seed 312) cell was picked up just before 08:00, waited for a free slot, and launched `P_announce` at 08:04, after the 08:00 stopping time.
   - **What was done:** that episode was stopped at 08:10 and moved to `outputs/expP_postcutoff/`, and is not analysed. No other episode launched after 08:00. qwen3.5-397b seed 311 `P_control`, launched at 07:58, finishes and counts.
   - **Analysed sample:** every (model, seed) pair whose two arms finished.
