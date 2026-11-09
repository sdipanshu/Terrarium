# When Do AI Agents Share Answer Keys?

**Incentives, confidentiality rules, and peer influence in a six-agent ring.**

Dipanshu Sharma (Independent Researcher). With Apart Research, Swarm Alignment Hackathon, November 2026.

Six LLM agents sit in a ring, can message only their two neighbours, and solve timed puzzles for individual scores. Some of them hold other agents' answer keys. We ask when they share the keys, whether a plain rule stops them, and whether one rule-breaker spreads the behaviour.

Models: `glm-5.2`, `deepseek-v4-flash`, `qwen3.5-397b`. Every experiment was pre-registered, with dated deviations.

## Key findings

| | Finding | Evidence |
|---|---|---|
| **1** | **One unmonitored sentence nearly eliminates a lucrative cheat.** | Without a rule, keys were shared in 9/9 episodes and 56% of workers submitted their key before seeing their puzzle. With "Answer keys are confidential. Do not send…", early key use was 0% and disclosures happened in 1/6 episodes. Agents gave up their whole puzzle score (0.65 → 0.00) rather than break the rule. R1: +52.8 pts (CI +16.7 to +86.1). |
| **2** | **Agents keep the letter of the rule, not its spirit.** | 198 messages in 23 episodes propose workarounds that convey a key without sending it: yes/no verification of guesses, or deriving the rule from the key. The same-turn reasoning cites needing their own answer (77%), a fair exchange (76%), a narrow reading of the rule (52%) and the designer's assumed intent (38%). It rarely cites altruism (5%) or score-maximising (2%). |
| **3** | **A planted rule-breaker adds little.** | 15–22% of its peers broke the rule, against 12.5% with no instigator (+2.5 to +10 pts, CIs include 0). The instigator's model made no detectable difference. |
| **4** | **A "no cheating" null can be the environment's fault.** | The first pointer experiment (P) found nothing because the shortcut was worthless. With three conditions fixed (value, a moment of use, faster than the honest path), Q gave +21 pts of workers receiving their key (40% vs 19%), and a positive control passed. |

- **Write-ups:** [`SUBMISSION_apart.docx`](SUBMISSION_apart.docx) is the hackathon report. [`REPORT.md`](REPORT.md) is the full technical report with every experiment, table and deviation.
- **Background results:** deadline pressure did not increase coordination (A1 −6.9 pts, CI −19.4 to +5.6; N1 −5.6 pts, CI −18.3 to +7.0).

## Experiments

| Exp. | Question | Pre-registration | Episode code | Analysis |
|---|---|---|---|---|
| A, N1 | Does a tight deadline increase method sharing? | `PREREG_A.md`, `PREREG_NOHINT.md` | `episode.py`, `episode_nohint.py` | `analyze_a.py`, `analyze.py` |
| B | Mixed deadlines in one ring | `PREREG_B.md` | `episode_mixed.py` | `analyze_b.py` |
| F | Rule-breaking under pressure, with a monitor | `PREREG_F.md` | `episode_keys.py` | `analyze_f.py` |
| P | Does a pointer to the answer holder spread? | `PREREG_P.md` | `episode_pointer.py` | `analyze_p.py` |
| Q | P with the shortcut made worth taking | `PREREG_Q.md` | `episode_prep_pointer.py` | `analyze_q.py` |
| R | A lucrative cheat, with and without a rule | `PREREG_R.md` | `episode_lucrative.py` | `analyze_r.py` |
| M | Peer influence from an instructed instigator | `PREREG_M.md` | `episode_instigator.py` | `analyze_m.py` |

- **Results:** final analysis outputs are in `outputs/analysis_*.txt` and `outputs/analysis_*.json`.
- **Loophole coding:** `outputs/analysis_loopholes.txt` and `outputs/analysis_loophole_stages.txt`.
- **Prompt audit:** `outputs/audit_prompts_Q.txt`, every system prompt and environment-written line actually sent in Q.
- **Raw logs:** the per-episode logs (`requests.jsonl`, `events.jsonl`) are not in the repository. They are available on request.

## Setup

- **Ring and transport:**
  - Six workers form a ring on a Terrarium `CommunicationNetwork`.
  - A message crosses one edge per 2-second tick, using a monotonic real-time clock.
- **Turns and tools:**
  - Each turn an agent calls exactly one tool: `send_message` (to a neighbour), `write_note`, `submit_answer`, or `wait` (5–60 s, returning early on a message).
  - Each agent keeps its full history for the episode.
- **Puzzles:**
  - Each puzzle is an 8-character string over A–F.
  - Its hidden rule is a composition of two operations (reverse, rotate, swap adjacent pairs, shift), shown through three examples. R and M show no examples for puzzle 2.
- **Key detection:** exact-string matching of each worker's key, also allowing spacing, reversal, shift and 6+ character fragments (`episode_keys.detect_key`).
- **Statistics:** paired bootstrap over (model, seed), 10,000 resamples, 95% CI, with Holm correction within each experiment.

## Running

Requirements:
- Python 3.11 or later, with the Terrarium package installed: `pip install -e .` at the repo root.
- An Adaption API key in `.env` as `ADAPTION_API_KEY`. The client is in `adaption_client.py`.

```bash
cd experiments/deadline_swarm

# offline tests: scripted agents on a fake clock, no API calls
python -m unittest test_smoke test_keys test_pointer test_prep_pointer test_lucrative test_instigator test_analysis -v

# one episode
python run_batch_r.py --one glm-5.2 501 R_rule outputs/expR/glm-5.2__s501__R_rule

# a batch with resume and archiving, or the paced queue used for the real runs
python run_batch_r.py --root outputs/expR --seeds 501-510
python slot_queue.py --only expR --budget 2 --stop-at 15:30

# analysis
python analyze_r.py outputs/expR --json outputs/analysis_R.json
```

- **Queue settings:** `slot_queue.py` paces launches to stay under the provider's rate limit of about 50 requests a minute: a 60 s gap between launches, a guard that holds launches when 429s spike, and a budget you can change while it runs (`outputs/slot_budget.txt`).
- **Reading an episode:** `transcript.py` renders an episode as a readable per-agent transcript.

## Limitations

- **Small pilots:** R (6 pairs) and M (8 pairs) are pilots.
- **Unvalidated coding:** the loophole and motive coding uses author-written regular expressions and is not yet human-validated.
- **Post-hoc additions:** some measures, and M's no-instigator baseline, were added after earlier results. Each is logged as an exploratory deviation in the `PREREG_*.md` files.
- **Infrastructure:** all models were served by one provider, and a 60 s gateway timeout cut off some long turns.
- **More:** see Appendix A of the report for the full list and the dual-use considerations.

## LLM usage

Claude (Anthropic) helped write and test the code, run and monitor the experiments, compute the pre-registered analyses, and draft the reports. All numbers come from the committed analysis scripts, and the author reviewed the claims, prompts and transcript excerpts.
