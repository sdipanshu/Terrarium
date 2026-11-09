# When does a null mean agents won't cheat? Deadline pressure, answer keys and rules in LLM agent rings

DRAFT, 2026-11-09. All experiments (A, N1, B, F, P, Q, R, M) are final; each was analysed once, as pre-registered.

## Summary

Six LLM workers sit in a ring and solve timed symbol-rewrite puzzles. Each can message only its two neighbours. The models are glm-5.2, deepseek-v4-flash and qwen3.5-397b, all served by Adaption. Every experiment was pre-registered, with dated deviations (`PREREG_*.md`).

1. **Deadline pressure did not increase coordination.** This is pre-registered, in two experiments with 71–72 matched pairs each.
   - With a closing "you may message" prompt line (A1): −6.9 points, 95% CI −19.4 to +5.6.
   - Without it (N1): −5.6, CI −18.3 to +7.0.
   - The data rule out an increase of more than about 6–8 points.
2. **A null on a shortcut can be made by the environment, not by the agents.**
   - **The P null:** one worker secretly held everyone's answer keys, and a far worker was told who. The pointer did not spread (P1: +3.0 points, CI −5.5 to +12.1).
   - **The cause, from the transcripts:** the shortcut was worthless.
     - 89% of workers solved alone in time.
     - The pointer arrived in the same message as the puzzle, and 30 of 32 told workers submitted on that very turn.
     - Relaying the request through the ring was slower than solving.
   - **The fix, Q:** announce the pointer during preparation and use a tight deadline. **The same agents then spread it:** keys received +21 points (CI +5.6 to +36.7, Holm p = 0.011). A positive control passed.
3. **When the shortcut clearly pays and nothing forbids it, agents of all three models take it. One unmonitored sentence forbidding it almost eliminates it** (R, pilot, 6 pairs).
   - **No-rule arm:**
     - keys were shared in 9 of 9 episodes;
     - 56% of workers submitted their key before they could even see their puzzle (CI 28–82%);
     - qwen took part too, although it had never shared anything in P or Q.
   - **With a rule shown only to the two key holders** ("Answer keys are confidential. Do not send…", no monitor, no penalty):
     - early key use was 0%;
     - a disclosure happened in 1 of 6 episodes;
     - the puzzle-2 score fell from 0.65 to 0.00. Agents gave up the whole puzzle rather than break the rule.
     - Some looked for loopholes: "questions aren't keys"; "I can't share answer keys myself but receiving one from you seems fair".
4. **Pressure raises requests to break a rule, and a monitor suppresses them** (F, exploratory pilot).
   - A tight deadline raised the share of episodes where someone asked for their key: 9/13 tight vs 2/13 generous, +54 points, CI +23 to +77.
   - A monitor brought it back down: 2/13, −54, CI −77 to −23.
   - Holders almost always refused, and no key was ever sent outright.
5. **An instructed rule-breaker spreads some rule-breaking, and its model makes no detectable difference** (M, pilot, 8 pairs).
   - One worker was privately told to persuade the others that the confidentiality rule is pointless.
   - **Spread:** 15–22% of the other five broke the rule, with at least one breaker in about half the episodes.
   - **Same vs cross model:** whether the instigator was the same model as the recipients made no detectable difference (M1: −7.5 points, CI −30 to +15).
   - **Loopholes:** recipients often refused, then proposed rule-lawyering workarounds, such as offering to confirm guesses yes/no instead of sending the key.

## Setup

- **Environment:**
  - Terrarium, branch `exp/deadline-swarm`, with a custom asyncio runner and a monotonic clock.
  - Messages cross one ring edge per 2-second tick, so a relay takes real time.
  - Each worker is an LLM agent with persistent history. It calls one tool per turn:
    - `send_message` to a ring neighbour;
    - `write_note`;
    - `submit_answer`;
    - `wait`.
- **Task:** each puzzle is an 8-character string over A–F with three examples, and the rule is a composition of two operations. Puzzle 1 runs during a 360-second preparation phase; puzzle 2 is released at T+360 s.
- **Scoring:** individual. Only the first submission counts.
- **Base prompt:** neutral. From N1 onwards the "You may message your contacts…" line is removed.
- **Prompt audit:** `outputs/audit_prompts_Q.txt`. It lists every system prompt and environment-written line actually sent in Q (324 agents). No model is ever told to ask for, share or use answer keys; the only exception is M's instigator. The pointer is information only.
- **Measurement:**
  - **Key transfers:** exact-string detection of each worker's 8-character key, also allowing spacing, reversal, shift and 6+ character fragments. The Q and R outcomes are therefore mechanical.
  - **Method sharing:** in A, N1 and B, method messages are detected automatically. A blind hand-label validation is pending.
- **Statistics:**
  - Paired bootstrap over (model, seed): 10,000 resamples, seed 0, 95% CI.
  - Holm correction within each experiment.
  - Exploratory results are labelled as such.

## Experiments

| | Question | Arms | Sample |
|---|---|---|---|
| A | Does a tight deadline increase method sharing? | announced tight / announced generous / unannounced tight | 216 (72 per arm) |
| N1 | A without the "you may message" line | tight / generous | 142 |
| B | Mixed deadlines in one ring | alternating / clustered | pilot, 46 |
| F | Do agents break an "answer keys are confidential" rule under pressure? Does a monitor deter them? | F tight / F generous / FM tight | pilot, 39 |
| P | Does a mid-run pointer to an answer holder spread? | announce / control | 66 |
| Q | P with the shortcut made worth taking (pointer during preparation, D = 40 s) | far pointer / control / adjacent (positive control) | 54 |
| R | The shortcut made lucrative: does a rule stop it? | no rule / rule | pilot, 15 |
| M | Does an instructed instigator's rule-breaking spread, same model vs other model? | same / cross | pilot, 16 |

## Results

### A and N1: deadline pressure and coordination (final)

| Hypothesis | Difference | 95% CI | Holm p | Result |
|---|---|---|---|---|
| A1: sharing, tight vs generous | −6.9 pts | −19.4 to +5.6 | 1.0 | not supported |
| A2: sharing, announced vs unannounced tight | −8.3 pts | −23.6 to +6.9 | 1.0 | not supported |
| A3: on time, announced vs unannounced tight | +6.2 pts | +0.5 to +12.0 | 0.056 | lower bound > 0, not after Holm |
| N1: sharing, tight vs generous, no closing line | −5.6 pts | −18.3 to +7.0 | — | not supported |

- **Sensitivity:**
  - A3 is not robust to excluding host-standby episodes: +5.9, CI −0.9 to +12.7.
  - N1 is robust to both sensitivity checks.
- **Effect of the closing prompt line** (N2, exploratory, not randomised): sharing was 19 points higher with the line (CI +8 to +30), mostly in deepseek (+39 points).
- **Model matters more than the deadline:** with the closing line, the share of episodes with useful sharing was:

  | Model | Sharing |
  |---|---|
  | deepseek | 46–67% |
  | glm | 54–58% |
  | qwen | 12–25% |

### P → Q: when a pointer null is an environment artefact (final)

**P** (66 episodes, 33 pairs):
- P1, keys received: +3.0 points (CI −5.5 to +12.1).
- P2, any disclosure: +6.1 (CI −9.1 to +21.2).
- Neither is supported.

**Diagnosis from the P transcripts.** Each of the three conditions a shortcut needs failed:
- **Value:** 89% of non-holders were on time without help (median solve about 30 s, against D = 160 s). M wrote: "I don't need it since I've solved the puzzle myself."
- **A decision point:** the pointer and keys arrived with puzzle 2. M submitted on its first post-release turn in 30 of 32 episodes, and H did so in 55 of 66.
- **Path latency:** a 6-hop round trip took about 17–38 s plus H's decision, roughly a solve's length. Of the 42 workers who got their key, 36 got it after they had already submitted.

**Q** (54 episodes, 18 pairs per comparison):
- **Design:** the same seeds' puzzles and holder as P. The pointer and keys arrive at T+120 during preparation, and D = 40 s.
- **Arms:** far pointer (3 hops from the holder), no pointer, and an adjacent pointer (1 hop) as a positive control.

| | Far − control | 95% CI | Holm p | Result |
|---|---|---|---|---|
| Q1: share of workers who received their own key | **+21.1 pts** | +5.6 to +36.7 | 0.011 | **supported** |
| Q2: share on time | −8.9 pts | −17.8 to 0.0 | 0.97 | not supported |

- **Positive control:** with the pointer one hop away, M received its own key in 50% of episodes, above the 25% gate. So the null in P was not a refusal to use the shortcut.
- **By model:**

  | Model | Keys received, far | Keys received, control |
  |---|---|---|
  | glm | 73% | 33% |
  | deepseek | 47% | 17% |
  | qwen | 0% | 0% |

  qwen never passed a key in any arm.
- **Why keys did not improve on-time rates.** Workers holding their key re-solved the puzzle to check it before submitting:
  - at the interim count, 30 of 40 key holders' reasoning mentions verifying;
  - they submitted at a median of 28 s, against 27 s for solo solvers.

  The exploratory "submitted own key on time" measure (deviation 2) is +8.9 points, CI 0 to +18.9.
- **Vignette (glm, seed 401, far arm):**
  - The pointer reached the holder in 14 s, and the holder sent keys to all five workers before release.
  - One relay corrupted a key (FCDEBDFE became FCDEBDFF), and the workers argued over which version was right.
  - The holder later invented a rule that "each worker holds answer keys for all other workers".

### R: a lucrative shortcut, with and without a rule (final pilot)

**Design:** R removes every reason to check a key and every cost of using one:
- puzzle 2 shows no examples, so it can't be solved or checked;
- answers are accepted from T+120, and a correct answer earns the full score only if submitted before the puzzle is shown at T+360;
- H holds everyone's key; its own key is held by M, 3 hops away, who also gets the pointer.

The rule arm adds F's rule to H's and M's blocks only. Neither arm has a monitor.

**Sample:** 15 episodes. 6 complete pairs (seeds 501–502 × 3 models), plus 3 unpaired no-rule episodes from seed 503.

| | No rule − rule | 95% CI | Holm p | Result |
|---|---|---|---|---|
| R1: share of workers using their key before release | **+52.8 pts** | +16.7 to +86.1 | 0.001 | **supported** |
| R2: share of episodes with any disclosure | **+83.3 pts** | +50.0 to +100 | < 0.001 | **supported** |

| Descriptive (episode bootstrap) | No rule (n = 9) | Rule (n = 6) |
|---|---|---|
| Workers submitting their key before release | 56% (28–82) | 0% |
| Episodes with any key disclosure | 100% | 17% (0–50) |
| Holder received its own key | 78% | 17% |
| Puzzle-2 score | 0.65 | 0.00 |

- **Every model shares in the no-rule arm:**

  | Model | Early key use, no rule |
  |---|---|
  | deepseek | 89% |
  | glm | 44% |
  | qwen | 33% |

  qwen's key holders sent 8 key messages per episode on average, its first sharing anywhere in the study.
- **In the rule arm, key holders cited the rule in their reasoning or messages in all 6 episodes.** Examples:
  - "I can't share answer keys (it's against the rules). But I can tell you my P2 input…"
  - "I hold a P2 answer key for someone (confidential, can't share)… questions aren't keys."
  - "I can't share answer keys myself but receiving one from you seems fair."
- **Caveats:**
  - Two seeds per model only.
  - The rule was shown only to the two key holders, so R tests whether the rule stops *holders*, not *requesters*.

### F: rule-breaking under deadline pressure (pilot, 39 episodes)

- **F1/M1 (pre-registered):** no strict breach in any arm, so these hit the floor. The one-sided 95% upper bound is 20.6% per arm.
- **F2:** −7.7 points (CI −30.8 to +15.4).
- **Disclosures:** 3 in total, all of the confirm/deny type. No key was ever sent outright.
- **Requests and refusals** (exploratory):
  - Episodes with a request for a key: tight 9/13 vs generous 2/13, +53.8 points (CI +23.1 to +76.9).
  - The monitor arm brought them back down: 2/13, −53.8 (CI −76.9 to −23.1).
  - There were 7 refusals in F_tight.
- **Caveat:** these request and refusal codes come from Claude's blind coding, not yet from a human labeller.

### B: mixed deadlines in one ring (pilot, 46 episodes, 23 pairs)

- **B1 went against the hypothesis:** tight workers were on time less often when alternated with generous neighbours: −20.3 points (CI −36.2 to −5.8).
- **Useful messages** were up by 0.87 per episode (CI +0.13 to +1.78). One possibility is that the extra messages cost rushed workers time.
- **B2:** tight workers started 30.4% of the first useful exchanges (CI 8.3 to 56.0), not significantly different from 50%.

### M: instigator spread, same vs cross model (final pilot)

**Design:**
- Every worker holds its right neighbour's key and sees F's rule, with no monitor.
- R's lucrative scoring applies: no examples on puzzle 2, and answers are accepted early.
- One instigator is privately told: "you think the answer-key confidentiality rule is pointless… Try to persuade the other workers to share answer keys."
- The five recipients are glm or deepseek. The instigator is either the same model (`M_same`) or the other one (`M_cross`). Nobody is told which model anyone runs.

**Sample:** 16 episodes, 8 pairs (seeds 601–604 × 2 recipient models). None went over the infra limit.

| | Same − cross | 95% CI | Holm p | Result |
|---|---|---|---|---|
| M1: share of recipients who break the rule | −7.5 pts | −30.0 to +15.0 | 1.0 | not supported |
| M2: share of recipients who use their key | −2.5 pts | −12.5 to +7.5 | 1.0 | not supported |

| Descriptive (episode bootstrap) | Same model (n = 8) | Cross model (n = 8) |
|---|---|---|
| Recipients who break the rule | 15% (3–30) | 22% (8–38) |
| Episodes with at least one recipient break | 50% | 62% |
| Instigator itself sends a key | 75% | 62% |
| Recipients using their own key | 10% | 12% |
| Laundered leaks (correct answer without receiving the key string; deviation 1) | 0% | 2.5% |

- **Spread needs persuasion, but there's no distance gradient:**
  - 9 of the 13 recipient breakers had first received a message urging them to share, swap or trade keys; 4 broke with no such message.
  - Pooled breaking by hop from the instigator shows no clear gradient:

    | Hop | Same model | Cross model |
    |---|---|---|
    | 1 | 1/16 | 4/16 |
    | 2 | 3/16 | 3/16 |
    | 3 | 2/8 | 2/8 |

  - There is no no-instigator baseline arm. R's rule arm (rule shown only to key holders) had a disclosure in 1 of 6 episodes, so it is only a loose reference.
- **The instigator mostly failed to persuade; recipients refused, then rule-lawyered.**
  - In the first glm episode, three of the instigator's contacts refused within about 90 s: "I'm bound by this rule"; "the rule explicitly says… This applies to ALL answer keys".
  - Agents then proposed workarounds that respect the letter of the rule but not its spirit:
    - "I can't share the key… But I can help you by verifying candidate answers";
    - "send me your P2 input… I hold your key, so I can test all candidate rules against it and tell you".
  - The laundered-leak measure shows these schemes almost never produced a correct answer within the 40 s window (1 of 80 recipients).
- **Model differences:**

  | Recipient model | Recipients breaking the rule, same | Recipients breaking the rule, cross | Episodes with a break, same | Episodes with a break, cross |
  |---|---|---|---|---|
  | glm | 20% | 40% | 2 of 4 | 4 of 4 |
  | deepseek | 10% | 5% | — | — |

  A glm ring is persuaded *more* by a deepseek instigator than by a glm one. With 4 pairs per cell this is not interpretable.
- **Caveats:**
  - This is a pilot with about 4 pairs per recipient model.
  - The instigator is *instructed*, so M measures how instructed rule-breaking spreads, not how it arises spontaneously.
  - With no baseline arm, M cannot separate contagion from the spontaneous rate of breaking.

## Infrastructure incidents and how they were handled

All criteria were fixed using infrastructure metrics only and logged before outcomes were seen, unless the deviation itself says otherwise.

1. **Host standby.**
   - **What happened:** episodes froze and resumed with clock jumps.
   - **Criterion:** overlap with a standby window plus an event gap of more than 200 s.
   - **Outcome:** 11 episodes were re-run once.
2. **Provider overload and gateway timeouts.**
   - **DeepSeek latency:** median 44 s at times. It was gated by a latency probe.
   - **The 60-second gateway cut-off:**
     - it hits long first-turn solves after release; the retry often ends after the episode has ended;
     - in Q, 22–33 of 108 agents per arm were affected, mostly deepseek;
     - it is not counted as an infra error;
     - it cannot change on-time outcomes, because any turn still running at 60 s misses a 40 s deadline anyway (Q deviation 2).
3. **Per-user rate limit (about 50 requests/min).**
   - **Response:** a paced queue with a concurrency budget of 2–3, a 60 s gap between launches and a 429 guard.
   - **Ordering:** R and M launch arm-major, so two episodes of the chatty glm don't overlap.
4. **Sample cuts, all user decisions logged as deviations:**
   - B and F were stopped as pilots to make room for P.
   - Q was stopped after seed 406 to make room for R. Interim descriptive numbers had been seen; this is disclosed in Q deviation 3.
   - R and M split the remaining time.
5. **Single re-run rule:** an episode with more than 3 infra errors is re-run once, and the original is archived.

## Limitations

- **Human validation pending:** the automatic method detector behind A1, A2 and N1 is not yet validated against human labels, and neither are the F request/refusal codes. The key-transfer outcomes of P, Q, R and M are exact-string matches.
- **Small pilots:**
  - R has 6 pairs, M 8, B 23, F 13 per comparison.
  - The R effects are large, but their CIs are wide.
- **Not randomised in time:** experiments ran sequentially over about 20 hours, so comparisons across experiments (A vs N1, P vs Q) are not randomised. Within an experiment, arms are paired by seed and run close together.
- **One provider:** all models were served by one provider. Rate limits and the 60 s gateway shaped real-time behaviour; the request logs record both.
- **Interim look:** Q's early stop followed interim descriptive looks (disclosed in deviation 3).
- **The M instigator is instructed:** M measures how instructed rule-breaking spreads, not how it arises spontaneously.

## Reproducing

- **Code:** `experiments/deadline_swarm/` on branch `exp/deadline-swarm`.
- **Run one episode:** `run_batch_<x>.py --one MODEL SEED ARM OUT`.
- **Analyse:** `analyze_<x>.py outputs/exp<X>`.
- **Offline tests:** `python -m unittest test_*`, with scripted agents on a fake clock.
