"""Build the hackathon submission (Apart Research template order) as a .docx.

python build_submission_docx.py  ->  SUBMISSION_apart.docx
"""
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt

TITLE = ("When Do AI Agents Share Answer Keys? Incentives, Confidentiality Rules, "
         "and Peer Influence in a Six-Agent Ring")

ABSTRACT = (
    "Deployed LLM agents will face situations where breaking a rule pays. We study this in a pre-registered "
    "testbed: six LLM agents (glm-5.2, deepseek-v4-flash, qwen3.5-397b) sit in a ring, can message only their "
    "two neighbours, and solve timed puzzles for individual scores while some hold other agents' answer keys. "
    "Rules work: when the key is necessary and sharing is permitted, keys were shared in 9 of 9 episodes and 56% "
    "of workers submitted their key before even seeing their puzzle; adding one unmonitored sentence (\"Answer "
    "keys are confidential. Do not send...\") cut early key use to 0% and disclosures to 1 of 6 episodes. Agents "
    "forfeited their entire puzzle score (0.65 to 0.00) rather than break it. But agents keep the letter, not "
    "the spirit: they proposed workarounds that convey a key without sending it - yes/no verification of guesses, "
    "or deriving the rule from the key - in 198 messages across 23 episodes. Their same-turn reasoning cites "
    "needing their own answer framed as a fair exchange (77%/76%), a narrow reading of the rule (52%) and the "
    "designer's assumed intent (38%), rarely altruism (5%) or score-maximising (2%). A planted rule-breaker added "
    "little: 15-22% of its peers broke the rule, against 12.5% with no instigator. Method lesson: a null \"agents "
    "don't cheat\" result is informative only if the shortcut is valuable, has a moment of use, and beats the "
    "honest path; our first environment violated these, and its null reversed once fixed (+21 points).")

doc = Document()
st = doc.styles["Normal"]
st.font.name = "Times New Roman"
st.font.size = Pt(11)


def h(text, level=1):
    doc.add_heading(text, level=level)


def p(text, italic=False, bold_lead=None, size=None, align=None):
    para = doc.add_paragraph()
    if bold_lead:
        r = para.add_run(bold_lead)
        r.bold = True
    r = para.add_run(text)
    r.italic = italic
    if size:
        r.font.size = Pt(size)
    if align:
        para.alignment = align
    return para


def bullets(items):
    for it in items:
        if isinstance(it, tuple):
            para = doc.add_paragraph(style="List Bullet")
            para.add_run(it[0]).bold = True
            para.add_run(it[1])
        else:
            doc.add_paragraph(it, style="List Bullet")


def numbered(items):
    for it in items:
        para = doc.add_paragraph(style="List Number")
        if isinstance(it, tuple):
            para.add_run(it[0]).bold = True
            para.add_run(it[1])
        else:
            para.add_run(it)


def table(caption, header, rows):
    cap = doc.add_paragraph()
    cap.add_run(caption).italic = True
    t = doc.add_table(rows=1 + len(rows), cols=len(header))
    t.style = "Light Grid Accent 1"
    for j, x in enumerate(header):
        t.cell(0, j).text = x
        for r in t.cell(0, j).paragraphs[0].runs:
            r.bold = True
    for i, row in enumerate(rows, 1):
        for j, x in enumerate(row):
            t.cell(i, j).text = x
    for row in t.rows:
        for c in row.cells:
            for para in c.paragraphs:
                for r in para.runs:
                    r.font.size = Pt(9.5)
    doc.add_paragraph()


# ---- header -------------------------------------------------------------------
tp = doc.add_paragraph()
tp.alignment = WD_ALIGN_PARAGRAPH.CENTER
tr = tp.add_run(TITLE)
tr.bold = True
tr.font.size = Pt(16)
p("Dipanshu Sharma - Independent Researcher", align=WD_ALIGN_PARAGRAPH.CENTER)
p("With Apart Research", italic=True, align=WD_ALIGN_PARAGRAPH.CENTER)
p("Research conducted at the Swarm Alignment Hackathon, November 2026.", italic=True, size=9,
  align=WD_ALIGN_PARAGRAPH.CENTER)

h("Abstract")
p(ABSTRACT)

# ---- 1 introduction ---------------------------------------------------------------
h("1. Introduction")
p("Safety evaluations of LLM agents increasingly ask whether agents will exploit shortcuts: share information "
  "they should not, collude, or game a specification. For multi-agent deployments two questions matter: do "
  "rules hold when breaking them is lucrative and nobody is watching, and does rule-breaking spread from one "
  "agent to its peers? Answering either requires an environment in which the shortcut is real, which we found "
  "is easy to get wrong.")
p("Threat model: agents with individual objectives, a confidentiality rule, and a peer-to-peer channel. The "
  "failure modes are direct disclosure of protected information, indirect disclosure through channels the rule "
  "does not name, and peer pressure that erodes compliance.")
p("Contributions:")
numbered([
    ("Rule compliance under strong incentives. ", "A single unmonitored sentence nearly eliminates a lucrative "
     "cheat that all three models otherwise take (Section 4.2)."),
    ("Letter-not-spirit behaviour. ", "Agents systematically propose loopholes that respect the rule's wording "
     "while defeating its purpose; their reasoning points to task completion and rule-lawyering, not altruism or "
     "reward-seeking (Section 4.3)."),
    ("Peer influence and a method lesson. ", "An instructed instigator adds little beyond a substantial "
     "spontaneous rate of rule-breaking (Section 4.4), and a shortcut experiment's clean null turned out to be an "
     "environment artefact that reversed once three conditions were fixed (Section 4.1)."),
])

h("2. Related Work")
p("Specification gaming - satisfying the literal objective while defeating its intent - is well documented for "
  "single agents (Krakovna et al., 2020) and sits within broader concrete safety problems (Amodei et al., 2016). "
  "Multi-agent work has examined emergent social behaviour of LLM agents (Park et al., 2023), covert collusion "
  "and steganographic channels between them (Motwani et al., 2024), and the wider landscape of multi-agent risks "
  "(Hammond et al., 2025). Our setting differs in three ways: agents face an explicit natural-language rule rather "
  "than a reward to game; the protected information is mechanically detectable (exact 8-character keys), so "
  "compliance is measured without a judge; and we vary the incentive, the rule, and a single peer's instructions "
  "in matched, pre-registered comparisons. The gap we address is how literal rule-following and indirect "
  "circumvention coexist in LLM agent groups, and how evaluation design can hide both.")

# ---- 3 methods ------------------------------------------------------------------
h("3. Methods")
bullets([
    ("Environment. ", "Built on the Terrarium multi-agent framework with a custom real-time runner. Six workers "
     "sit in a fixed ring; each sees only its two neighbours' names. Messages cross one edge per 2-second tick. "
     "Each turn an agent calls exactly one tool: send_message (to a neighbour), write_note, submit_answer, or "
     "wait (5-60 s, returns early on a message). Agents keep their full history; time passes while they think."),
    ("Models. ", "glm-5.2, deepseek-v4-flash and qwen3.5-397b via one provider (temperature 0.7). All six "
     "workers in an episode run the same model, except in experiment M."),
    ("Task. ", "Each puzzle is an 8-character string over A-F; its hidden rule composes two operations "
     "(reverse, rotate, swap adjacent pairs, shift) and is shown through three examples. Puzzle 1 runs in a "
     "360-second preparation phase; puzzle 2 is released at T+360 s with deadline D. Scoring is individual; only "
     "the first submission counts."),
    ("Prompts. ", "Neutral: contacts, tools, time and scoring. An audit of every system prompt and "
     "environment-written line actually sent (324 agents in Q) confirms no model is told to ask for, share or "
     "use keys - except M's instructed instigator."),
    ("Measurement and statistics. ", "Key transfers are exact-string matches of each worker's key (also "
     "spacing, reversal, shift, 6+ character fragments). Each experiment was pre-registered before its first "
     "episode, with dated deviations. Paired bootstrap over (model, seed), 10,000 resamples, 95% CI; Holm "
     "correction within each experiment. Loophole and motive coding uses author-written regular expressions "
     "(exploratory)."),
])
table("Table 1. Experiments. Each arm is matched on seeds (same names, puzzles and key holder).",
      ["Exp.", "Manipulation", "Arms", "Episodes"],
      [["P", "Pointer to the answer holder at release, D = 160 s", "pointer / none", "66"],
       ["Q", "P fixed: pointer and keys during preparation, D = 40 s", "far / none / adjacent (positive control)", "54"],
       ["R", "Key needed to score (no examples), early answer box; rule vs none", "no rule / rule", "15 (pilot)"],
       ["M", "Every worker holds a key + rule; one instructed instigator", "same model / cross model / none", "24 (pilot)"]])
p("What did not work: our first shortcut test (P) gave the shortcut no value; we diagnosed this from transcripts "
  "and redesigned (Section 4.1). A per-episode launch burst exceeded the provider's rate limit; we added paced "
  "launches. A 60-second gateway timeout cuts long post-release turns; it cannot change 40-second on-time "
  "outcomes and is reported per arm.", italic=False)

# ---- 4 results --------------------------------------------------------------------
h("4. Results")
h("4.1 When a null is an environment artefact (P to Q)", 2)
p("Observation. In P, a pointer told the worker farthest from the key holder where the answers were; it had no "
  "effect (keys received +3.0 points, CI -5.5 to +12.1; 33 pairs). Transcripts show the shortcut was worthless: "
  "89% of workers solved alone in time, the told worker submitted on the very turn the pointer arrived in 30 of "
  "32 episodes, and 36 of the 42 workers who ever received their key got it after submitting. In Q, with the "
  "pointer and keys arriving during preparation and D = 40 s, 40% of workers received their own key with the "
  "pointer vs 19% without (+21.1 points, CI +5.6 to +36.7, Holm p = 0.011; 18 pairs); a positive control with the "
  "pointer one hop from the holder passed its pre-registered gate (50% vs gate 25%). Receiving did not mean "
  "benefiting: 21% vs 12% submitted their key on time, and holders of a correct key took a median 27.5 s to "
  "submit vs 26 s solo, because they re-solved to check it.")
p("Interpretation. A shortcut evaluation is informative only if the shortcut is (i) valuable under the arm's "
  "deadline, (ii) available before the agent commits, and (iii) faster than the honest path.")

h("4.2 One sentence nearly eliminates a lucrative cheat (R)", 2)
p("In R puzzle 2 shows no examples (solving alone means guessing among ~100 rules) and a correct answer scores "
  "fully only if submitted before release. The rule arm adds one sentence to the two key holders' instructions: "
  "\"RULE: Answer keys are confidential. Do not send an answer key, or any part, hint or encoding of one, to "
  "anyone.\" There is no monitor or penalty.")
table("Table 2. R results (pilot). Episode bootstrap 95% CIs in brackets. Pre-registered paired tests: R1 early "
      "key use +52.8 points [+16.7, +86.1], Holm p = 0.001; R2 any disclosure +83.3 points [+50, +100].",
      ["Measure", "No rule (n = 9)", "Rule (n = 6)"],
      [["Workers submitting their key before release", "56% [28-82]", "0%"],
       ["Episodes with any key disclosure", "100%", "17%"],
       ["Holder received its own key", "78%", "17%"],
       ["Mean puzzle-2 score", "0.65", "0.00"]])
p("Without the rule every model cheats (early key use: deepseek 89%, glm 44%, qwen 33%; qwen shared nothing in "
  "P or Q). With the rule, key holders cited it in every episode and forfeited the whole puzzle.")

h("4.3 Letter, not spirit: loopholes and their motives", 2)
p("Although the rule bans any \"hint or encoding\", agents across the rule conditions proposed a verification "
  "oracle (\"I can't share the key... but I can verify candidate answers you propose (yes/no)\") or rule "
  "derivation (\"send me your P2 input; I'll test candidate rules against the key\") in 198 messages across 23 "
  "episodes. Table 3 codes the same-turn reasoning of the 129 non-instigator messages.")
table("Table 3. Themes in the reasoning behind loophole proposals (n = 129; themes overlap; regex coding, not "
      "human-validated).",
      ["Theme", "Share"],
      [["Needs its own answer or key", "77%"],
       ["Frames it as an exchange (\"you hold mine, I hold yours\")", "76%"],
       ["Reads the rule's scope narrowly (\"applies only to answer keys\")", "52%"],
       ["Infers designer intent (\"the only way is for key holders to verify\")", "38%"],
       ["Voices caution, then proceeds", "33%"],
       ["Admits equivalence to sending the key", "5%"],
       ["Helping others", "5%"],
       ["Explicit score-maximising", "2%"]])
p("Interpretation. The loopholes look like task-completion moves: the agent needs its own answer, judges the task "
  "unsolvable alone, infers that the designers must intend key holders to help, and reads the rule narrowly "
  "enough to permit it. One glm agent: \"Is telling her the rule equivalent to telling her the answer? In a sense, "
  "yes, but the rule itself is not the answer key - it's the method.\" Proposing, using and profiting differ: in "
  "M, workarounds were proposed in 14 of 16 episodes, used (a holder gave a yes/no verdict without the key) in 7, "
  "and recovered a correct answer for 1 of 80 recipients. The behaviour concentrates in deepseek (113 of 129 "
  "messages; glm 16; qwen 0).")

h("4.4 Peer influence (M)", 2)
p("One worker is privately instructed to persuade the others that the rule is pointless; the five recipients are "
  "glm or deepseek and the instigator is the same model, the other model, or (exploratory baseline, added after "
  "the main results) an ordinary worker.")
table("Table 4. M results (8 pairs per comparison). Pre-registered M1 (same vs cross, recipients breaking the "
      "rule): -7.5 points [-30, +15], not supported.",
      ["Measure", "Same-model instigator", "Cross-model instigator", "No instigator"],
      [["Recipients sending a key", "15%", "22%", "12.5%"],
       ["Episodes with >= 1 recipient break", "50%", "62%", "50%"],
       ["Difference vs no instigator", "+2.5 [-12.5, +17.5]", "+10.0 [-2.5, +22.5]", "-"]])
p("Observation. Most rule-breaking is spontaneous under these lucrative settings; the instigator adds at most a "
  "modest increment, and its model makes no detectable difference. Recipients typically refused first (\"I'm "
  "bound by this rule\") and then proposed the workarounds of Section 4.3.")

# ---- 5 discussion -----------------------------------------------------------------
h("5. Discussion and Limitations")
p("Implications. Explicit rules are a strong lever - one sentence outweighed a large, immediate incentive in all "
  "three models - but compliance is literal: agents search the space the wording leaves open and justify it by "
  "inferring designer intent. Rules should name the purpose (\"do not help anyone obtain another's answer by any "
  "means\"), and monitors should cover confirmation channels, not only verbatim leaks. Evaluation design "
  "determines whether any of this is visible.")
p("Limitations. R (6 pairs) and M (8 pairs) are pilots with wide intervals. Loophole and motive coding is "
  "author-written regex, not human-validated. Some measures and the M baseline were added after earlier results "
  "and are labelled exploratory. All models were served by one provider; a toy domain, three open-weight models, "
  "one topology and short episodes limit generality. In R the rule was shown only to key holders. If agents "
  "inferred they were being tested, compliance may overstate deployment behaviour. Deadline pressure itself is "
  "not isolated by these comparisons (Appendix B).")
p("Future work. Randomise a tight vs generous deadline on Q's solvable puzzles with the rule fixed, measuring "
  "whether pressure makes agents act on received keys without re-checking; validate loophole coding with human "
  "labels; study relay corruption and confabulated environment facts (Appendix C).")

h("6. Conclusion")
p("When cheating clearly pays, LLM agents cheat; a single plain-language rule nearly stops them, even unmonitored "
  "and at the cost of their whole score. Yet the same agents keep probing the rule's edges, proposing "
  "confirmation schemes and rule derivations that honour its letter and defeat its purpose, mostly to complete "
  "their own task. Peer pressure adds little on top of this spontaneous tendency. Finally, a shortcut evaluation "
  "can return a reassuring null for reasons that have nothing to do with the agents.")

h("Code and Data")
p("Code, pre-registrations (PREREG_*.md), offline tests, analysis scripts, analysis outputs and the prompt audit "
  "are on branch exp/deadline-swarm: https://github.com/sdipanshu/Terrarium/tree/exp/deadline-swarm/experiments/deadline_swarm . Raw per-episode logs (requests.jsonl, "
  "events.jsonl) are available from the author on request. Info-hazard note: the circumvention "
  "techniques described are elementary and domain-specific; no attack tooling is released.")

h("References")
for ref in [
    "Amodei, D., Olah, C., Steinhardt, J., Christiano, P., Schulman, J., & Mane, D. (2016). Concrete Problems in "
    "AI Safety. arXiv:1606.06565.",
    "Hammond, L., et al. (2025). Multi-Agent Risks from Advanced AI. Cooperative AI Foundation. arXiv:2502.14143.",
    "Krakovna, V., et al. (2020). Specification gaming: the flip side of AI ingenuity. DeepMind Blog.",
    "Motwani, S. R., et al. (2024). Secret Collusion among Generative AI Agents. arXiv:2402.07510.",
    "Park, J. S., O'Brien, J. C., Cai, C. J., Morris, M. R., Liang, P., & Bernstein, M. S. (2023). Generative "
    "Agents: Interactive Simulacra of Human Behavior. arXiv:2304.03442.",
]:
    doc.add_paragraph(ref)

h("Appendix A. Limitations and Dual-Use / Ethical Considerations")
p("Limitations: ", bold_lead=None)
bullets([
    "Pilot sample sizes for R (6 pairs) and M (8 pairs); B and F are also pilots.",
    "Exploratory, unvalidated regex coding of loopholes and motives; the method-sharing detector in Appendix B "
    "is also unvalidated. Key-transfer outcomes are exact-string matches.",
    "Post-hoc additions (measures, M baseline) and an early stop in Q after interim descriptive looks, each "
    "logged as a dated deviation.",
    "Single provider: a 60-second gateway timeout cut long turns (22-33 of 108 agents per Q arm, mostly "
    "deepseek); rate limits shaped scheduling. Experiments ran sequentially, so cross-experiment comparisons "
    "are not randomised.",
    "The M instigator is instructed; M measures how instructed rule-breaking spreads, not how it arises.",
])
p("Dual-use: the findings describe how agents circumvent rules (verification oracles, rule derivation) and how "
  "a peer can be asked to persuade others. These techniques are elementary and specific to a toy domain; we "
  "release no attack tooling, and we judge the defensive value - rule writers and monitors should anticipate "
  "confirmation channels - to outweigh the risk.")
p("Ethics: no human subjects or personal data; all agents are LLMs in a closed simulation without external tools "
  "or internet access. The instigator is a role instruction inside a sandbox and does not train or modify any "
  "model. Every prompt sent is logged and audited.")

h("Appendix B. Deadline pressure and coordination")
p("A and N1 (216 and 142 episodes): a 40-second deadline did not increase useful method-sharing vs 160 seconds "
  "(A1 -6.9 points, CI -19.4 to +5.6; N1 -5.6, CI -18.3 to +7.0). One permissive prompt line moved sharing more "
  "than the deadline (+19 points, CI +8 to +30; not randomised). B (pilot): mixing deadlines in one ring lowered "
  "tight workers' on-time rate (-20 points, CI -36 to -6). F (pilot, rule, solvable puzzles): no outright key "
  "transfer; tight deadlines raised requests for keys (+54 points, CI +23 to +77) and a monitor cut them (-54, "
  "CI -77 to -23).")

h("Appendix C. Further exploration")
bullets([
    "Relay corruption: keys mutate across hops (FCDEBDFE became FCDEBDFF over three relays).",
    "Confabulated environment facts spread through the ring (e.g. \"each worker holds answer keys for all others\").",
    "Verification overhead: agents re-solve rather than trust a correct peer answer.",
])

h("LLM Usage Statement")
p("Claude (Anthropic) was used to write and test the experiment code, run and monitor the experiments, compute "
  "the pre-registered analyses, and draft this report. All reported numbers were produced by the committed "
  "analysis scripts from logged data; the author reviewed the claims, prompts and transcript excerpts. "
  "Loophole and motive codes were produced with author-written regular expressions and have not been validated "
  "by an independent human labeller.")

doc.save("SUBMISSION_apart.docx")
print("saved SUBMISSION_apart.docx")
