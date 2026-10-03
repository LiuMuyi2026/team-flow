# Teams where everyone uses CLI coding agents: coordination pain, security risks, expected controls, price points (state of the world 2026-10-03)

Evidence labels used below (a reading key, not a section). **[primary]** means I fetched and read the page itself. **[snippet]** means only a search-engine snippet or summary was available because the egress proxy blocked the page. Blocked sites included news.ycombinator.com, reddit.com (also refused by the search tool), arxiv.org, survey.stackoverflow.co, linearb.io, thehackernews.com, labs.cloudsecurityalliance.org, simonwillison.net, newsletter.pragmaticengineer.com, hai.stanford.edu, github.blog and chrisloy.dev. Treat snippet wording as paraphrase and its numbers as medium confidence. **[aggregator]** means a third-party compilation rather than the original publisher, which is lower confidence. "Data" means survey, telemetry or benchmark results; "anecdote" means an individual's report.

---

## Q1. What coordination problems do agent-heavy teams actually report?

### Takeaway
The best-quantified team-level pain is not duplicate work or merge conflicts. It is the review/merge queue: agent PRs wait several times longer for a first human review and merge far less often. Agents also help individuals much more than teams: only 17% of agent users say agents improved collaboration within their team. Agent work is mostly done by one person at a time. One developer usually both reviews and fixes the agent's output, and only about 1 in 8 agentic workflows involves more than one human. The vendors' own multi-agent features stay inside one person's session, and their docs list failure modes: task status that lags, file overwrites, agents that stop early, and false "needs you" alerts. Practitioners do report duplicated work, conflicting edits, silent stalls and lost context, but I found no survey-grade numbers for any of them.

### Cited Findings

**Survey, telemetry and benchmark data**
- Stack Overflow Developer Survey 2025 (results out mid-2025): about 70% of agent users agree agents reduced time on specific tasks and 69% agree they increased productivity. Only **17% agree agents "improved collaboration within my team"**, the lowest-rated impact by a wide margin. [snippet] — [Stack Overflow 2025 Developer Survey](https://survey.stackoverflow.co/2025/); [The New Stack](https://thenewstack.io/23-of-devs-regularly-use-ai-agents-per-stack-overflow-survey/)
- SO 2025: 87% of developers are concerned about the accuracy of information from AI agents, and 81% worry about the privacy and security of data when using them. [snippet] — [Stack Overflow 2025 Developer Survey](https://survey.stackoverflow.co/2025/)
- LinearB 2026 Software Engineering Benchmarks (8.1M PRs, about 4,800 teams/orgs, 163,820 contributors, 42 countries):
  - AI PRs **wait 4.6x longer before review**, but are reviewed 2x faster once someone picks them up.
  - AI PRs **merge within 30 days 32.7% of the time, against 84.4% for unassisted PRs**. [snippet of LinearB's own pages]
  - Sources: [LinearB benchmarks](https://linearb.io/resources/engineering-benchmarks); [LinearB blog](https://linearb.io/blog/8-million-prs-engineering-productivity); [byteiota](https://byteiota.com/linearb-2026-ai-prs-wait-4-6x-longer-queue-crisis/)
  - **Conflict:** one secondary write-up says "agentic AI PRs wait 5.3x longer". It may be counting a different category (agentic vs AI-assisted), and I did not resolve the difference. [aggregator] — [baeseokjae.github.io](https://baeseokjae.github.io/posts/linearb-2026-engineering-benchmarks/)
- Aggregators say GitHub reported in May 2026 that Copilot code review had processed more than 60M reviews and that more than 1 in 5 code reviews on GitHub involve an agent. [aggregator; GitHub primary not verified] — [prlens.dev](https://prlens.dev/guides/ten-x-prs-one-x-reviewers); [flowverify](https://www.flowverify.co/blog/ai-code-review-bottleneck-2026-data)
- Empirical study of **25,264 agent-generated PRs across 2,361 popular GitHub repos (2025 data)**:
  - In 70% of projects, fewer than 1 in 5 contributors took part in agentic workflows.
  - The median project produced only 1–2 agent PRs over 3 months.
  - **In 79% of agentic PRs, the same developer both reviewed and modified the AI's contribution.**
  - Only about 1 in 8 workflows involved more than one human. [snippet]
  - Sources: [LeadDev, "AI-coding agents kill team collaboration"](https://leaddev.com/ai/ai-coding-agents-kill-team-collaboration); [arXiv 2607.14037, "Early Adoption of Agentic Coding Tools by GitHub Projects"](https://arxiv.org/pdf/2607.14037)
- CooperBench (Stanford-led, arXiv 2601.13295, Jan 2026), more than 600 collaborative coding tasks across 12 libraries in 4 languages: [snippet]
  - Agents score on average **about 30% lower when two cooperate** than when one agent does both tasks. GPT-5 and Claude Sonnet 4.5 reach about 25% with two-agent cooperation, roughly 50% below the single-agent result.
  - Agents spend up to 20% of their budget on communication. This reduces merge conflicts but does not improve success.
  - Failure causes:
    - **Expectation failures 42%**: the agent does not integrate its partner's state.
    - **Commitment failures 32%**: the agent breaks promises or makes claims that cannot be verified.
    - **Communication failures 26%**: questions go unanswered.
  - Sources: [arXiv 2601.13295](https://www.arxiv.org/abs/2601.13295); [CooperBench](https://cooperbench.com/); [Stanford HAI](https://hai.stanford.edu/news/ai-coding-agents-fail-at-teamwork)
- Anthropic internal study (published Dec 2, 2025; 132 engineers surveyed, 53 interviews, 200k Claude Code transcripts): [primary]
  - Engineers self-report using Claude in 60% of their work, with a +50% productivity boost.
  - "More than half said they can 'fully delegate' only between 0-20% of their work."
  - Questions now go to the agent instead of colleagues: "I ask way more questions [now] in general, but like 80-90% of them go to Claude"; "More junior people don't come to me with questions as often."
  - Engineers worry that the skills needed to supervise AI are eroding (a "supervision paradox").
  - Source: [Anthropic, How AI is transforming work at Anthropic](https://www.anthropic.com/research/how-ai-is-transforming-work-at-anthropic)
- DORA 2025 (Sept 2025): [snippet]
  - AI acts as an "amplifier". It improves throughput but often costs stability where engineering foundations are weak.
  - 59% say code quality improved, 10% say it got worse and 30% are unsure.
  - About 90% use AI (the snippet says "daily") and 65% are heavily reliant on it.
  - Sources: [Google Cloud blog](https://cloud.google.com/blog/products/ai-machine-learning/announcing-the-2025-dora-report); [DORA 2025](https://dora.dev/dora-report-2025/)
- DORA "ROI of AI-assisted Software Development" (2026.01, covered May 2026): [snippet]
  - Teams go through a J-curve: productivity often dips before it improves.
  - A "verification tax" (time spent understanding, validating and correcting AI code) belongs in any ROI calculation.
  - Returns run through code review and the whole delivery flow, not through the speed of opening PRs.
  - Sources: [InfoQ](https://www.infoq.com/news/2026/05/dora-roi-ai-assisted-dev-report/); [Kodus](https://kodus.io/en/dora-accelerate-state-of-devops/)
- METR randomized trial (July 2025): experienced open-source developers were 19% slower with AI tools but believed afterwards that they had been about 20% faster. [snippet] — [ScienceBlog](https://scienceblog.com/t-a-randomized-trial-by-metr-found-that-experienced-developers-completed-real-coding-tasks-19-slower-when-allowed-to-use-ai-tools-yet-afterwards-they-estimated-on-average-that-ai-had-made-them-20-fast/)
- METR 2026 follow-up: about an 18% task-time reduction for 10 returning developers, with a confidence interval from −38% to +9%. METR itself calls this data unreliable, because 30–50% of developers withheld tasks they did not want to do without AI. [aggregator] — [byteiota](https://byteiota.com/metr-ai-productivity-survey-2026/); [ingenire](https://ingenire.com/blog/metr-2026-developer-productivity-study)

**Vendor documentation that admits coordination failure modes [primary]**
- Claude Code "agent teams" are experimental and off by default. The documented limitations and guidance:
  - "Task status can lag: teammates sometimes fail to mark tasks as completed, which blocks dependent tasks."
  - "Two teammates editing the same file leads to overwrites."
  - "One team per session … You can't create additional named teams or share a team across sessions."
  - The task list "persists locally and is never uploaded".
  - "Teammate permission requests bubble up to the lead, which can create friction."
  - "Teammates may stop after encountering errors instead of recovering"; "The lead can stop early too."
  - "Letting a team run unattended for too long increases the risk of wasted effort."
  - Teammates "don't inherit the lead's conversation history", so context has to be passed explicitly.
  - Anthropic recommends starting with 3–5 teammates.
  - Source: [Claude Code Docs: agent teams](https://code.claude.com/docs/en/agent-teams)
- Claude Code issue #98373 (filed Sept 30, 2026): the idle "Claude is waiting for your input" notification fires while background agents or teammates are still running. Reporter: "With several delegations per task this becomes a steady stream of false 'needs you' alerts." — [GitHub issue #98373](https://github.com/anthropics/claude-code/issues/98373)
- Users have built a whole set of tools to answer "is my agent blocked on me?":
  - Notification hooks with event types `permission_prompt`, `idle_prompt`, `agent_needs_input` and `agent_completed`, routed to desktop or phone push.
  - Phone apps that stream live sessions.
  - `claude remote-control`.
  - [snippet] — [alexop.dev](https://alexop.dev/posts/claude-code-notification-hooks/); [codeongrass](https://codeongrass.com/blog/claude-code-notifications-phone/)

**Practitioner anecdotes (Hacker News, snippet-level; wording paraphrased, no verbatim quotes available)**
- Fatigue from reviewing coworkers' AI PRs. Threads include "Ask HN: Etiquette giving feedback on mostly AI-generated PRs from co-workers" and "My coworkers continue to dump hundreds of lines of AI documentation in every PR …". Summaries describe two complaints:
  - Reviewers spend full effort on code the author did not hold to the same standard.
  - Thoughtful review comments get answered with some form of "I don't know, I just had AI do it."
  - [snippet] — [HN 46308807](https://news.ycombinator.com/item?id=46308807); [HN 49337050](https://news.ycombinator.com/item?id=49337050); [HN 45723057](https://news.ycombinator.com/item?id=45723057)
- People building multi-agent setups call **state coordination** the most underappreciated problem, meaning keeping two agents from silently overwriting each other's work on shared state. Their workarounds: [snippet]
  - one Kanban ticket per agent session;
  - file "claims" that flag overlapping work;
  - git worktrees;
  - a central activity log, because you cannot watch many agents in real time.
  - Sources: [HN 46990733](https://news.ycombinator.com/item?id=46990733); [HN 47270020](https://news.ycombinator.com/item?id=47270020)
- "Ask HN: How is your team collaborating while working with coding agents?" (2026). Summarized answers: most collaboration still happens in GitHub issues and PRs, and agents are treated as one more tool. [snippet] — [HN 47393964](https://news.ycombinator.com/item?id=47393964)
- Threads whose titles alone show demand: "Ask HN: What is the 'Control Plane' for local AI agents?", "Ask HN: What do you do when your AI agents are working?" and "Ask HN: How are you keeping AI coding agents from burning money?" [title only] — [HN 47242849](https://news.ycombinator.com/item?id=47242849); [HN 49049986](https://news.ycombinator.com/item?id=49049986); [HN 47559293](https://news.ycombinator.com/item?id=47559293)
- Practitioner guides report that without task claiming, multiple agents fix the same bug independently and overwrite each other. Recommended fixes are directory ownership and worktrees. [anecdote] — [MindStudio](https://www.mindstudio.ai/blog/claude-code-agent-teams-parallel-workflows); [dev.to (battyterm)](https://dev.to/battyterm/how-i-run-a-team-of-ai-coding-agents-in-parallel-p7c)
- Chris Loy, "Coding too fast to collaborate" (July 19, 2026; author is an AI-startup CTO and advisor). Opinion: engineers now talk to their agents instead of their colleagues, and design processes get bypassed because individuals are rewarded for faster delivery. [snippet] — [chrisloy.dev](https://chrisloy.dev/post/2026/07/19/coding-too-fast-to-collaborate)
- Cross-time-zone handoffs: the only material I found was vendor or blog claims that agents can "move tasks forward overnight" for engineers in another region to review. No measured evidence. [snippet] — [MindStudio](https://www.mindstudio.ai/blog/build-ai-agent-runs-overnight)

### Inferences
- **The review queue is the hard-data bottleneck**: 4.6x wait, 32.7% vs 84.4% merge rate, and DORA's point that returns run through review. A board that shows who is waiting on whose review or decision targets the measured pain more directly than a board that only prevents duplicate work.
- **Agent work is single-player today.** One developer reviews and fixes the output 79% of the time, and only 17% say agents helped team collaboration. The vendors' native coordination only covers one human: Claude agent teams allow one team per session and keep the task list local. That leaves a real, unmet need for visibility across several humans each running several agents. The closest incumbent is GitHub Agent HQ "mission control" (see Q2), but it is tied to GitHub and Copilot.
- **Agent-to-agent self-coordination is unreliable.** CooperBench reports 32% commitment failures, and the Claude docs admit status lag and early stops. This supports keeping commitments (claim, assign, done) as human-confirmed board state instead of trusting agents' own claims.
- **The "who is stuck" signal is noisy even for a single person** (false idle alerts, home-made push hooks). A team-level "who is blocked, who is needed" view matches real behavior, but the evidence is anecdotal. Validate it in user interviews.
- Lost context in handoffs and cross-time-zone handoffs are plausible pains (teammates do not inherit context), but they are **not evidenced by data**. They are a hypothesis to test, not a proven need.

### Gaps
- No survey or telemetry quantifies duplicated work or merge-conflict rates between different people's agents, or how often agent sessions silently stall.
- No data on managers' visibility into who is blocked in agent-heavy teams.
- No measured evidence on cross-time-zone handoffs involving agents.
- Reddit content was unreachable: the search tool refuses reddit.com and the proxy blocks it. HN was readable only through snippets, so there are **no verbatim community quotes** here.
- Stack Overflow's 2026 annual survey results were not yet published as of Oct 1, 2026. Their blog was "getting ready for 2026 results" ([SO blog, Sept 30, 2026](https://stackoverflow.blog/2026/09/30/getting-ready-for-2026-results-a-look-back-on-developer-survey-findings)).
- I deliberately excluded aggregator numbers whose origin I could not trace. Examples: "median time in code review up 441.5%", "commits +240% but releases +30%", and "75% of Google's new code is AI-generated (April 2026)".

---

## Q2. Adoption context: how widely are Claude Code and Codex used in teams, how big are the teams, and is running several agents in parallel common?

### Takeaway
By 2026, CLI agents are mainstream among engaged professional developers:
- Claude Code is the most-used and most-loved tool in the Pragmatic Engineer 2026 survey.
- In Stack Overflow's April 2026 pulse survey, agent use is around 59%, against 31% in the 2025 annual survey, though the pulse sample is skewed.
- Codex has several million weekly users.
- Autonomous runs are getting longer.

Vendors have productized running several agents in parallel (Claude Code agent teams, GitHub Agent HQ). Still, **no survey measures what share of engineers run several agents at once**, and the typical size of all-agent teams is not measured either.

### Cited Findings
- SO 2025: [snippet]
  - 31% currently use AI agents; 38% have no plans to; 52% either don't use agents or stick to simpler AI tools.
  - Trust: 46% distrust AI accuracy, 33% trust it, 3% "highly trust" it.
  - The New Stack's headline puts **regular** agent use at 23%, a different measure from "currently using".
  - Sources: [Stack Overflow 2025](https://survey.stackoverflow.co/2025/); [The New Stack](https://thenewstack.io/23-of-devs-regularly-use-ai-agents-per-stack-overflow-survey/)
- Stack Overflow April 2026 pulse survey: [snippet]
  - Agent use is 59%.
  - Among agent users, Claude Code rose from 41% (2025 annual) to 55%. In 2025, ChatGPT (82%) and GitHub Copilot (68%) led.
  - Caveat from SO: the pulse sample was smaller and skewed toward daily AI users and executives, so it is not directly comparable with the annual survey.
  - The 2026 annual survey opened June 23, 2026.
  - Sources: [SO blog, Sept 30, 2026](https://stackoverflow.blog/2026/09/30/getting-ready-for-2026-results-a-look-back-on-developer-survey-findings); [SO blog, June 23, 2026](https://stackoverflow.blog/2026/06/23/the-2026-developer-survey-is-now-open-for-human-developers-only/)
- Pragmatic Engineer "AI Tooling for Software Engineers in 2026" (Mar 7, 2026; 906 respondents; median 11–15 years of experience; mostly Europe and US): [aggregator/snippet; primary blocked]
  - 95% use AI weekly. 75% use AI for at least half of their engineering work, and 56% for 70% or more.
  - **Claude Code is the #1 most-used tool**, reached about eight months after launch.
  - Most loved: Claude Code 46%, Cursor 19%, GitHub Copilot 9%.
  - **70% use 2–4 AI coding tools at the same time.**
  - 55% regularly use AI agents, rising to 63.5% among staff+ engineers.
  - Sources: [Pragmatic Engineer](https://newsletter.pragmaticengineer.com/p/ai-tooling-2026); [aiproductivity.ai summary](https://aiproductivity.ai/news/pragmatic-engineer-survey-ai-tooling-2026/)
- Claude Code reportedly had about $2.5B annualized run-rate revenue by February 2026. [aggregator] — [getpanto.ai](https://www.getpanto.ai/blog/anthropic-ai-statistics)
  - Weekly-active-user figures **conflict**: "4.2M WAU in Q1 2026" vs "surpassed 2M WAU by May 2026". Low confidence. — [gradually.ai](https://www.gradually.ai/en/claude-code-statistics/)
- OpenAI Codex: 3M+ weekly active users by April 8, 2026 (attributed to Sam Altman), with token usage growing 70%+ month over month. [aggregator] — [dev.to](https://dev.to/max_quimby/did-codex-overtake-claude-code-the-7m-user-question-5bam); [Wikipedia](https://en.wikipedia.org/wiki/OpenAI_Codex_(AI_agent))
- Anthropic Economic Index on software development (2025): 79% of Claude Code conversations are classified as automation, against 49% of Claude.ai coding conversations. Startups were the early adopters of Claude Code and enterprises lagged. [snippet] — [Anthropic](https://anthropic.com/research/impact-software-development)
- Anthropic telemetry (published Feb 18, 2026): the 99.9th-percentile Claude Code turn "nearly doubled, from under 25 minutes to over 45 minutes" between Oct 2025 and Jan 2026. The median turn is about 45 seconds. [primary] — [Anthropic, Measuring AI agent autonomy in practice](https://www.anthropic.com/research/measuring-agent-autonomy)
- Anthropic "2026 Agentic Coding Trends Report": predicts a shift from single assistants to orchestrated multi-agent teams. It repeats that developers use AI in about 60% of their work but can "fully delegate" only 0–20%. [aggregator summary] — [NYU Shanghai RITS](https://rits.shanghai.nyu.edu/ai/anthropics-2026-agentic-coding-trends-report-from-assistants-to-agent-teams/)
- Running several agents in parallel has been productized:
  - Claude Code agent teams: experimental, 3–5 teammates recommended. [primary] — [Claude Code Docs](https://code.claude.com/docs/en/agent-teams)
  - GitHub Agent HQ: launched Oct 2025. Its "mission control" lets users "assign, steer, and track the work of multiple agents". Anthropic's Claude and OpenAI's Codex agents were added in Feb 2026 as a public preview for Copilot Pro+ and Enterprise. [snippet] — [GitHub blog](https://github.blog/news-insights/company-news/welcome-home-agents/); [ChannelLife](https://channellife.com.au/story/github-adds-claude-codex-agents-to-unified-ai-hub)
- Community signals: the HN discussion of "Embracing the parallel coding agent lifestyle" (Oct 2025) and a top comment, "What I see most engineers do is parallelize". [snippet] — [HN 45489884](https://news.ycombinator.com/item?id=45489884); [HN 45265597](https://news.ycombinator.com/item?id=45265597)
- A vendor claims that by 2026 individual engineers "routinely" run several agents in parallel. [vendor, unverified] — [aq.dev](https://aq.dev/multiplayer-coding-agents/)
- Adoption within teams is uneven: in 70% of open-source projects, fewer than 1 in 5 contributors use agentic workflows. [snippet] — [LeadDev](https://leaddev.com/ai/ai-coding-agents-kill-team-collaboration)

### Inferences
- The target user (an engineer on Claude Code or Codex) is a large and growing population, especially among senior engineers. Because 70% use 2–4 tools at once, a coordination layer has to work across vendors (Claude Code, Codex and others). That supports an MCP-plus-hooks design over a single-vendor integration.
- Autonomous runs of 45+ minutes at the tail point to a need for asynchronous status (progress and commits reported automatically) rather than live watching.
- "Each engineer runs several agents in parallel" is real among power users but not measured. Treat it as a segment, not the norm.

### Gaps
- No reliable figure for the share of engineers running several agents at once.
- No data on the typical size of teams where everyone uses agents (2–5 people or otherwise).
- Claude Code weekly-active-user figures conflict, and no primary Anthropic number was retrieved.
- SO 2026 annual results are still pending.
- China-specific adoption and availability were not researched (out of scope per brief).

---

## Q3. Security: incidents and attack patterns when agents read shared work items written by other people or agents; recommended mitigations; products that implement them

### Takeaway
The most repeatedly demonstrated real-world attack on coding agents in 2025–2026 is this: **an agent reads text someone else wrote in a shared work tracker, treats it as instructions, and acts on it.** Cases:
- GitHub issues (Invariant Labs, May 2025)
- GitLab merge requests and comments (Legit Security, 2025)
- support tickets (Supabase MCP, July 2025)
- an issue title fed to an AI triage bot (Clinejection, Feb 2026), which led to a real compromise of about 4,000 developer machines
- PR titles and issue comments against Claude Code Security Review, Gemini CLI Action and Copilot's agent (Comment and Control, April 2026)

Two related attack classes:
- **Repository or config files that execute when opened**: Claude Code trust-dialog bypasses, Codex CVE-2025-61260 and GitSpawn (Sept 2026).
- **Supply-chain compromise of agent tooling**: Amazon Q's wiper prompt and Nx "s1ngularity", which drove locally installed agent CLIs with permission-skipping flags.

The consensus mitigations:
- break the "lethal trifecta" / follow the "Rule of Two";
- filter content by the author's trust level;
- sandbox the agent;
- give it least privilege;
- keep consequential actions behind independent human approval.

Products implement parts of this: GitHub MCP lockdown mode, Copilot agent approval rules, Claude Code's sandbox and auto-mode classifier, and Snyk/Invariant guardrails. **I found no product that gates teammate-written task text before it reaches an agent inside a team planning tool.**

### Cited Findings

**Incidents and disclosed attack chains, roughly chronological**
- **GitLab Duo** (reported to GitLab Feb 12, 2025; published May 2025 by Legit Security): [snippet]
  - Hidden prompts were planted in merge request descriptions, commit messages, issue comments and source code, using Unicode smuggling, base16 payloads and white-text KaTeX.
  - Duo Chat was made to leak private source code (and potentially undisclosed vulnerabilities) through an HTML image tag.
  - GitLab fixed it in duo-ui!52.
  - Sources: [Legit Security](https://www.legitsecurity.com/blog/remote-prompt-injection-in-gitlab-duo); [Simon Willison](https://simonwillison.net/2025/May/23/remote-prompt-injection-in-gitlab-duo/)
- **GitHub MCP "toxic agent flow"** (Invariant Labs, May 2025): [snippet]
  - An attacker files an issue in a public repo. The user then asks their agent something harmless, such as to check open issues.
  - The agent pulls private-repo data into context and leaks it through a public PR.
  - Described as an architectural problem rather than a server bug, with "no obvious fix".
  - Sources: [Invariant Labs](https://invariantlabs.ai/blog/mcp-github-vulnerability); [DevClass](https://www.devclass.com/ai-ml/2025/05/27/researchers-warn-of-prompt-injection-vulnerability-in-github-mcp-with-no-obvious-fix/1623458)
- **Supabase MCP** (General Analysis demo, July 2025): [snippet]
  - Text in a support ticket told the developer's agent (Cursor with the Supabase MCP server running on the `service_role` key, which bypasses row-level security) to read the `integration_tokens` table and post the contents into the ticket.
  - Supabase said no customer incident occurred.
  - Sources: [General Analysis](https://generalanalysis.com/blog/supabase-mcp-blog); [Pomerium](https://www.pomerium.com/blog/when-ai-has-root-lessons-from-the-supabase-mcp-data-leak)
- **Amazon Q Developer VS Code extension v1.84.0** (July 2025): [snippet]
  - An attacker's PR to the official repo inserted a wiper prompt ("clean a system to a near-factory state and delete file-system and cloud resources"), and it shipped publicly.
  - It was flagged about six days later, on July 23. Reportedly it did not work because of a syntax error. The fix shipped in 1.85.0.
  - Sources: [The Register](https://www.theregister.com/2025/07/24/amazon_q_ai_prompt/); [SC World](https://www.scworld.com/news/amazon-q-extension-for-vs-code-reportedly-injected-with-wiper-prompt)
- **Nx "s1ngularity"** (Aug 26, 2025): [snippet/aggregator]
  - A stolen npm token was used to publish 8 malicious Nx versions.
  - The postinstall script ran locally installed AI CLIs (`claude`, `gemini`, `q`) with `--dangerously-skip-permissions`, `--yolo` and `--trust-all-tools` to hunt for secrets.
  - Stolen data was published to public GitHub repos named `s1ngularity-repository`.
  - Reported scale varies by source; one says 2,300+ secrets, 225 organizations and 6,700+ repositories exposed.
  - Sources: [StepSecurity](https://www.stepsecurity.io/blog/supply-chain-security-alert-popular-nx-build-system-package-compromised-with-data-stealing-malware); [The Stack](https://www.thestack.technology/s1ngularity-nx-supply-chain-attack-github-aws-openai-keys-stolen/); [Semgrep](https://semgrep.dev/blog/2025/security-alert-nx-compromised-to-steal-wallets-and-credentials/); [OX Security](https://www.ox.security/blog/nx-supply-chain-breach-how-s1ngularity-weaponized-ai/)
- **Codex CLI**:
  - CVE-2025-61260 (v0.23.0 and earlier): project-local `.env` and `.codex/config.toml` MCP configs load without confirmation, so opening a repo can run its commands. [snippet] — [GitHub Advisory GHSA-xrxf-jgv3-qmrm](https://github.com/advisories/GHSA-xrxf-jgv3-qmrm)
  - Sandbox bypass GHSA-w5fx-fh39-j5rw (High, Sept 19, 2025). [primary] — [openai/codex advisories](https://github.com/openai/codex/security/advisories)
  - BeyondTrust: a command injection let attackers steal GitHub user access tokens and move laterally. Reported Dec 2025, patched by late Jan/Feb 2026. [snippet] — [Cybersecurity News](https://cybersecuritynews.com/openai-codex-command-injection-vulnerability/)
  - Cymulate (Windows): prompt injection delivered through a web search makes the agent plant a malicious Node runtime, which is later executed outside the sandbox via Windows executable search order. [snippet] — [Cymulate](https://cymulate.com/blog/codex-cli-rce-prompt-injection-mitigations/)
- **Claude Code**:
  - Feb 2026, Check Point via The Hacker News: CVE-2026-21852. A repo settings file pointing `ANTHROPIC_BASE_URL` at an attacker's endpoint exfiltrated API keys when Claude Code was started in that repo; RCE flaws were disclosed alongside. [snippet] — [The Hacker News](https://thehackernews.com/2026/02/claude-code-flaws-allow-remote-code.html)
  - Other 2026 CVEs [snippet]:
    - CVE-2026-24887: bypasses the confirmation prompt via `find`. — [SentinelOne](https://www.sentinelone.com/vulnerability-database/cve-2026-24887/)
    - CVE-2026-39861: injected context makes the agent create a symlink that escapes the sandbox; fixed in v2.1.64. — [SentinelOne](https://www.sentinelone.com/vulnerability-database/cve-2026-39861/)
    - CVE-2026-35020/35021/35022: OS command injection. — [SentinelOne](https://www.sentinelone.com/vulnerability-database/cve-2026-35021/)
  - Anthropic's own advisory list (page 1 of 4) [primary] — [anthropics/claude-code security advisories](https://github.com/anthropics/claude-code/security/advisories):
    - "Workspace Trust Dialog Bypass via Repo-Controlled Settings File" (High, Mar 18, 2026)
    - "Trust Dialog Bypass via Git Worktree Spoofing Allows Arbitrary Code Execution" (High, Apr 24, 2026)
    - "Out-of-Band Data Exfiltration via Pre-Approved HuggingFace Domain in WebFetch" (Moderate, Jun 13, 2026)
    - "Sandbox Escape via Git Worktree Path Confusion" (High, Jun 25, 2026)
    - A Claude Desktop/Cowork bug where opening a malicious file could run host commands (High, Sep 25, 2026)
- **Clinejection** (Feb 2026): [snippet]
  - Cline's Claude-based issue-triage GitHub Action had excessive permissions.
  - A prompt injection in an **issue title** gave the attacker command execution. From there, GitHub Actions cache poisoning led to theft of `VSCE_PAT`, `OVSX_PAT` and `NPM_RELEASE_TOKEN`.
  - An unauthorized Cline CLI 2.3.0 was published to npm and installed the OpenClaw agent globally on **about 4,000 machines** over about 8 hours.
  - Token rotation was incomplete: on Feb 9 the wrong npm token was revoked.
  - Sources: [Adnan Khan](https://adnanthekhan.com/posts/clinejection/); [Snyk](https://snyk.io/blog/cline-supply-chain-attack-prompt-injection-github-actions/); [The Hacker News](https://thehackernews.com/2026/02/cline-cli-230-supply-chain-attack.html)
- **RoguePilot** (Orca Security, Feb 2026): a passive prompt injection in a GitHub issue makes Copilot in Codespaces leak `GITHUB_TOKEN`, allowing repository takeover. [snippet] — [Orca](https://orca.security/resources/blog/roguepilot-github-copilot-vulnerability/); [The Hacker News](https://thehackernews.com/2026/02/roguepilot-flaw-in-github-codespaces.html)
- **Comment and Control** (disclosed Apr 15, 2026 by Aonan Guan, Zhengyu Liu and Gavin Zhong; CSA research note Apr 17, 2026): [snippet]
  - Payloads in PR titles, issue bodies, issue comments or HTML comments hijack three agents: Claude Code Security Review, Gemini CLI Action and the Copilot coding agent.
  - Each leaks its own credential (`ANTHROPIC_API_KEY`, `GEMINI_API_KEY`, `GITHUB_TOKEN`) back as an agent-written PR or issue comment. **The whole loop runs inside GitHub, with no external server.**
  - Copilot had three runtime mitigations: environment-variable filtering, secret scanning and a network firewall. All three were bypassed by reading the unfiltered parent process's environment with `ps auxeww`.
  - Rewards: Anthropic rated the finding CVSS 9.4 (bounty $100); Google paid $1,337; GitHub paid $500.
  - CSA's advice: treat PR titles, issue bodies and review comments as injection surfaces.
  - Sources: [CSA research note](https://labs.cloudsecurityalliance.org/research/csa-research-note-comment-control-github-prompt-injection-20/); [Cybersecurity News](https://cybersecuritynews.com/prompt-injection-via-github-comments/); [VentureBeat](https://venturebeat.com/security/ai-agent-runtime-security-system-card-audit-comment-and-control-2026); CSA follow-up, Aug 2026: [CSA](https://labs.cloudsecurityalliance.org/research/csa-research-note-ai-coding-agent-ci-prompt-injection-202608/)
- **GitSpawn** (Manifold Security, disclosed Sept 2, 2026): [snippet]
  - 8 flaws across 7 CLI agents: Claude Code, Codex, Cursor, goose, Hermes Agent, Qwen Code and Grok Build.
  - A repository's `.git/config` sets `core.fsmonitor`, which runs attacker commands when the agent automatically runs git. The command runs as the user, **outside the sandbox and without an approval prompt**.
  - Delivery only needs a repo copied with its `.git` intact: an archive, a shared drive, a sync folder or a USB stick.
  - Fixes shipped for goose, Claude Code and Cursor. Hermes Agent, Qwen Code, Grok Build and a second Claude Code path were still vulnerable at Manifold's Sept 1 retest.
  - Sources: [The Hacker News](https://thehackernews.com/2026/09/malicious-git-configs-can-make-claude.html); [AgentOffense](https://agentoffense.com/blog/malicious-git-config-ai-agents-rce-gitspawn/)
- Help Net Security (June 11, 2026), reporting on OWASP: prompt injection still drives most agentic-AI security failures in production. [snippet] — [Help Net Security](https://www.helpnetsecurity.com/2026/06/11/owasp-prompt-injection-ai-security-failures/)

**Frameworks and guidance**
- "Lethal trifecta" (Simon Willison, June 16, 2025): an agent is exploitable when it combines access to private data, exposure to untrusted content and the ability to communicate externally. [snippet] — [Simon Willison](https://simonwillison.net/2025/Jun/16/the-lethal-trifecta/)
- Meta "Agents Rule of Two" (Oct 31, 2025): within one session an agent should have no more than two of three properties: [A] processes untrustworthy inputs, [B] accesses sensitive systems or private data, [C] changes state or communicates externally. If a workflow needs all three, the agent should not run autonomously and needs human-in-the-loop approval or other reliable validation. [snippet] — [Meta AI](https://ai.meta.com/blog/practical-ai-agent-security/); [Simon Willison](https://simonwillison.net/2025/Nov/2/new-prompt-injection-papers/)
- OWASP Top 10 for Agentic Applications (first version Dec 2025): [snippet] — [OWASP GenAI](https://genai.owasp.org/resources/); [Teleport](https://goteleport.com/blog/owasp-top-10-agentic-applications/)
  - ASI01 Agent Goal Hijack
  - ASI02 Tool Misuse
  - ASI03 Identity & Privilege Abuse
  - ASI04 Agentic Supply Chain
  - ASI05 Unexpected Code Execution
  - ASI06 Memory & Context Poisoning
  - **ASI07 Insecure Inter-Agent Communication**
  - **ASI08 Cascading Failures**
  - **ASI09 Human-Agent Trust Exploitation**
  - ASI10 Rogue Agents

**Mitigations already implemented in products**
- **GitHub MCP server "lockdown mode"** [primary] — [github-mcp-server docs](https://github.com/github/github-mcp-server/blob/main/docs/server-configuration.md):
  - It "ensures the server only surfaces content in public repositories from users with push access to that repository".
  - It is "a best-effort content filter meant to reduce prompt-injection risk from untrusted repository content; it is not an authorization boundary". Withheld content may still be reachable through other tools.
  - Content from `github-actions[bot]` and `copilot` is always treated as safe.
  - A separate read-only mode disables all write tools.
- **GitHub Copilot cloud agent** [snippet of docs] — [GitHub Docs](https://docs.github.com/en/copilot/concepts/agents/cloud-agent/risks-and-mitigations):
  - The agent cannot mark its own PR "Ready for review", approve it or merge it.
  - **The user who asked Copilot to create the PR cannot approve it.**
  - Actions workflows do not run until a user with write access clicks "Approve and run workflows".
- **Anthropic Claude Code**:
  - Sandboxing (Oct 20, 2025): filesystem isolation plus network isolation so a compromised agent cannot modify sensitive files or exfiltrate data. [primary] — [Anthropic](https://www.anthropic.com/engineering/claude-code-sandboxing)
  - Auto mode (Mar 25, 2026): an input-layer probe adds a warning when a tool result looks like an injection attempt, and the classifier strips assistant text and tool results — "stripping tool results is the primary prompt-injection defense, since tool outputs are where hostile content enters the context". [primary] — [Anthropic](https://www.anthropic.com/engineering/claude-code-auto-mode)
- **Claude Code agent teams: messages from other agents are not treated as consent** [primary] — [Claude Code Docs](https://code.claude.com/docs/en/agent-teams):
  - The receiving agent is told a message "came from another Claude session, not from you".
  - "A teammate can't approve a permission prompt or supply consent on your behalf."
  - In auto mode, the classifier "treats an approval claim relayed from another agent as untrusted input rather than confirmation from you". It also reviews every inter-agent message before delivery: "A message it blocks never reaches the recipient."
- **Snyk / Invariant Labs**: Snyk acquired Invariant Labs (closed June 2025). Products: Invariant Guardrails, a runtime layer detecting PII, secrets and prompt injection; and MCP-scan with "Toxic Flow Analysis", which scans local MCP servers and toolsets for dangerous flows. [snippet] — [Snyk Labs](https://labs.snyk.io/resources/snyk-labs-invariant-labs/); [Snyk Toxic Flow Analysis](https://labs.snyk.io/resources/toxic-flow-analysis/); [BankInfoSecurity](https://www.bankinfosecurity.com/embargo-0624-9am-et-agentic-ai-security-gets-fuel-snyks-invariant-labs-buy-a-28789)
- Docker MCP Gateway is cited as an alternative way to lock down agent tool access. [aggregator] — [AI Learning Guides](https://ailearningguides.com/mcp-scan-vs-docker-mcp-gateway-2026)

### Inferences
- **Shared work items are the proven delivery channel for prompt injection.** An "accept before your agent sees it" gate is the same idea as GitHub's lockdown mode, which filters by the author's push access. But GitHub itself says this is "best-effort … not an authorization boundary". So the gate must be paired with least-privilege tools (what the agent can do after reading), and marketing should not present it as a complete defense.
- **The threat model of a private 2–5 person board is different from public-repo incidents.** The likely vectors are:
  - (a) external text a teammate pastes in, such as customer tickets, logs or web content;
  - (b) a teammate's agent that was injected elsewhere and relays the injection onto the board (OWASP ASI07/ASI08);
  - (c) supply-chain compromise of the MCP server or hook scripts themselves, as with Amazon Q, Nx and Clinejection.

  I found no in-the-wild case of (b) in a private team tool. It is a forward-looking risk; the risk in (a) and (c) is evidenced.
- **Read-then-write-back loops are an exfiltration path.** Comment and Control, the Supabase demo and the GitHub MCP flow all exfiltrated by writing into the same shared channel the attacker could read. A board where agents both read and post text has that same structure. Useful controls: keep secrets off the board, filter or redact agent-authored posts, label provenance (human vs agent, and whose agent), and rate-limit agent posting.
- **Hooks are code that runs on every member's machine.** GitSpawn and the config-file CVEs show that anything repo- or board-supplied which changes how tools run becomes a remote-code-execution vector. Board content must never configure hooks or MCP settings.
- **Requiring human sign-off for commitments has direct vendor precedent:**
  - GitHub's "the requester can't approve" rule and "Approve and run workflows" button;
  - Anthropic's rule that consent relayed by another agent is untrusted;
  - Meta's Rule of Two, which calls for human-in-the-loop when all three properties are present.

  A passkey confirmation for commitment actions is consistent with this guidance and is defensible to a security-minded buyer.

### Gaps
- I found **no public incident inside a private team planning tool** (Linear, Jira, Notion, Asana MCPs) where ticket text written by a teammate hijacked a coworker's agent. I did not specifically search Atlassian Rovo, Linear or Notion MCP incidents; that is worth a follow-up.
- Bounty, CVSS and scale numbers come mostly from secondary press, because the primary research blogs were blocked.
- No data on how widely GitHub lockdown mode, Snyk/Invariant guardrails or MCP gateways are adopted or how well they work.
- I could not fetch Simon Willison's original lethal-trifecta text, so the exact wording is not quoted.

---

## Q4. Human-in-the-loop expectations: do teams want agents to accept or claim work on their own, or require human sign-off? Any data on approval fatigue?

### Takeaway
Approval fatigue is measured, and vendors acknowledge it:
- **Claude Code users approve 93% of permission prompts.**
- Anthropic's answer is fewer prompts, not more: sandboxing cut prompts by 84%, and auto mode uses a classifier.
- Experienced users move from approving each action to monitoring and interrupting.

For commitments, the industry still keeps a human as the accountable party:
- Linear keeps the human as assignee when work is delegated to an agent.
- GitHub forbids both the agent and the person who requested it from approving the agent's PR, and requires a human to approve CI runs.

Two counter-signals: small-team users complain about the friction of GitHub's "requester can't approve" rule, and since Sept 1, 2026 GitHub lets Copilot approve PRs when admins enable it for specific scopes. **No survey directly measures whether teams want agents to claim teammates' work on their own.**

### Cited Findings
- "**Claude Code users approve 93% of permission prompts.**" (Anthropic, Mar 25, 2026) [primary] — [Anthropic, Claude Code auto mode](https://www.anthropic.com/engineering/claude-code-auto-mode)
  - A secondary article claims 97%; this **conflicts** with the primary figure. — [Gloss](https://gloss.run/post/you-were-approving-97-percent)
  - Search summaries of secondary coverage also claim auto mode "blocked 89% of harmful actions vs 13.6% for human review". I did not find this figure in the primary article; treat it as unverified. — [Tessl](https://tessl.io/blog/claude-code-gets-auto-mode-to-cut-approval-fatigue)
- Auto-mode classifier evaluation (full pipeline) [primary] — [Anthropic](https://www.anthropic.com/engineering/claude-code-auto-mode):
  - 0.4% false-positive rate on 10,000 real actions.
  - **17% false-negative rate on 52 real "overeager" actions**: "The 17% false-negative rate on real overeager actions is the honest number."
  - 5.7% false-negative rate on 1,000 synthetic exfiltration attempts.
  - The session is escalated to the human after 3 consecutive denials or 20 in total.
  - Anthropic's framing: "If you are manually approving every action carefully, it's arguably a regression."
- Sandboxing (Oct 20, 2025): "sandboxing safely reduces permission prompts by 84%". Approval fatigue is described as "users might not pay close attention to what they're approving, and in turn making development less safe." [primary] — [Anthropic](https://www.anthropic.com/engineering/claude-code-sandboxing)
- Anthropic, "Measuring AI agent autonomy in practice" (Feb 18, 2026) [primary] — [Anthropic](https://www.anthropic.com/research/measuring-agent-autonomy):
  - Full auto-approve is used in about 20% of sessions for new users (<50 sessions) and **over 40%** for experienced users (~750 sessions).
  - Interruptions rise from 5% of turns for new users to about 9% for experienced users.
  - On complex tasks, Claude asks for clarification more than twice as often as humans interrupt it.
  - "80% of tool calls come from agents that appear to have at least one kind of safeguard"; "73% appear to have a human in the loop in some way"; "only 0.8% of actions appear to be irreversible".
  - Anthropic recommends against requiring approval for every action, and calls for "new forms of post-deployment monitoring infrastructure".
- Claude Code still defaults to human approval; auto mode is an explicit opt-in (July 7, 2026). [snippet] — [Tech Times](https://www.techtimes.com/articles/319874/20260707/claude-code-defaults-human-approval-auto-mode-requires-explicit-opt.htm)
- Anecdote, title only: "I turned on auto-approve in Claude Code and broke CI in 30 minutes". — [dev.to](https://dev.to/kenimo49/i-turned-on-auto-approve-in-claude-code-and-broke-ci-in-30-minutes-1g1a)
- **Linear's delegation model** [snippet] — [Linear docs: assign and delegate](https://linear.app/docs/assigning-issues); [Linear Agent Interaction Guidelines](https://linear.app/developers/aig):
  - When an issue is delegated to an agent, the human stays the primary assignee and the agent is added as a contributor.
  - Rationale: an agent "cannot be held accountable", so final responsibility stays with a human.
  - The Agent Interaction Guidelines and SDK were published July 30, 2025.
- **GitHub Copilot cloud agent**: neither the agent nor the person who requested the PR can approve it, and workflows need human approval to run. [snippet] — [GitHub Docs](https://docs.github.com/en/copilot/concepts/agents/cloud-agent/risks-and-mitigations)
- **Friction from that rule** (GitHub community discussion, Nov 19, 2025; no staff response at the time of reading). [primary] — [GitHub Discussion #179997](https://github.com/orgs/community/discussions/179997)
  - GitHub's own message to the user: "Approvals from users that collaborated with Copilot on changes will not satisfy review requirements."
  - The user asks for "at least … an option to turn this off and allow the user to approve."
- **Copilot code review can now approve PRs** (GitHub changelog, Sept 1, 2026; public preview): [snippet]
  - Off by default, and configurable at enterprise, organization and repository level. Repository admins can limit which file paths Copilot may approve.
  - An "approval assessment" alone does not count toward merge requirements.
  - Commentators urge keeping an independent human gate.
  - Sources: [GitHub Changelog](https://github.blog/changelog/2026-09-01-copilot-code-review-can-now-approve-pull-requests/); [DevOps.com](https://devops.com/github-puts-copilot-in-the-approval-seat-for-pull-requests/); [General Analysis guide](https://generalanalysis.com/guides/github-copilot-pull-request-approvals)
- **Claude Code agent teams: autonomy among one person's agents** [primary] — [Claude Code Docs](https://code.claude.com/docs/en/agent-teams):
  - Teammates can **self-claim**: "after finishing a task, a teammate picks up the next unassigned, unblocked task on its own". File locking prevents two teammates claiming the same task.
  - Plan approvals are granted by the lead "without the lead reviewing it".
  - Claude Code "doesn't ask you to confirm the launch" of teammates.
  - Teammates' permission prompts all surface in the lead's session, which the docs call friction.
- The Rule of Two calls for human-in-the-loop approval when an agent has untrusted input, sensitive access and the ability to change state all at once. [snippet] — [Meta AI](https://ai.meta.com/blog/practical-ai-agent-security/)
- At Anthropic, more than half of engineers say they can "fully delegate" only 0–20% of their work. [primary] — [Anthropic](https://www.anthropic.com/research/how-ai-is-transforming-work-at-anthropic)

### Inferences
- **Autonomy is accepted inside one person's own agents; commitments to other people stay human.** Vendors ship self-claiming among one person's agents. Accountability across people stays with humans: Linear keeps the human as assignee, and GitHub requires human approvals. That supports a design where agents can propose a claim, draft an assignment or suggest a blocker, and the accountable human confirms it.
- **A confirmation that fires often stops being a real check.** Approval rates of 93%, plus Anthropic's own position that careful per-action approval is close to a regression, show that frequent passkey prompts would be clicked through on reflex. Keep the passkey for rare, high-consequence actions. Only 0.8% of agent actions are irreversible, which suggests commitment actions can be rare. Show provenance and a diff at the moment of confirmation.
- **Small teams resent "independent approver" rules** (Discussion #179997). For a 2–5 person team, the useful middle ground is: the accountable human can confirm their own agent's proposal with a passkey, but no agent can confirm for itself or for another agent.
- **The market is moving toward agent autonomy scoped by policy** (Copilot approvals limited by path, auto-mode classifiers). Per-action policies (e.g., agents may auto-post progress; humans confirm claims, assignments and accepting outside text) fit that direction.

### Gaps
- No survey on whether teams want agents to accept or claim tasks from teammates on their own.
- No data on fatigue from passkey/WebAuthn-style confirmations specifically, or on approval rates for team-level actions (claim, assign) as opposed to tool-level actions.
- No primary data on how widely Copilot's new auto-approval is adopted.

---

## Q5. Willingness to pay: per-seat prices of dev-team tools in 2026, and any evidence of paying for agent coordination or observability

### Takeaway
2026 per-seat price anchors:

| Category | Product | Price per user per month |
|---|---|---|
| Work tracker | Jira Standard / Premium | $7.91 / $14.54 |
| Work tracker | Linear Basic / Business | $10 / $16 |
| AI coding, standard seat | Copilot Business / Enterprise | $19 / $39 |
| AI coding, standard seat | Claude Team Standard | $20–25 |
| AI coding, standard seat | ChatGPT Business (includes Codex) | $20–25 |
| AI coding, standard seat | Cursor Teams Standard | $40 |
| AI coding, premium seat | Claude Team Premium, ChatGPT Business Premium | $100–125 |
| AI coding, premium seat | Cursor Teams Premium | $120 |

Multi-agent tracking is being **bundled into these subscriptions** (GitHub Agent HQ mission control, Cursor Teams analytics, Claude Code agent teams). I found no disclosed pricing or revenue for a standalone agent-coordination board, so willingness to pay for that category is **unproven**.

### Cited Findings
- **Linear:** Free; Basic $10; **Business $16 per user per month** (annual). A 5-user Business team costs $80/month. [aggregator] — [costbench](https://costbench.com/software/developer-tools/linear/); [aiproductivity.ai](https://aiproductivity.ai/blog/linear-pricing/)
- **Jira Cloud** [aggregator] — [automationatlas](https://automationatlas.io/answers/jira-pricing-explained-2026/); [costbench](https://costbench.com/software/project-management/jira/):
  - Free for up to 10 users.
  - Standard $7.91 and Premium $14.54 per user per month (annual list price). Monthly billing is about $8.15 / $15.25.
  - Enterprise is custom-quoted.
- **GitHub Copilot** [aggregator] — [CloudZero](https://www.cloudzero.com/blog/github-copilot-cost/); [agentmarketplace.ai](https://agentmarketplace.ai/github-copilot-enterprise-pricing):
  - **Business $19, Enterprise $39** per user per month. Enterprise requires GitHub Enterprise Cloud (about $21/user), so the real floor is about $60.
  - Since June 1, 2026, billing is in GitHub AI Credits: 1,900 (Business) or 3,900 (Enterprise) included per seat, pooled across the company, $0.01 per extra credit.
  - Promotional credits ended Aug 31, 2026.
- **GitHub Agent HQ:** the Claude and Codex agents are a public preview for Copilot Pro+ and Enterprise; each agent session consumes one premium request (Feb 2026). [snippet] — [ChannelLife](https://channellife.com.au/story/github-adds-claude-codex-agents-to-unified-ai-hub)
- **Claude Team** [aggregator; vendor page not fetched] — [Justin McKelvey](https://justinmckelvey.com/blog/claude-team-plan); [Tygart Media](https://tygartmedia.com/claude-team-pricing-2026-standard-premium-seats/); [aipricing.guru](https://www.aipricing.guru/subscriptions/claude-team-premium/):
  - Standard seat $20 (annual) / $25 (monthly).
  - **Premium seat $100 (annual) / $125 (monthly)**, with about 6.25x Pro usage.
  - Minimum 2 seats, maximum 150. Every seat includes Claude Code, and seat types can be mixed.
- **ChatGPT Business (includes Codex)** [snippet] — [OpenAI Help Center](https://help.openai.com/en/articles/8792536-managing-billing-and-seats-in-chatgpt-business); [OpenAI, Codex flexible pricing for teams](https://openai.com/index/codex-flexible-pricing-for-teams/); [Codex pricing](https://developers.openai.com/codex/pricing):
  - Standard seats $25 (monthly) / $20 (annual), including ChatGPT and Codex.
  - Premium seats $100 (annual) / $125 (monthly).
  - As of June 24, 2026, new Business workspaces can no longer add standalone Codex-only seats.
  - OpenAI also offers pay-as-you-go Codex pricing for teams.
- **Cursor Teams** (from June 1, 2026) [aggregator] — [NxCode](https://www.nxcode.io/resources/news/cursor-ai-pricing-plans-guide-2026); [LowCode Agency](https://www.lowcode.agency/blog/cursor-ai-pricing):
  - **Standard $40**, Premium $120 per user per month (5x the usage at 3x the price). Annual billing takes 20% off ($32 Standard).
  - Includes usage analytics, a team marketplace for shared rules and skills, agentic code reviews and SSO.
- **Coordination costs tokens:** Claude Code agent teams "use significantly more tokens than a single session", and usage "scales with the number of active teammates". [primary] — [Claude Code Docs](https://code.claude.com/docs/en/agent-teams)
- Cost anxiety (title only): "Ask HN: How are you keeping AI coding agents from burning money?" — [HN 47559293](https://news.ycombinator.com/item?id=47559293)
- Funding signal for human-agent "multiplayer" collaboration (general business agents, not coding-specific): Dust raised $40M in May 2026, positioned as "multiplayer AI for human-agent collaboration". [aggregator] — [AI Agents Directory](https://aiagentsdirectory.com/news/ai-agents-news-brief-funding-orchestration-and-security-concerns-dominate); [Dust](https://dust.tt/)
- Signal that buyers pay for agent security: Snyk bought Invariant Labs (June 2025) to sell agent and MCP security. Separately, Snyk reported revenue above $300M and laid off 200+ employees (reported Oct 1, 2026). [snippet] — [BankInfoSecurity](https://www.bankinfosecurity.com/embargo-0624-9am-et-agentic-ai-security-gets-fuel-snyks-invariant-labs-buy-a-28789); [Tech.eu](https://tech.eu/2026/10/01/snyk-laid-off-over-200-employees-revenues-top-300m)

### Inferences
- **Budget exists, but bundled features compete with any standalone product.** A 5-person team spends about $100–200/month on standard AI seats, or $500–625/month on premium seats, and about $40–80/month on a tracker. A coordination board priced like a tracker ($8–16 per user) would be under roughly 10–15% of a premium team's AI spend. But incumbents bundle multi-agent tracking at no extra cost, so a standalone product has to sell what the bundles don't cover:
  - coordination across several humans, not just one person's agents;
  - coordination across vendors (Claude Code and Codex together);
  - the injection gate plus human-confirmed commitments.
- AI vendors charge per seat and per agent session or credit (Copilot AI Credits, Agent HQ premium requests, premium seats). None charges separately for coordination UI, which suggests buyers see it as a feature rather than a product. That is a risk for a standalone tool.
- The free tiers of Jira (up to 10 users) and Linear set expectations that a 2–5 person team pays $0 for basic tracking. Monetization may need to sit on security and governance features (passkey audit trail, provenance, policy), which security buyers already show willingness to pay for (Snyk/Invariant). This is an inference only; it has not been tested with buyers.

### Gaps
- No public data on willingness to pay specifically for agent coordination or observability, and no disclosed pricing for standalone multiplayer coding-agent boards found in this pass. Competitor pricing is assumed to be covered by another workstream.
- Every price above comes from aggregators or snippets, because vendor pricing pages were not fetched or were blocked. Verify on the vendor pages before publishing. Aggregators also disagree on Claude Team premium pricing over time.
- No data on budgets or price sensitivity of China+US cross-border small teams (out of scope per brief).
