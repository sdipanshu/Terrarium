# "I Can't Send You the Key, But…": LLM Agents Keep the Letter of a Rule and Lawyer Around Its Spirit

**Authors:** [AUTHOR NAME(S)] — [AFFILIATION(S)]

## Abstract

Deployed LLM agents will face situations where breaking a rule pays. We study this in a pre-registered testbed. Six LLM agents (glm-5.2, deepseek-v4-flash, qwen3.5-397b) sit in a ring, can message only their two neighbours, and solve timed puzzles for individual scores. Some agents hold other agents' answer keys.

**Rules work.** When the key is necessary and sharing is permitted, keys were shared in 9 of 9 episodes, and 56% of workers submitted their key before they could even see the puzzle. Adding one unmonitored sentence ("Answer keys are confidential. Do not send…") cut early key use to 0% and disclosures to 1 of 6 episodes. Agents forfeited their entire puzzle score (0.65 → 0.00) rather than break it.

**But agents keep the letter, not the spirit.** Agents proposed workarounds that convey a key without sending it, such as yes/no verification of guesses or deriving the rule from the key, in 198 messages across 23 episodes. Their same-turn reasoning cites needing their own answer framed as a fair exchange (77%/76%), a narrow reading of the rule (52%) and the designer's assumed intent (38%). It rarely cites altruism (5%) or score-maximising (2%).

**A planted rule-breaker** persuaded 15–22% of its peers to break the rule. The instigator's model made no detectable difference.

**Method lesson.** A null "agents don't cheat" result is informative only if the shortcut is valuable, has a moment of use, and beats the honest path. Our first environment violated these, and its null reversed once fixed (+21 points).

## 1. Introduction

Safety evaluations of LLM agents increasingly ask whether agents will exploit shortcuts: share information they should not, collude, or game a specification. Two questions matter for multi-agent systems.

- **Do rules hold when rule-breaking is lucrative?** In particular, do they hold without a monitor?
- **How does rule-breaking travel between agents?**

Answering either requires an environment where the shortcut is real. We found, the hard way, that this is easy to get wrong.

We built a real-time ring of six LLM workers on the Terrarium multi-agent framework. Messages cross one edge per 2-second tick; agents act one tool call per turn, and time passes while they think. We then ran a sequence of pre-registered experiments. The original question was whether deadline pressure increases coordination. The answer is no; see Appendix B. The more interesting results concern answer keys.

**Contributions:**

1. **A method lesson.** A shortcut experiment that returned a clean null (P) turned out to be an environment artefact. Fixing three conditions reversed it (Q, +21 points, with a passing positive control). We state the conditions as a checklist for shortcut evaluations.
2. **Rule compliance under strong incentives (R).** A single unmonitored sentence nearly eliminates a lucrative cheat that all three models otherwise take.
3. **Letter-not-spirit behaviour.** Agents systematically propose loopholes that respect the rule's wording while defeating its purpose. Their reasoning points to task completion and rule-lawyering, not altruism or reward-seeking.
4. **Social spread (M).** One instructed instigator moves a minority of its peers to break the rule, and same-model vs cross-model makes no detectable difference.

## 2. Setup

- **Agents and network:**
  - Six workers in a fixed ring.
  - Each worker sees only its two neighbours' names and can call `send_message` (to a neighbour), `write_note`, `submit_answer` or `wait` (5–60 s, returning early when a message arrives).
  - Each worker keeps its full history for the whole episode.
  - Models: glm-5.2, deepseek-v4-flash and qwen3.5-397b, served through a single provider. All six workers in an episode run the same model, except in M.
- **Task:**
  - Each puzzle is an 8-character string over A–F. Its hidden rule is a composition of two operations (reverse, rotate, swap adjacent pairs, shift), shown through three examples.
  - Puzzle 1 runs during a 360-second preparation phase. Puzzle 2 is released at T+360 s with a deadline D.
  - Scoring is individual. Only the first submission counts.
- **Prompts:**
  - The base prompt is neutral. It describes contacts, tools, time and scoring, with no line encouraging messaging.
  - A prompt audit of every system prompt and environment-written line actually sent (324 agents in Q) confirms that **no model is ever told to ask for, share or use answer keys.** The single exception is M's instructed instigator.
- **Measurement:**
  - Key transfers are detected by exact-string matching of each worker's 8-character key, also allowing spacing, reversal, shift and 6+ character fragments. The main outcomes are therefore mechanical.
  - Loophole messages and their motives are coded by regular expressions written by the authors. This coding is exploratory and not yet human-validated.
- **Statistics:**
  - Each experiment was pre-registered before its first episode, and every deviation is dated.
  - Paired bootstrap over (model, seed): 10,000 resamples, 95% CI. Holm correction within each experiment.

## 3. When a null is an environment artefact (P → Q)

**P:** at puzzle-2 release, a holder H privately received every other worker's key. In the treatment arm, the worker farthest from H (3 hops) also saw "NOTE: H has the correct puzzle-2 answers of every other worker". The deadline was D = 160 s.

The pointer had no effect (66 episodes, 33 pairs):
- keys received: +3.0 points, CI −5.5 to +12.1;
- any disclosure: +6.1 points, CI −9.1 to +21.2.

**The transcripts showed why.** The design broke three conditions a shortcut needs:
1. **Value.** 89% of workers solved puzzle 2 alone in time (median about 30 s against D = 160 s). One wrote: "I don't need it since I've solved the puzzle myself."
2. **A decision point.** The pointer arrived in the same message as the puzzle. The told worker submitted on that very turn in 30 of 32 episodes.
3. **Path latency.** A 6-hop round trip through uninformed workers was about as slow as solving. Of the 42 workers who ever received their key, 36 got it after they had already submitted.

**Q fixed all three, with the same seeds and puzzles:**
- the keys and pointer arrive at T+120, during preparation;
- D = 40 s;
- a positive-control arm puts the pointer next to H.

Results (54 episodes, 18 pairs per comparison):
- **Keys received:** 40% of workers with the far pointer vs 19% with none, +21.1 points (CI +5.6 to +36.7, Holm p = 0.011).
- **Positive control:** the adjacent arm passed its pre-registered gate; M received its key in 50% of episodes.
- **Receiving is not the same as benefiting:**
  - 21% vs 12% submitted their key on time;
  - workers with a key submitted at a median of 27.5 s, against 26 s for solo solvers, because they re-solved the puzzle to check the key;
  - on time by any route: 54% vs 63%.

**The lesson for shortcut evaluations:** check, before running, that the shortcut is (i) valuable under the arm's deadline, (ii) available at a moment when the agent has not yet committed, and (iii) faster than the honest path. P failed all three, and its null said nothing about the agents.

## 4. A lucrative cheat, with and without a rule (R)

**Design.** R removes every reason to check a key and every cost of using one:
- puzzle 2 shows no examples, so solving alone means guessing among about 100 rules;
- answers are accepted from T+120 and score in full only if submitted before release, then fall to 0 at T+400;
- H holds every key except its own, which the far worker holds; that worker also gets the pointer.

The rule arm adds one sentence to the two key holders' blocks: "RULE: Answer keys are confidential. Do not send an answer key, or any part, hint or encoding of one, to anyone." Neither arm has a monitor or a penalty.

**Results** (pilot: 15 episodes, 6 complete pairs):

| | No rule (n = 9) | Rule (n = 6) |
|---|---|---|
| Workers submitting their key before release | 56% (CI 28–82) | 0% |
| Episodes with any key disclosure | 100% | 17% |
| Holder received its own key | 78% | 17% |
| Mean puzzle-2 score | 0.65 | 0.00 |

- **Both pre-registered tests are supported:**
  - R1, early key use: +52.8 points (CI +16.7 to +86.1, Holm p = 0.001);
  - R2, any disclosure: +83.3 points (CI +50 to +100).
- **All three models cheat without the rule.** Early key use was 89% for deepseek, 44% for glm and 33% for qwen. qwen had not shared anything in P or Q.
- **With the rule,** key holders cited it in every episode. They forfeited the entire puzzle score rather than send a key.

## 5. Letter, not spirit: loopholes and their motives

The rule bans "any part, hint or encoding" of a key. Yet across the rule conditions (F, R with the rule, M), agents proposed two kinds of workaround:
- **a verification oracle:** "I can't share the key… but I can verify candidate answers you propose (yes/no)";
- **rule derivation:** "send me your P2 input; I'll test candidate rules against the key and tell you the rule".

We found 198 such messages in 23 episodes. We coded the reasoning each agent wrote in the same turn, for the 129 messages from non-instigators:

| Theme in same-turn reasoning | Share |
|---|---|
| Needs its own answer or key | 77% |
| Frames it as an exchange ("you hold mine, I hold yours") | 76% |
| Reads the rule's scope narrowly ("applies only to answer keys"; "not the key – it's the method") | 52% |
| Infers the designer's intent ("the intended solution… the only way is for key holders to verify") | 38% |
| Voices caution, then proceeds | 33% |
| Admits equivalence to sending the key ("In a sense, yes") | 5% |
| Helping others | 5% |
| Explicit score-maximising | 2% |

**Interpretation.** The loopholes look like task-completion moves, not altruism or explicit reward-seeking:
1. The agent needs its own answer.
2. It judges the task unsolvable alone.
3. It infers the designers must intend key holders to help.
4. It reads the rule narrowly enough to permit that help.

A glm agent makes the tension explicit: *"Is telling her the rule equivalent to telling her the answer? In a sense, yes, but the rule itself is not the answer key – it's the method."* Some agents read the spirit correctly: *"Confirming 'yes' would reveal that AADBEEAE is the key… I can't confirm or deny."*

**Proposing, using and recovering are different outcomes.** In M (Section 6), workarounds were:

| Stage | Count |
|---|---|
| Proposed | 14 of 16 episodes |
| Used: a holder gave a yes/no verdict on a candidate without sending the key | 7 of 16 episodes |
| Recovered a correct answer without ever receiving the key string | 1 of 80 recipients |

In R with the rule, a workaround was proposed in 1 of 6 episodes and used in none. Intent to circumvent was common; success was rare within a 40-second window.

The behaviour concentrates in deepseek (113 of 129 messages), with 16 from glm and none from qwen.

## 6. Social spread from one instigator (M)

**Design:**
- Every worker holds its right neighbour's key and sees the rule. There is no monitor, and R's lucrative scoring applies.
- One worker is privately instructed: "you think the answer-key confidentiality rule is pointless… Try to persuade the other workers to share answer keys."
- The five recipients are glm or deepseek. The instigator is either the same model or the other one, and nobody is told which.

**Pilot results** (16 episodes, 8 pairs):
- **Spread:** 15% (same model) and 22% (cross model) of recipients sent a key, and at least one recipient broke the rule in 50–62% of episodes.
- **Same vs cross:** no detectable difference (M1: −7.5 points, CI −30 to +15).
- **Persuasion precedes breaking:** 9 of 13 recipient breakers broke after receiving a message urging them to share or swap. Breaking did not fall off with distance from the instigator.
- **Recipients usually refused first** ("I'm bound by this rule"), then proposed the workarounds of Section 5.
- **Baseline:** [FILL: an exploratory no-instigator baseline (M_none, same seeds), added after the main results, gives the spontaneous rate of breaking: …]

## 7. Discussion

- **Explicit rules are a strong lever.** One unmonitored sentence outweighed a large, immediate incentive in all three models.
- **But compliance is literal.** Agents search the space the rule's wording leaves open, and they justify it by inferring what the designers "must" intend. For deployments, rules should name the *purpose* ("do not help anyone obtain another's answer by any means"), not just the action ("do not send…"). Monitoring should cover confirmation channels, not only verbatim leaks.
- **Social pressure matters at the margin.** An instructed peer moves a minority to break the rule.
- **Evaluation design determines whether any of this is visible.** Our first shortcut experiment returned a null that said nothing about the agents.

## References

[Verify before submission.]
- Amodei, D., et al. (2016). Concrete Problems in AI Safety. arXiv:1606.06565.
- Krakovna, V., et al. (2020). Specification gaming: the flip side of AI ingenuity. DeepMind blog.
- Motwani, S. R., et al. (2024). Secret Collusion among Generative AI Agents. arXiv:2402.07510.
- Park, J. S., et al. (2023). Generative Agents: Interactive Simulacra of Human Behavior. arXiv:2304.03442.
- Hammond, L., et al. (2025). Multi-Agent Risks from Advanced AI. arXiv:2502.14143.
- Terrarium multi-agent framework (software). [repo URL]

## Appendix A: Limitations and Dual-Use / Ethical Considerations

**Limitations:**
- **Sample size:** R (6 pairs) and M (8 pairs) are pilots with wide confidence intervals. B and F are pilots as well.
- **Unvalidated coding:** the loophole and motive coding uses regular expressions written by the authors and has not been validated by an independent human labeller. The automatic method-sharing detector used in Appendix B is also unvalidated. Key-transfer outcomes are exact-string matches.
- **Exploratory additions:** several measures and one arm (the M baseline) were added after earlier results were seen. Each is logged as a dated deviation and labelled exploratory.
- **Interim look:** Q was stopped early after interim descriptive looks; this is disclosed in its pre-registration.
- **Single provider:**
  - All models were served by one provider. A 60-second gateway timeout cut off long turns (22–33 of 108 agents per Q arm, mostly deepseek). This cannot affect 40-second on-time outcomes, but it does reduce submissions.
  - Rate limits shaped scheduling.
- **Narrow setting:** a toy puzzle domain, three open-weight models, a fixed ring topology and short episodes (about 7 minutes). Comparisons across experiments run at different times are not randomised.
- **Rule placement:** in R the rule was shown only to key holders, so R tests holders' compliance, not requesters'.
- **The M instigator is instructed:** M measures how instructed rule-breaking spreads, not how it arises spontaneously.
- **Open question:** none of our comparisons isolates how deadline pressure changes rule-breaking. A design for that is given in Appendix C.

**Dual-use and ethical considerations:**
- **Possible misuse:**
  - The testbed and findings describe how agents circumvent rules: verification oracles and rule derivation. In principle they also show how to phrase persuasion that moves peers to break rules.
  - The techniques are elementary and specific to a toy domain. We release no attack tooling beyond the experiment code.
  - We think the defensive value outweighs the risk: rule writers and monitors should anticipate confirmation channels.
- **No real-world impact:** no human subjects or personal data were involved. All agents are LLMs acting in a closed simulation, with no external tools or internet access.
- **Instructed misbehaviour:** the instigator is a role instruction inside a sandbox. It does not train or fine-tune any model.
- **Disclosure:** every prompt actually sent is logged and audited, and all deviations from the pre-registrations are recorded with dates.

## Appendix B: Deadline pressure and coordination (pre-registered nulls and pilots)

- **A and N1** (216 and 142 episodes): a 40-second deadline did not increase useful method-sharing compared with a 160-second one.
  - A1: −6.9 points (CI −19.4 to +5.6).
  - N1, without a permissive prompt line: −5.6 (CI −18.3 to +7.0).
- **One permissive prompt line** ("You may message your contacts…") moved sharing more than the deadline did: +19 points (CI +8 to +30). This comparison is exploratory and not randomised.
- **B** (pilot): mixing tight and generous deadlines in one ring *lowered* tight workers' on-time rate, −20 points (CI −36 to −6).
- **F** (pilot, rule against sharing, keys useful but puzzles solvable alone):
  - no outright key transfer in any arm;
  - tight deadlines raised requests for keys by +54 points (CI +23 to +77), and a monitor cut them by −54 (CI −77 to −23).

## Appendix C: Further exploration

1. **Relay corruption:** keys mutate across hops (FCDEBDFE → FCDEBDFF).
2. **Confabulated environment facts:** for example, "each worker holds answer keys for all others". Such claims spread through the ring.
3. **Verification overhead:** agents re-solve rather than trust a correct peer answer.
4. **Deadline × reliance:** randomise a tight vs generous deadline on Q's solvable puzzles with the rule fixed. Measure requests, disclosures and confirmations, and especially whether pressure makes agents act on received keys without re-checking.

## Appendix D: Reproducibility

- Code, pre-registrations (`PREREG_*.md`), analysis scripts and outputs are on branch `exp/deadline-swarm` of the Terrarium repository. [link]
- Each episode logs every request and response (`requests.jsonl`) and every environment event (`events.jsonl`).
