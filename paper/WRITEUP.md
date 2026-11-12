# Works but Hackable: Measuring and Closing the Security Gap of Gemma 4 on Real Backend Applications

**Subtitle:** A second look beats a security warning: on 280 full backend apps, Gemma 4 31B reviewing its own code adds +8.6 points of secure-and-correct pass@1, while a security prompt adds +1.8.

## Abstract

Open models are increasingly asked to write whole applications, not single functions, yet their security is mostly measured one function at a time. We evaluate Gemma 4 31B-it on the Python half of BaxBench: 56 backend tasks (28 security-critical scenarios × Flask and FastAPI), 5 samples each. Every generated app is started in Docker, checked with functional tests and attacked with end-to-end exploits. Gemma's apps work 72.5% of the time, but only 43.2% work *and* resist every exploit: **40.4% of working apps are exploitable**, most often through resource exhaustion (CWE-400) and cross-site scripting (CWE-79). We compare two zero-training fixes any developer can apply to any model. BaxBench's generic security prompt changes secure-and-correct pass@1 by +1.8 points (95% CI −5.0 to +8.9). A single **self-review pass**, in which the model audits its finished app against a ten-item checklist, adds **+7.1 points (+1.1 to +14.3)** and cuts the exploitable share of working apps from 40.4% to 26.2%. Review also breaks apps, and we trace three quarters of those breakages to one cause: the reviewer escapes HTML with `jinja2.escape` and `flask.escape`, APIs both libraries have since removed. Keeping the original app whenever the reviewed one fails to start (one launch, no tests) gives **+8.6 points (+2.9 to +15.4)** and costs under $0.001 per app. All 840 apps, review transcripts, per-sample scores and scripts are released.

## 1. Introduction

AI-written code now ships in production services, yet most security evaluations of code models still ask for one function at a time (CWEval, SecurityEval, CyberSecEval). Real deployments ask for more: a whole backend with routing, authentication, a database and file handling, where one missing check anywhere is exploitable. BaxBench (Vero et al., 2025) measures exactly this. It found that even frontier models produce working but exploitable backends at high rates.

This matters most for the models developers run themselves. Gemma 4 is built for local and on-device use, so the question "can I trust the backend it wrote?" is one its users often answer without a frontier model or a security team in the loop. We ask two practical questions:

1. **How large is the security gap for Gemma 4 on real backend tasks?** How often does it produce apps that work but can be exploited, and which weaknesses dominate?
2. **Which cheap, model-agnostic fix closes the most of it?** A security instruction up front, or a second pass in which the model reviews its own code?

The second question comes from our earlier, unpublished result on single functions. On CWEval, a self-review checklist added +8.9 points of secure-and-correct pass@1 to a 120B open model, more than LoRA fine-tuning on 1,813 verified secure-coding tasks (+4.9). It was not obvious that this gain would survive the jump to whole applications. An app has more places for a flaw to hide, and the reviewer must keep the entire API contract intact while it fixes things.

**Contributions.**
- A measurement of Gemma 4 31B on BaxBench Python (280 apps per condition, 840 scored in total), with per-CWE and per-framework failure analysis.
- A controlled, paired comparison of security prompting against self-review on the same 56 tasks, with bootstrap confidence intervals and sample-level transitions (which apps review fixed, which it broke, and why).
- A diagnosis of review's main failure mode, a removed library API. A zero-test guard recovers it, giving a significant gain over both the base model and the security prompt.
- A released, reproducible pipeline, including a fix for running BaxBench's Docker environments on arm64.

## 2. Setup

**Benchmark.** BaxBench v1.0.0 (MIT licence). Each task pairs a scenario (an OpenAPI specification for a backend such as a login service, a file search API, a secret store or a shopping cart) with a framework. We use all 28 scenarios × {Flask, FastAPI} = 56 tasks. For each generated app, BaxBench builds a Docker image, starts the server, runs the scenario's functional tests, then runs its security exploits (SQL and OS-command injection, path traversal, XSS, log injection, missing authorisation, weak credential storage, resource exhaustion and others). A sample is **correct** if every functional test passes. It is **secure and correct** (BaxBench's sec_pass) if it is correct and no exploit succeeds. We report pass@1 averaged over 5 samples per task, then over tasks.

**Model.** Gemma 4 31B-it via OpenRouter (`google/gemma-4-31b-it`), temperature 0.4, BaxBench's own OpenAPI prompt and system prompt, no reasoning mode.

**Conditions.**
- **Base:** BaxBench's standard prompt.
- **Security prompt:** BaxBench's built-in `generic` safety prompt, which adds an instruction to follow secure-coding best practice.
- **Self-review:** after generating with the base prompt, the same model sees its own app as the previous assistant turn and receives a ten-item checklist: path traversal; injection into shell, SQL or templates; HTML, header and log-line neutralisation; SSRF; authorisation and ownership checks; password and token handling; cryptography; deserialisation; resource limits; error handling. It is told to keep every endpoint, status code and response format exactly as specified, and to return the full fixed app. The checklist comes from our earlier function-level work, extended with four web items. It never sees BaxBench's tests, exploits or CWE labels. If no code comes back, the original app is kept. Each review revises one specific base sample, so outcomes pair sample by sample.
- **Self-review + start check:** the same reviewed apps, except that the original is kept whenever the reviewed app never starts. "Never starts" means the server answers none of the functional requests; in practice that is one launch of `python app.py`. The guard uses no test or exploit outcome and is computed post hoc from the scored runs.

**Statistics.** Differences are paired by task. 95% confidence intervals come from 5,000 bootstrap resamples of the 56 tasks.

**Infrastructure.** All generation (1,960 base apps across BaxBench's 14 frameworks, plus the 280 security-prompt apps and 280 reviews) cost about $2.40 in API calls. Scoring ran BaxBench's unmodified tests on a 32-vCPU Linux VM. Docker image builds there occasionally crashed under parallel load (a containerd race on BaxBench's shared image tag). We re-ran every sample whose image failed to build until all 840 built. None of these crashes depended on the generated code. On arm64 hosts, BaxBench's Debian Bullseye images fail to build because the security mirror lists an arm64 sqlite3 package that returns 404. We point apt at the snapshot mirrors the images already pin, which changes only where packages are downloaded from (`docs/SETUP.md`).

## 3. Results

### 3.1 The gap

**Table 1.** Gemma 4 31B on BaxBench Python, 280 apps per condition. Deltas are in secure-and-correct pass@1 versus base, with 95% CIs.

| Condition | Correct | Secure & correct | Δ vs base | Exploitable, among correct | Never started |
|---|---|---|---|---|---|
| Base | 72.5% | 43.2% | — | 40.4% | 8.2% |
| Security prompt | 70.4% | 45.0% | +1.8 [−5.0, +8.9] | 36.0% | 9.6% |
| Self-review | 68.2% | 50.4% | **+7.1 [+1.1, +14.3]** | **26.2%** | 12.9% |
| Self-review + start check | **73.9%** | **51.8%** | **+8.6 [+2.9, +15.4]** | 30.0% | **5.4%** |

Gemma 4 31B writes a working backend 72.5% of the time, but 40.4% of those working apps fall to at least one exploit. Only 43.2% are both correct and secure. **Two in five apps that a developer would see "working" are exploitable.** The gap depends strongly on the framework. Both work equally often (Flask 72.1%, FastAPI 72.9%), but 32.6% of working Flask apps are exploitable against 48.0% of working FastAPI apps (secure and correct: 48.6% vs 37.9%). 8.2% of apps never start at all and these count as failures in every metric.

The weaknesses in working base apps are concentrated in a few classes: uncontrolled resource consumption (CWE-400, 33 samples), XSS (CWE-79, 28), log injection (CWE-117, 10), insufficiently protected credentials (CWE-522, 9), improper access control (CWE-284, 8) and path traversal (CWE-22, 7). Classic injection is absent: no SQL or OS-command injection exploit succeeded against any working app. What it misses are the checks a specification does not spell out, such as limits on input size, escaping of user text rendered as HTML, and stripping newlines before logging.

### 3.2 A warning versus a second look

The security prompt barely moves the needle: +1.8 points, a CI that spans zero, and better results on 8 tasks against worse on 6. It does remove log injection entirely (CWE-117: 10 → 0), but it slightly *increases* resource-exhaustion and XSS findings (CWE-400: 33 → 36, CWE-79: 28 → 29). Its overall exploitable rate among working apps falls only from 40.4% to 36.0%. Telling Gemma to "be secure" makes it fix the problem it already knows to look for, and little else.

Self-review is far more effective at removing vulnerabilities. Among working apps the exploitable share falls from 40.4% to **26.2%**, a 35% relative reduction. Secure-and-correct pass@1 rises by **+7.1 points** (CI +1.1 to +14.3), with 11 tasks better and 4 worse. The paired transitions in Table 2 show where this comes from: review turns 25 of the 82 exploitable base apps (30%) into secure ones, and breaks the functionality of only 7 of the 121 apps that were already secure.

**Table 2.** What self-review did to each base sample (n = 280).

| Base → after review | Secure | Exploitable | Broken |
|---|---|---|---|
| **Secure** (121) | 113 | 1 | 7 |
| **Exploitable** (82) | **25** | 44 | 13 |
| **Broken** (77) | 3 | 5 | 69 |

Review is not free, however. It breaks 20 working apps (13 exploitable, 7 secure), and correctness falls by 4.3 points (CI −10.0 to +0.7). Against the security prompt directly, review alone is +5.4 points (CI −0.7 to +12.5), better on 12 tasks and worse on 6, which is suggestive but not conclusive. So the real question is what breaks the apps.

### 3.3 Why review breaks apps, and a one-launch fix

We read the server logs of every working app that review broke. **15 of the 20 failed for the same reason:** the reviewer, correctly deciding to HTML-escape user input against XSS, wrote `from jinja2 import escape` (22 apps) or `from flask import escape` (4 apps). Both names were removed, in Jinja2 3.1 (2022) and Flask 2.3 (2023); the function now lives in `markupsafe`. All 26 apps that use them crash on import. The base model never used either import. This is a failure of stale API knowledge, not of security judgement: the model picked the right fix and called it with a function that no longer exists.

This failure is cheap to detect without any security tooling: the app does not start. The **start check** keeps the original app whenever the reviewed one never starts, which needs a single launch and no tests. With it, the "never started" rate falls *below* base (8.2% → 5.4%, as review also repairs some apps that never ran). Correctness rises slightly (72.5% → 73.9%), and secure-and-correct pass@1 reaches **51.8%: +8.6 points over base (CI +2.9 to +15.4)**, better on 12 tasks and worse on only 2. Against the security prompt it is **+6.8 points (CI +0.7 to +13.9)**, a significant win for the second look over the warning.

The guard has a visible cost in Table 3. Falling back to the original app also restores the original's XSS bug, so CWE-79 returns from 14 to 26. The reviewer's *intent* was right on those apps. A checklist line naming `markupsafe.escape`, or an environment with the old names, would likely keep both gains. We did not test this, to avoid tuning the method on the benchmark.

**Table 3.** CWEs among working apps (count of samples; one sample can have several).

| CWE | Base | Security prompt | Self-review | Review + start check |
|---|---|---|---|---|
| 400 Resource exhaustion | 33 | 36 | 27 | 27 |
| 79 Cross-site scripting | 28 | 29 | **14** | 26 |
| 117 Log injection | 10 | **0** | **0** | **0** |
| 522 Weak credential protection | 9 | 6 | 9 | 9 |
| 284 Improper access control | 8 | 6 | 4 | 4 |
| 22 Path traversal | 7 | 7 | 4 | 4 |
| Exploitable working samples | 82 | 71 | **50** | 62 |

Across all reviewed samples that still run, review removed 10 log-injection, 10 resource-exhaustion, 4 access-control, 3 path-traversal and 3 XSS findings, and introduced only 3 new ones (two XSS, one resource exhaustion). **Resource exhaustion is the hardest class:** review removes some of it, but CWE-400 remains the most common weakness in every condition. Fixing it means inventing limits (body size, list length, regex complexity, upload size) that the specification never states.

**By framework.** Flask gains steadily under review (secure and correct 48.6% → 54.3% → 55.7% with the start check). FastAPI, which starts from the larger gap, gains more (37.9% → 46.4% → 47.9%). Its correctness drop under unguarded review (72.9% → 63.6%) is fully recovered by the start check (72.9%). FastAPI apps that render HTML use Jinja2 directly, which is why the removed import hit them hardest.

### 3.4 Cost

Self-review doubles the number of model calls. For all 280 apps it cost **$0.234** on OpenRouter, or **$0.00084 per app ($0.84 per 1,000 apps)**, about the same as generating the app in the first place. The start check costs one process launch. The security prompt is free, and on this evidence nearly free of effect too.

## 4. Discussion

**A second look is worth more than a warning.** Telling Gemma 4 up front to write secure code changes little: it fixes the one class it already anticipates (log injection) and leaves the rest. Asking it to audit concrete code against concrete failure modes halves XSS, removes log injection, cuts path traversal and access-control bugs, and reduces the exploitable share of working apps by a third. The gain (+8.6 points with the start check) is close to what the same style of review gave a 120B model on single functions (+8.9 on CWEval). This suggests the effect is not specific to one model, one benchmark or the function-level setting. Gemma appears to *have* the security knowledge; what it lacks while generating is the *check*.

**The failure modes of review are mechanical, so they are cheap to guard.** Three quarters of review's breakages came from a single removed API. That matters for anyone deploying self-review: a small model's library knowledge lags its security knowledge, and a one-launch smoke test is enough to stop a "fix" from shipping a crash.

**What remains is the specification gap.** After review, the dominant residual weakness is resource exhaustion, followed by credential protection (CWE-522, unchanged by any intervention). Both need decisions the API specification does not make: how large an input may be, or which password hash to use. These are good targets for fine-tuning or for checklists specific to a framework or domain.

**Limitations.** One model size, one temperature and 5 samples per task; with 56 tasks, CIs are several points wide, and only the review conditions exclude zero. Python frameworks only: BaxBench also covers Go, JavaScript, PHP, Ruby and Rust, and all 1,960 base samples across 14 frameworks are generated and released for follow-up. Exploits test known attack patterns, so passing them does not prove an app is secure. The checklist was designed by us. The start check is computed post hoc from BaxBench's "no functional request succeeded" signal rather than by a separate launch, though both detect the same import-time crash. We planned a third intervention, LoRA fine-tuning of Gemma 4 12B on 959 execution-verified secure-coding tasks, but GPU capacity was not available in time. The training and generation scripts are released.

## 5. Related work

- **App-level security benchmarks.** BaxBench (Vero et al., ICML 2025) evaluates correct and secure backend generation with end-to-end exploits; SecRepoBench and SEC-bench evaluate repository-level secure completion and vulnerability patching.
- **Function-level secure code generation.** CWEval (Peng et al., 2025), CyberSecEval (Bhatt et al., 2023) and Pearce et al. (2022) measure insecure completions. SafeCoder (He et al., 2024) instruction-tunes for security and reports trade-offs with functionality.
- **Self-correction.** Self-Refine (Madaan et al., 2023) shows that iterative self-feedback improves many generation tasks. We test a single, checklist-guided security review on whole applications, measure what it breaks as well as what it fixes, and pair it with an execution guard.

## References

- Vero, M., Mündler, N., Chibotaru, V., Raychev, V., Baader, M., Jovanović, N., He, J., Vechev, M. *BaxBench: Can LLMs Generate Correct and Secure Backends?* ICML 2025. arXiv:2502.11844.
- Peng, J., Cui, L., Huang, K., Yang, J., Ray, B. *CWEval: Outcome-driven Evaluation on Functionality and Security of LLM Code Generation.* LLM4Code @ ICSE 2025. arXiv:2501.08200.
- He, J., Vero, M., Krasnopolska, G., Vechev, M. *Instruction Tuning for Secure Code Generation.* ICML 2024 (PMLR 235). arXiv:2402.09497.
- Bhatt, M. et al. *Purple Llama CyberSecEval: A Secure Coding Benchmark for Language Models.* 2023. arXiv:2312.04724.
- Pearce, H. et al. *Asleep at the Keyboard? Assessing the Security of GitHub Copilot's Code Contributions.* IEEE S&P 2022.
- Madaan, A. et al. *Self-Refine: Iterative Refinement with Self-Feedback.* NeurIPS 2023.
- Gemma Team, Google DeepMind. *Gemma 4 Technical Report.* 2026.

## Reproducibility

Code, prompts, all generated apps, review transcripts (`review.json` per sample), BaxBench server logs and per-sample scores: https://github.com/jenishk20/gemma-secure-backends. Key scripts: `scripts/baxbench_review.py` (self-review), `scripts/score_all.sh` (scoring), `scripts/summarize.py` (all tables, CIs, transitions and the start check). Running `python3 scripts/summarize.py` on the released results regenerates every number in this paper (`results/summary.txt`).
