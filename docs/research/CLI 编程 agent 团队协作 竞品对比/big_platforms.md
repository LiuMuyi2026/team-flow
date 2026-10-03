# Big platforms for "humans + their coding agents as one team" (state as of 2026-10-03)

Confidence legend used on every bullet: **[P]** = primary page fetched and read in full this session (code.claude.com, claude.com docs, GitHub Docs source markdown on raw.githubusercontent.com, GitHub community discussions/issues). **[S]** = search-engine snippet only; the page itself was blocked by the egress proxy (github.blog, docs.github.com, linear.app, atlassian.com, cursor.com, openai.com, developers.openai.com, slack.com, notion.com, Microsoft and Google blogs were all blocked), so treat as lower confidence. **[S-agg]** = snippet from an aggregator / third-party blog, lowest confidence. The session's web-search budget ran out near the end, so a few dates could not be cross-checked; they are listed under Gaps.

## 1. GitHub: Copilot cloud agent, Agent HQ (Claude + Codex), Issues/Projects, integrations, MCP server

### Takeaway
GitHub ships the most complete *cross-vendor* "assign a work item to an agent" surface: since Feb 2026 an issue can be assigned to Copilot, Claude or Codex (third-party agents still **public preview** as of Oct 2026), sessions are tracked in an Agents tab/panel, and enterprises get an agent control plane (GA 2026-02-26). Its human-approval model is strong at the code boundary (write-access-only triggers, non-writer comments hidden from the agent, workflow approval, human merge, extra approval for app-identity PRs), but there is no claim / blocker / ask-for-help semantics, and every agent run is a GitHub-hosted cloud session, not an engineer's local Claude Code or Codex CLI session.

### Cited Findings
**What ships, with dates**
- Copilot coding agent: GitHub's announcement discussion (created 2025-05-13, marked "Discussion updated: 09-25-2025") now reads "Copilot coding agent ... is now **generally available** for all paid Copilot subscribers" [P] — [GitHub community #159068](https://github.com/orgs/community/discussions/159068)
- Renamed **Copilot cloud agent** in April 2026; the usage-metrics API added `used_copilot_cloud_agent`, keeping `used_copilot_coding_agent` until 2026-08-01 [S] — [GitHub Changelog 2026-04-23](https://github.blog/changelog/2026-04-23-copilot-cloud-agent-fields-added-to-usage-metrics/). Since 2026-04-01 it can research, plan and code on a branch before opening a PR ("no longer limited to pull-request workflows") [S] — [GitHub Changelog 2026-04-01](https://github.blog/changelog/2026-04-01-research-plan-and-code-with-copilot-cloud-agent/); current docs confirm research → plan → branch changes → PR, and that deep research/planning is "only available ... on GitHub.com, and in public preview for the Microsoft Teams and Slack integrations" [P] — [GitHub Docs source: About Copilot cloud agent](https://raw.githubusercontent.com/github/docs/main/content/copilot/concepts/agents/cloud-agent/about-cloud-agent.md)
- **Agent HQ** was announced at Universe on 2025-10-28 as "mission control" for agents from Anthropic, OpenAI, Google, Cognition and xAI [S] — [Visual Studio Magazine](https://visualstudiomagazine.com/articles/2025/10/28/github-introduces-agent-hq-to-orchestrate-any-agent-any-way-you-work.aspx), [The New Stack](https://thenewstack.io/github-agent-hq/)
- Claude and Codex went into **public preview** on GitHub on 2026-02-02 for Copilot Pro+ and Enterprise, then on 2026-02-26 "now also available for Copilot Business and Pro subscribers". Each session consumed one premium request during the preview [P] — [GitHub community #186179](https://github.com/orgs/community/discussions/186179)
- As of the current docs, "Third-party coding agents are currently in public preview", and the only supported third-party agents are **Anthropic Claude and OpenAI Codex**. Pro / Pro+ / **Max** subscribers enable them in personal policies; Business/Enterprise enable them in org/enterprise policies [P] — [GitHub Docs source: About third-party coding agents](https://raw.githubusercontent.com/github/docs/main/content/copilot/concepts/agents/about-third-party-coding-agents.md)
- Entry points: the Agents tab, **assigning an agent to an existing issue**, `@AGENT_NAME` in a PR comment, GitHub Mobile, VS Code (start a session or delegate an existing session to another agent) [P] — [same doc](https://raw.githubusercontent.com/github/docs/main/content/copilot/concepts/agents/about-third-party-coding-agents.md). One issue can be assigned "to Claude, Codex, Copilot, or all three" to compare drafts [S] — [GitHub Blog "Pick your agent"](https://github.blog/news-insights/company-news/pick-your-agent-use-claude-and-codex-on-agent-hq/)
- Enabling a partner agent installs a GitHub App ("anthropic code agent" / "openai code agent"). Its actions appear in the audit log, but the app is not listed among installations. Third-party agent output is scanned automatically with CodeQL, secret scanning, and Advisory Database checks on new dependencies, with no GHAS license needed [P] — [About third-party coding agents](https://raw.githubusercontent.com/github/docs/main/content/copilot/concepts/agents/about-third-party-coding-agents.md)
- **Enterprise AI Controls & agent control plane: GA 2026-02-26.** Admins set security policies and audit logging, choose which agents are allowed, control model access, and see usage metrics [S] — [GitHub Changelog 2026-02-26](https://github.blog/changelog/2026-02-26-enterprise-ai-controls-agent-control-plane-now-generally-available/)
- Integrations with Microsoft Teams, Slack, Linear, Azure Boards and Jira [P] — [GitHub Docs source: About Copilot integrations](https://raw.githubusercontent.com/github/docs/main/content/copilot/concepts/tools/about-copilot-integrations.md). Dates:
  - Teams app GA around 2025-09-19 [P] — [community #177494](https://github.com/orgs/community/discussions/177494)
  - Slack and Linear public preview 2025-10-20 [P] — [community #177494](https://github.com/orgs/community/discussions/177494)
  - Linear GA 2026-07-23 [S] — [GitHub Changelog](https://github.blog/changelog/2026-07-23-copilot-cloud-agent-for-linear-is-now-generally-available/)
  - Azure Boards public preview 2025-09-18 [S] — [GitHub Changelog](https://github.blog/changelog/2025-09-18-assign-azure-boards-work-items-to-copilot-coding-agent-in-public-preview/)
- New **shared** Slack and Teams experiences shipped 2026-08-21 in public preview [S] — [Slack changelog](https://github.blog/changelog/2026-08-21-the-new-github-copilot-experience-in-slack/), [Teams changelog](https://github.blog/changelog/2026-08-21-shared-agentic-work-with-github-copilot-in-microsoft-teams/)
- A 2026-09-25 update (public preview, Copilot Business/Enterprise) lets Copilot read Slack files, attachments and message links, plus Teams inline images, forwarded messages, and channel/thread history [S] — [GitHub Changelog 2026-09-25](https://github.blog/changelog/2026-09-25-updates-to-github-copilot-for-slack-and-microsoft-teams/)

**Team visibility / handoff**
- The agents panel/page shows "Sessions that you started, or that another user prompted Copilot to work on". A session log shows reasoning, tools used, token usage and session length. You can steer with follow-up prompts, stop a session (pushed commits are kept), or archive it [P] — [GitHub Docs source: Managing agent sessions](https://raw.githubusercontent.com/github/docs/main/content/copilot/how-tos/copilot-on-github/use-copilot-agents/manage-and-track-agents.md)
- Commits are "authored by Copilot, with the person who started the task listed as co-author", and each commit message links to the session log [P] — [same doc](https://raw.githubusercontent.com/github/docs/main/content/copilot/how-tos/copilot-on-github/use-copilot-agents/manage-and-track-agents.md)
- Handoff is built into the design: "Copilot cloud agent can start a task, which you then pick up and continue working on yourself" [P] — [About Copilot cloud agent](https://raw.githubusercontent.com/github/docs/main/content/copilot/concepts/agents/cloud-agent/about-cloud-agent.md)
- **Slack:** in a DM, Copilot acts with your linked personal GitHub permissions. In a shared thread or channel it creates artifacts "under its app identity". "Only users with **write** access to a repository can trigger Copilot to make changes, but any conversation participant can provide input". Workspace guests and outside collaborators cannot start or steer a session. Each task gets a dedicated "Slack Code" code channel, one channel per task [P] — [GitHub Docs source: Slack integration](https://raw.githubusercontent.com/github/docs/main/content/copilot/how-tos/copilot-integrations/integrate-cloud-agent-with-slack.md)
- **Jira:** progress streams into Jira's chat panel, and "The user who initiated the agent session can view progress there". A follow-up `@Copilot` on the work item starts a new session and a *new* PR. Requirements: Jira must be an AI-enabled app with Rovo activated, and installation needs a Jira site admin plus a GitHub org owner. Jira context copied into a PR "is visible to everyone if the repository is public" [P] — [GitHub Docs source: Jira integration](https://raw.githubusercontent.com/github/docs/main/content/copilot/how-tos/copilot-integrations/integrate-cloud-agent-with-jira.md)
- **Linear:** an org owner who is also a Linear workspace admin installs the app once, after which any org member can connect. Linear's workspace/team "agent guidance" prompt is passed to Copilot on every trigger [P] — [GitHub Docs source: Linear integration](https://raw.githubusercontent.com/github/docs/main/content/copilot/how-tos/copilot-integrations/integrate-cloud-agent-with-linear.md)

**Approval / permission model**
- Only users with write access can trigger the agent, and "Comments from users without write access are never presented to the agent". Hidden characters are filtered. Workflows do not run until a write-access user clicks "Approve and run workflows". The agent cannot mark its PR "Ready for review", approve, or merge [S] — [GitHub Docs: Risks and mitigations](https://docs.github.com/en/copilot/concepts/agents/cloud-agent/risks-and-mitigations)
- PRs created by Copilot from a shared Slack/Teams context carry the app identity, so "one more approval is required before merging, as long as the repository already requires at least one approval. This is enabled by default" (rulesets) [P] — [GitHub Docs reusable](https://raw.githubusercontent.com/github/docs/main/data/reusables/copilot/cloud-agent/unattributed-additional-approval-note.md)
- Limits: one repository per run; one branch and exactly one PR per task; a **59-minute** hard session limit; incompatible rulesets or branch protections block the agent [P] — [About Copilot cloud agent](https://raw.githubusercontent.com/github/docs/main/content/copilot/concepts/agents/cloud-agent/about-cloud-agent.md)

**Pricing**
- The cloud agent is "available for all paid Copilot plans". It consumes **GitHub Actions minutes and AI Credits**, depending on model and tokens, and third-party agents bill the same way [P] — [About Copilot cloud agent](https://raw.githubusercontent.com/github/docs/main/content/copilot/concepts/agents/cloud-agent/about-cloud-agent.md), [About third-party coding agents](https://raw.githubusercontent.com/github/docs/main/content/copilot/concepts/agents/about-third-party-coding-agents.md)
- Aggregators report the switch from premium-request counting to AI Credits on 2026-06-01, with plans Free, Pro $10, Pro+ $39, **Max $100**, Business $19/seat and Enterprise $39 [S-agg] — [usagebox](https://usagebox.com/articles/github-copilot-usage-based-billing-2026), [aicodingdir](https://aicodingdir.com/blog/github-copilot-pricing-guide-2026/). The Max tier and AI Credits are confirmed by the docs' wording [P] (same docs as above). One commentator notes that the Slack/Teams preview "sandbox bills" [S-agg] — [Digital Applied](https://www.digitalapplied.com/blog/github-copilot-slack-teams-public-preview-sandbox-billing)

**GitHub MCP server and prompt injection through shared items**
- **Lockdown mode** "ensures the server only surfaces content in public repositories from users with push access to that repository". It is "a best-effort content filter ... it is not an authorization boundary". Content from `github-actions[bot]` and `copilot` is always treated as safe. Enable it with the `X-MCP-Lockdown: true` header or `--lockdown-mode`; once an operator enables it server-side, a header cannot disable it. There is also a **read-only mode**, plus toolsets and excluded tools [P] — [github-mcp-server docs/server-configuration.md](https://github.com/github/github-mcp-server/blob/main/docs/server-configuration.md)
- A lockdown-mode flaw (GHSA-pjp5-fpmr-3349 / CVE-2026-48529, Medium) let an HTTP-mode singleton reuse the first user's GraphQL client for every user's trust checks. It affected versions ≥0.22.0 and <1.1.2 and is fixed in 1.1.2 [S] — [github/github-mcp-server](https://github.com/github/github-mcp-server). Tool-specific configuration arrived on 2025-12-10 [S] — [GitHub Changelog](https://github.blog/changelog/2025-12-10-the-github-mcp-server-adds-support-for-tool-specific-configuration-and-more/)
- Invariant Labs (May 2025) showed that a malicious issue in a public repo can hijack an agent using the GitHub MCP server into leaking private-repo data [S] — [Docker blog](https://www.docker.com/blog/mcp-horror-stories-github-prompt-injection/), [Cybernews](https://cybernews.com/security/github-mcp-vulnerability-has-far-reaching-consequences/)
- **"Comment and Control"** (disclosed 2026-04-16, CVSS 9.4 per the researcher) hit three agents:
  - The Copilot coding agent ran instructions hidden in an **HTML comment inside an issue**, which is invisible when the Markdown is rendered, once a victim assigned that issue to Copilot.
  - Claude Code Security Review and the Gemini CLI Action were hijacked through PR titles and issue comments.
  - Bounties paid were Anthropic $100, Google $1,337 and GitHub $500, and GitHub classified the issue as a "known architectural limitation".

  [P, secondary case study] — [vectara/awesome-agent-failures case study](https://raw.githubusercontent.com/vectara/awesome-agent-failures/main/docs/case-studies/comment-and-control-prompt-injection.md); original write-up [S] — [oddguan.com](https://oddguan.com/blog/comment-and-control-prompt-injection-credential-theft-claude-code-gemini-cli-github-copilot/)

### Inferences
- GitHub is the only place today where **Claude and Codex can both be assigned work items natively alongside humans**. They run as GitHub-hosted cloud agents billed to the Copilot plan (Actions minutes + AI Credits), not on the engineer's own Claude or ChatGPT seat and not as their local CLI session. A teammate's local Claude Code or Codex CLI work stays invisible in Agent HQ.
- The model is "agent = assignee, the human who triggered = co-author". Nothing marks "this is Alice's agent working on Alice's claimed task", and nothing stops one person's agent from being pointed at work a teammate already owns.
- Session visibility is per-person (sessions you started or prompted). Team-wide oversight is the Enterprise control plane and metrics, which is overkill and unaffordable for 2–5 people.
- There is no blocker or ask-for-help primitive: people fall back on issue comments, labels and Slack.
- Approval sits at merge, workflow and permission time ("agent can't approve or merge"). Nothing gates commitment actions such as accepting a task or reassigning someone else's.
- The injection defense keys on repository write access, so in a 2–5 person private repo where everyone has write access it filters nothing. The HTML-comment bypass shows the hidden-content filtering was not airtight as of April 2026.

### Gaps
- github.blog and docs.github.com were blocked, so many changelog dates are snippet-level. The "risks and mitigations" page could not be fetched (raw path 404).
- No confirmed date for Azure Boards GA, and no information on whether third-party agents will reach GA (possibly at Universe 2026, which is after 2026-10-03).
- No evidence found of agent-specific views in **GitHub Projects** (e.g., an agent-sessions column) beyond assigning Copilot as the assignee.
- Copilot and Agent HQ availability for mainland-China developers was not researched.

## 2. Linear: agents, delegation, agent sessions, Linear Agent "coding sessions"

### Takeaway
Linear has the most deliberate human/agent model: **issues are assigned to humans and only delegated to agents**, so a human stays accountable, and agent sessions show live state. Third-party agents (Codex, Cursor, Copilot and others) can be delegated, and since 2026-06-11 Linear's own Linear Agent writes code by running Claude Code or Codex in a cloud sandbox. There is still no Anthropic-built Claude Code delegate agent, no approval gate beyond PR review, and Linear's site was unreachable, so confidence is lower.

### Cited Findings
- "Instead of assigning issues to agents as you would to human teammates, you delegate to them... the issue still has a human assignee—someone accountable for the result—but it also has a delegated agent". "Issues can only be assigned to humans, and only delegated to agents... an agent cannot be held accountable" [S] — [Linear Docs: Assign and delegate issues](https://linear.app/docs/assigning-issues), [Agent Interaction Guidelines](https://linear.app/developers/aig)
- The Agent Session "tracks the lifecycle of a given agent task. Sessions are created automatically when an agent is mentioned or delegated an issue", and "Session state is visible to users, and updated automatically based on the agent's emitted activities" [S] — [Linear Developers: Agents](https://linear.app/developers/agents). The guidelines and SDK were published on 2025-07-30 [S] — [Linear changelog](https://linear.app/changelog/2025-07-30-agent-interaction-guidelines-and-sdk)
- **Codex in Linear** launched 2025-12-04 [S] — [Linear changelog](https://linear.app/changelog/2025-12-04-openai-codex-agent). "Assign an issue to Codex or mention @Codex in a comment, and Codex creates a cloud [task] and replies with progress and results" [S] — [OpenAI Developers: Codex in Linear](https://developers.openai.com/codex/integrations/linear)
- **Cursor:** delegate issues to Cursor or mention @Cursor. Connecting requires a Cursor admin. Inline `[repo=…] [model=…] [branch=…]` syntax configures a run [S] — [Cursor Docs: Linear](https://cursor.com/docs/integrations/linear)
- **GitHub Copilot:** public preview 2025-10-20 [P] — [community #177494](https://github.com/orgs/community/discussions/177494); GA 2026-07-23 [S] — [GitHub Changelog](https://github.blog/changelog/2026-07-23-copilot-cloud-agent-for-linear-is-now-generally-available/). Linear "agent guidance", a prompt set at workspace or team level, is passed to the agent automatically [P] — [GitHub Docs source: Linear integration](https://raw.githubusercontent.com/github/docs/main/content/copilot/how-tos/copilot-integrations/integrate-cloud-agent-with-linear.md)
- "Deeplink to AI coding tools" shipped 2026-02-26 (title only seen) [S] — [Linear changelog](https://linear.app/changelog/2026-02-26-deeplink-to-ai-coding-tools)
- **Linear Agent** entered public beta for all teams on 2026-03-24 with skills and automations; "Code Intelligence" was announced as coming [S] — [Linear changelog: Introducing Linear Agent](https://linear.app/changelog/2026-03-24-introducing-linear-agent)
- **Coding sessions** shipped 2026-06-11 [S] — [Linear changelog](https://linear.app/changelog/2026-06-11-coding-sessions), [Linear Docs: Coding sessions](https://linear.app/docs/coding-sessions), [linear.app/coding-sessions](https://linear.app/coding-sessions):
  - "When you delegate an issue to Linear, we start a secure coding session through Claude Code or Codex".
  - Linear drafts a PR, puts the diff on the issue, and you can merge from Linear.
  - A session starts from assignment, chat, a comment, or a **Slack thread**, and runs in a cloud sandbox that can run apps, use browser automation, and capture screenshots.
  - Available on **Basic, Business and Enterprise** plans; requires a GitHub connection with code access and uses **AI credits**.
- Coding sessions reached mobile on 2026-07-30 [S] — [Linear changelog](https://linear.app/changelog/2026-07-30-coding-sessions-on-mobile). Agent-assisted editing and "Loops" (recurring agent workflows) shipped around 2026-07-23 [S] — [Linear changelog](https://linear.app/changelog/2026-07-23-agent-assisted-editing)
- **No native Claude Code delegate in Linear:** the feature request anthropics/claude-code#12925 ("Assign issues to Claude Code to trigger cloud agent sessions") was opened 2025-12-03 and is still open with no maintainer response [P] — [GitHub issue #12925](https://github.com/anthropics/claude-code/issues/12925). An aggregator also says there was no native integration as of July 2026 [S-agg] — [aidenapp.org](https://aidenapp.org/linear-claude-code)
- Anthropic's **Claude Tag** can connect to Linear through a dedicated account token "so it can file tickets and post status updates" [P] — [claude.com docs index (llms.txt)](https://claude.com/docs/llms.txt). Google Jules gained an MCP connection to Linear on 2026-02-02 [S] — [Jules changelog](https://jules.google/docs/changelog/2026-02-02/)

### Inferences
- Linear's assignee-vs-delegate split is the closest big-platform analogue to Longtable's rule that the person stays accountable and confirms commitments. It is a data-model distinction, though, not a confirmation gate: anyone allowed to delegate can kick off an agent.
- "Coding sessions" put Claude Code and Codex *inside Linear's cloud*, billed through Linear AI credits. They do not connect each engineer's own Claude or ChatGPT subscription, local repo, or CLI hooks to the board.
- A mixed Claude Code + Codex team gets first-party Codex delegation and Claude only through Linear Agent or a user-configured MCP. The asymmetry is the opposite of GitHub's, where both are first-class.

### Gaps
- linear.app was blocked, so the following could not be checked:
  - whether agents can change status or assignee without human confirmation;
  - any per-agent permission scopes;
  - Linear MCP server details (launch date, write scopes);
  - AI-credit prices;
  - any filtering of untrusted comment text before it reaches agents (no source found).

## 3. Atlassian: Jira + Rovo / Rovo Dev, agents in Jira, third-party coding agents, Rovo MCP server

### Takeaway
Through 2026 Jira repositioned itself as the control plane for humans and agents. Agents can be assignees (open beta 2026-02-25; reported GA around May 2026). On 2026-07-15 Atlassian added assignment to **Claude Code, Cursor and GitHub Copilot**, a built-in Jira Coding Agent, agent sessions in Jira, and automation routing, at no extra cost on paid Jira Cloud, with Codex "forthcoming". Third-party agents in Jira Automation are still beta. The stack is heavyweight and needs Rovo/AI activation, and prompt injection through tickets has been demonstrated.

### Cited Findings
- Atlassian opened a beta of "agents in Jira" on 2026-02-25, letting teams "assign tasks, set deadlines and track progress for AI agents from the same interface used to manage human workers" [S] — [TechInformed](https://techinformed.com/atlassian-adds-ai-agents-to-jira-under-existing-permissions/), [Atlassian Community: Introducing Agents in Jira](https://community.atlassian.com/forums/Jira-articles/Introducing-Agents-in-Jira/ba-p/3194583). "An agent shows up as an assignee, with the same fields and patterns your teams already know". You can "assign the agent to a work item or trigger the agent as work moves through your workflow" [S] — [Atlassian blog](https://www.atlassian.com/blog/rovo/ai-agents-in-jira), [Atlassian Support](https://support.atlassian.com/jira-software-cloud/docs/collaborate-on-work-items-with-ai-agents/)
- Reported "generally available ... with full audit trails and governance controls" for Rovo or third-party MCP-enabled agents (GA cited as May 2026 for Standard/Premium/Enterprise) [S-agg] — [UC Today](https://www.uctoday.com/project-management/why-your-next-jira-assignee-might-not-be-human/). Named partners include Box, Canva, Cursor, GitHub, Databricks and Cognition [S] (same search; [Atlassian blog](https://www.atlassian.com/blog/rovo/ai-agents-in-jira))
- **2026-07-15:** assign Jira work items to Claude Code, Cursor and GitHub Copilot; a built-in **Jira Coding Agent**; **agent sessions in Jira**; agent automations; agentic templates; Jira for Slack; and a DX report tracking AI spend per PR. "available today for paid Jira Cloud customers at no additional cost" [S] — [SiliconANGLE 2026-07-15](https://siliconangle.com/2026/07/15/atlassian-evolves-jira-orchestration-hub-developers-ai-agents/), [Futurum](https://futurumgroup.com/insights/atlassian-fuses-the-agent-work-surface-workflow-and-control-plane-into-jira/). Support for OpenAI Codex is "forthcoming" [S] — [DevOps.com](https://devops.com/atlassian-extends-ai-reach-of-jira-into-agentic-engineering-workflows/)
- Jira Automation can trigger GitHub Copilot, Cursor or Claude as a rule step, passing the full work-item context. The doc says "This experience is currently in beta" [S] — [Atlassian Support: third-party coding agents in Jira automation](https://support.atlassian.com/jira-software-cloud/docs/use-third-party-coding-agents-in-jira-automation/), [Atlassian Community](https://community.atlassian.com/forums/Jira-articles/New-Put-your-coding-agents-to-work-with-Jira-Automation/ba-p/3268918). There is also an "Introducing Claude Agent for Jira" post and an "Automation: Claude agent action" release note, dates not confirmed [S] — [Atlassian blog](https://www.atlassian.com/blog/company-news/claude-agent-for-jira), [release note](https://community.atlassian.com/release-notes/6pIgj1TiuOGxWVopdZBkUe)
- **Rovo Dev** runs inside Jira, moving routine work (security patches, dependency migrations, feature-flag cleanups) "from task item to merge-ready PR in the background" [S] — [Jira Spring 2026 release](https://www.atlassian.com/software/jira/release). Rovo Dev GA was announced on the community forum (date not verified) [S] — [Atlassian Community](https://community.atlassian.com/forums/Rovo-for-Software-Teams-Beta/Rovo-Dev-is-now-generally-available/ba-p/3125394). "Rovo Dev capabilities are moving directly into eligible Jira and Teamwork Collection (TWC) subscriptions" [S] — [Rovo Dev pricing](https://www.atlassian.com/software/rovo-dev/pricing)
- The **Atlassian Rovo MCP Server** went GA on 2026-02-04, covering Jira, Confluence, JSM Ops, Bitbucket Cloud and Compass. It is described as free and not counting against Rovo credits. Credits are 25/70/150 per user per month on Standard/Premium/Enterprise, pooled per org [S-agg] — [The AI Agent Index](https://theaiagentindex.com/agents/atlassian-rovo)
- Third-party prerequisites: GitHub Copilot for Jira needs Jira as "an AI-enabled app" with Rovo activated [P] — [GitHub Docs source: Jira integration](https://raw.githubusercontent.com/github/docs/main/content/copilot/how-tos/copilot-integrations/integrate-cloud-agent-with-jira.md). Cursor's Jira integration (changelog 2026-05-19) "supports Atlassian commercial cloud sites with Rovo enabled", not HIPAA, FedRAMP or Gov [S] — [Cursor Docs: Jira](https://cursor.com/docs/integrations/jira), [Cursor changelog 05-19-26](https://cursor.com/changelog/05-19-26)
- **Prompt injection:** Cato CTRL's "Living off AI" proof of concept (June 2025) used a malicious Jira Service Management ticket. When an internal support engineer's Claude processed it through Atlassian's MCP, it pulled other internal Jira data and posted it to the attacker's ticket, with the engineer acting as an unwitting proxy [S] — [Cato Networks](https://www.catonetworks.com/blog/cato-ctrl-poc-attack-targeting-atlassians-mcp/), [SC World](https://www.scworld.com/news/jira-tickets-become-attack-vectors-in-poc-living-off-ai-attack)

### Inferences
- Jira now has the broadest cross-vendor assignee list (Claude Code, Cursor, Copilot, Rovo; Codex coming) plus session visibility. For a 2–5 person China+US team, though, it means Jira Cloud plus Rovo activation plus admin setup, and the agents are again vendor-hosted runs triggered from Jira, not the engineers' local CLIs.
- "Agents under existing permissions" with audit trails covers governance, not explicit per-action human confirmation. No source showed a passkey-style or human-confirm step for an agent accepting or claiming work.
- The JSM demo is directly analogous to Longtable's threat model: text from someone else lands in a shared ticket and gets executed by *your* agent.

### Gaps
- atlassian.com and support.atlassian.com were blocked, so:
  - exact GA dates for Agents in Jira and Rovo Dev, and the Codex arrival date, are unconfirmed;
  - how Claude Code is invoked from Jira (Anthropic-hosted cloud session vs Rovo-hosted) is unknown;
  - approval settings for agent transitions are unknown;
  - Atlassian Cloud usability from mainland China was not researched.

## 4. Slack: vendor agent bots, Slack MCP / platform, "Slack Code" channels

### Takeaway
Slack is where cross-vendor agent work is coordinated *socially*. Every vendor has an @-mention bot (Claude Tag / Claude Code in Slack, Codex, Cursor, GitHub Copilot, @ChatGPT, Linear Agent). Slack itself shipped an official MCP server (GA 2026-02-17) and, at Dreamforce 2026, "Slack Code" code channels where people and agents see plan, diff and preview together. Each bot is still single-vendor with its own identity and billing, Slack has no task/claim/blocker model, and pulling channel context into prompts is an acknowledged injection risk.

### Cited Findings
- Slack's **official hosted MCP server** has been GA since 2026-02-17 at `mcp.slack.com/mcp` with user-token OAuth and 50+ partners (Anthropic, Google, OpenAI, Perplexity and others); Claude.ai, Claude Code, Perplexity and Cursor are documented clients [S-agg] — [Gamut](https://www.gamut.so/blog/slack-mcp-server-guide), [Truto](https://truto.one/blog/best-mcp-server-for-slack-in-2026/). Official framing: "Slack Securely Powers Your Third-Party Agents With Your Business Context" (MCP + Real-time Search API) [S] — [Slack blog](https://slack.com/blog/news/mcp-real-time-search-api-now-available). A Slackbot MCP client lets Slackbot call connected MCP tools [S] — [slack.dev](https://slack.dev/context-aware-agents-slack-mcp-server-real-time-search/)
- **Dreamforce 2026:** "Slack Code ... code channels ... people and AI agents come together in a dedicated space ... to write, review, and ship code live, with everyone able to see the plan, the code diff, and a working preview". Partners: Anthropic, OpenAI, GitHub, Vercel, Cognition. "Slackbot in channels"; "Slackforce" [S] — [Salesforce: Dreamforce 2026 takeaways](https://www.salesforce.com/news/stories/five-dreamforce-2026-takeaways/), [Slack blog](https://slack.com/blog/news/ai-powered-interface-for-work), [Concret.io recap](https://www.concret.io/blog/dreamforce-2026-day-3-keynote) [S-agg]. GitHub already uses it: Copilot "will create a dedicated code channel, called **Slack Code** ... one channel per task" [P] — [GitHub Docs source: Slack integration](https://raw.githubusercontent.com/github/docs/main/content/copilot/how-tos/copilot-integrations/integrate-cloud-agent-with-slack.md)
- **Vendor bots in Slack (date and status):**
  - **Claude Tag**: public beta, Team/Enterprise, launched 2026-06-23 [P/S] (see §5).
  - **Claude Code in Slack**: research-preview beta from 2025-12-08 [P] — [Claude blog](https://claude.com/blog/claude-code-and-slack); now being retired for Team/Enterprise [P] — [Claude Code Docs: Slack](https://code.claude.com/docs/en/slack).
  - **Codex in Slack**: GA 2025-10-06 on Plus, Pro, Business, Edu and Enterprise [S] — [OpenAI](https://openai.com/index/codex-now-generally-available/), [InfoWorld](https://www.infoworld.com/article/4070541/openai-codex-adds-sdk-admin-tools-slack-integration.html).
  - **Cursor**: `@cursor` plus a prompt; it detects repo, model, base branch or named environment [S] — [Cursor Docs: Slack](https://cursor.com/docs/integrations/slack).
  - **GitHub Copilot**: shared sessions, public preview 2026-08-21 [S/P] (see §1).
  - **@ChatGPT in Slack and Microsoft Teams**: DevDay 2026-09-29, Business/Enterprise only, "teammates do not need their own ChatGPT licence" [S-agg] — [Nerdschalk](https://nerdschalk.com/chatgpt-business-teams-slack-marketplace/), [TechCityAuthority](https://www.techcityauthority.com/2026/09/openai-devday-2026-everything-announced.html).
  - **Linear coding sessions** can be started from a Slack thread [S] — [linear.app/coding-sessions](https://linear.app/coding-sessions).
- **Injection risk is acknowledged by the vendors.** Anthropic: "Claude may follow directions from other messages in the context, so users should make sure to only use Claude in trusted Slack conversations" [P] — [Claude Code Docs: Slack](https://code.claude.com/docs/en/slack). GitHub: Copilot "uses all messages in the conversation to inform the work. The entire thread becomes the decision-making context" [P] — [GitHub Docs source: Slack integration](https://raw.githubusercontent.com/github/docs/main/content/copilot/how-tos/copilot-integrations/integrate-cloud-agent-with-slack.md)

### Inferences
- A mixed Claude Code + Codex team in Slack gets parallel, unconnected bots: Claude Tag in one thread, Codex in another, each with its own identity, billing, sandbox and progress display. Nothing aggregates "who is doing what" across them except humans reading channels.
- "Slack Code" channels (shared plan/diff/preview) are the nearest thing to a shared live view of agent work, but they are per-task, per-vendor and Slack-only (no WeChat), and the Dreamforce partner list suggests vendor-run agents rather than engineers' local CLIs.

### Gaps
- slack.com and docs.slack.dev were blocked. Exact Dreamforce 2026 dates, GA vs pilot status of Slack Code beyond GitHub's preview, and Slack AI pricing are unconfirmed.
- Slack's API/data-use terms for third-party LLM apps were not researched.

## 5. Anthropic: Claude Code team/enterprise features and multi-agent coordination

### Takeaway
Anthropic has the richest *single-person* multi-agent tooling: agent teams with a shared, lock-claimed task list, agent view, cross-session messaging, Projects, and hooks. Its *organization* features include Team-visible cloud sessions, analytics, server-managed settings, plugin marketplaces and Code Review. Since 2026-06-23 there is also **Claude Tag**, a shared-identity @Claude in Slack that anyone in a channel can task and steer. Every coordination primitive is Claude-only, and the claim/task primitives are scoped to one human (Projects "belong to one user"; agent teams live on one machine). There is no cross-person, cross-vendor board.

### Cited Findings
**Multi-agent primitives (Claude Code)**
- Five ways to run parallel work: subagents, **agent view** (research preview), **agent teams** (experimental, off by default), dynamic workflows, and **Projects** (public beta, Pro/Max). "In every approach the workers are Claude sessions. To involve a different tool, expose it to Claude as an MCP server" [P] — [Claude Code Docs: Run agents in parallel](https://code.claude.com/docs/en/agents)
- **Agent teams** launched with Opus 4.6 on 2026-02-05 as a research preview [S] — [TechCrunch](https://techcrunch.com/2026/02/05/anthropic-releases-opus-4-6-with-new-agent-teams), [MarkTechPost](https://www.marktechpost.com/2026/02/05/anthropic-releases-claude-opus-4-6-with-1m-context-agentic-coding-adaptive-reasoning-controls-and-expanded-safety-tooling-capabilities/). Current docs [P] — [Claude Code Docs: Agent teams](https://code.claude.com/docs/en/agent-teams):
  - Enable with `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`.
  - A lead plus teammates share a task list with states "pending, in progress, and completed" and dependencies. "Task claiming uses file locking to prevent race conditions".
  - Mailboxes live at `~/.claude/teams/{team}/inboxes/{agent}.json`.
  - Hooks `TeammateIdle`, `TaskCreated` and `TaskCompleted` can block with exit code 2.
  - The task list "persists locally and is never uploaded".
  - Limitations: "One team per session ... can't share a team across sessions", no nested teams, the lead is fixed, no resumption of in-process teammates, and "Task status can lag".
- Agent-team permissions [P] — [Agent teams](https://code.claude.com/docs/en/agent-teams):
  - Teammates inherit the lead's permission mode, and their prompts surface in the lead session.
  - Plan approvals are granted by the lead "without the lead reviewing it".
  - "A teammate can't approve a permission prompt or supply consent on your behalf"; in auto mode, relayed approval claims are treated "as untrusted input".
- **Agent view** (`claude agents`) is one screen showing your background sessions grouped as Needs input / Working / Completed [P] — [Agent view](https://code.claude.com/docs/en/agent-view)
- **Projects** [P] — [Projects](https://code.claude.com/docs/en/claude-projects):
  - One conversation that spawns parallel cloud "threads" with shared instructions and project memory (`MEMORY.md`); an Overview pane lists "Waiting on you".
  - "public beta on Pro and Max ... They aren't available on Team or Enterprise plans yet".
  - "A project belongs to one user. You can't share a project or its threads with another user ... There are no organization-level controls for projects during the beta".
- **Cross-session messaging** works only between *your own* sessions (this machine, your other machines, the cloud), and "a message from another session never counts as your consent" [P] — [Cross-session messaging](https://code.claude.com/docs/en/cross-session-messaging)
- **Channels** (research preview) push chat or webhook events into a running session through an MCP plugin (Telegram, Discord, iMessage). A sender allowlist applies, and with *permission relay* "Anyone who can reply through the channel can approve or deny tool use in your session". Team/Enterprise must explicitly enable channels, and admins can restrict them via `allowedChannelPlugins` [P] — [Channels](https://code.claude.com/docs/en/channels)

**Cloud sessions and sharing**
- Cloud sessions are available on Pro, Max and Team, and on Enterprise with premium or "Chat + Claude Code" seats [P] — [Claude Code in the cloud](https://code.claude.com/docs/en/claude-code-on-the-web):
  - On Team/Enterprise a session can be set to **Team** visibility, visible to the org with repository-access verification. Recipients see a snapshot that "doesn't update in real time".
  - GitHub only for clone/PR (GHES on Team/Enterprise).
  - Credentials stay outside the VM, behind a proxy.
  - Auto-fix PR replies post "under your username" but labelled Claude Code.
  - Routines run on a schedule, an API call, or GitHub events.
- **Claude Code in Slack (earlier version)** [P] — [Claude Code Docs: Slack](https://code.claude.com/docs/en/slack):
  - Runs under each user's own account and plan limits; channels only, no DMs.
  - Sessions are automatically Team-visible on Team/Enterprise.
  - Limits: GitHub only, one PR per session.
  - "Anthropic is retiring this version for Team and Enterprise workspaces in favor of Claude Tag; it remains the setup path on Pro and Max".

**Claude Tag (shared @Claude in Slack)**
- Status and price: "Public Beta". Available on Team and Enterprise, first-party only; not on Free, Pro or Max. Channel work bills to an org **usage balance** under an Owner-set spend limit, with no per-seat charge [P] — [Claude Tag overview](https://claude.com/docs/claude-tag/overview). Released 2026-06-23 as a replacement for the old Slack app, with a 30-day opt-in migration [S] — [VentureBeat](https://venturebeat.com/technology/anthropic-launches-claude-tag-replacing-its-slack-app-with-a-persistent-ai-teammate-that-learns-monitors-and-works-autonomously), [KuCoin news flash](https://www.kucoin.com/news/flash/anthropic-launches-claude-tag-with-agent-identity-for-slack-integration) [S-agg]
- Team semantics [P] — [How Claude Tag works](https://claude.com/docs/claude-tag/concepts/how-it-works):
  - "Anyone in the channel can steer a running session by replying in its thread"; a **Stop** button records who stopped it.
  - Progress is a live checklist (edits don't trigger Slack notifications).
  - Channel memory persists.
  - "team work → Claude Tag; personal work → Cowork or Claude Code".
- Identity and safety [P] — [Security and data handling](https://claude.com/docs/claude-tag/concepts/security-and-data):
  - Claude acts under its own service accounts (the Claude app in Slack, the Claude GitHub App for PRs).
  - Per-channel/workspace **Access bundles**; Agent Proxy injects credentials outside the sandbox; egress is default-deny.
  - With **personal connectors**, "Claude is designed to take direction from the connector's owner, treating what other people post in the thread as information for the task rather than as instructions". On Enterprise, an admin can require the user's review of every result before it posts.
- Access restrictions [P] — [Restrict where Claude Tag operates](https://claude.com/docs/claude-tag/admins/restrict-access):
  - Replies from restricted members "reach Claude marked as coming from someone who can't use it. Claude can read them as context and doesn't act on them".
  - Guests "can't approve a tool or permission request".
  - Claude doesn't work in Slack Connect (cross-company) channels.
- Carry-over from Claude Code [P] — [Claude Tag for Claude Code users](https://claude.com/docs/claude-tag/concepts/for-claude-code-users), [Security and data](https://claude.com/docs/claude-tag/concepts/security-and-data):
  - Repo `CLAUDE.md` files and skills load; repo **hooks don't run**; `.mcp.json` doesn't load.
  - Sessions run in auto mode with admin allow rules instead of per-user prompts.
  - Not available with ZDR or CMEK.

**Org admin and visibility**
- The Team/Enterprise analytics dashboard shows usage metrics, contribution metrics (public beta, needs the GitHub app), a leaderboard and CSV export; per-user tokens and cost come via OpenTelemetry or a spend report [P] — [Analytics](https://code.claude.com/docs/en/analytics)
- Server-managed settings (Team/Enterprise Owners) [P] — [Server-managed settings](https://code.claude.com/docs/en/server-managed-settings). Also: managed MCP allow/deny lists, org plugin management through managed settings, org plugin sync from a GitHub/GitLab repo, and private marketplaces [P] — [docs index](https://code.claude.com/docs/llms.txt), [claude.com docs index](https://claude.com/docs/llms.txt)
- **Code Review**: research preview on Team/Enterprise, averaging **$15–25 per review**; findings "don't approve or block your PR" [P] — [Code Review](https://code.claude.com/docs/en/code-review)
- Built-in prompt-injection safeguards: permission system, network-command approval, WebFetch page summaries instead of raw pages, folder trust and `.mcp.json` approval, command-injection detection, fail-closed matching. Advice: "Avoid piping untrusted content directly to Claude" [P] — [Security](https://code.claude.com/docs/en/security)

### Inferences
- Agent teams (shared task list with locked claiming, dependencies, completion hooks) is functionally the closest analogue to Longtable's board, but for **one human's Claude sessions on one machine**, local only, never uploaded and experimental. Claude Tag is the multi-human surface but lives in Slack, uses a shared org identity rather than each engineer's agent, and has no task-board semantics.
- Anthropic already ships parts of Longtable's injection posture: thread posts from non-owners are treated as information, restricted members' replies are context only, and peer agents can't approve. These live only inside Anthropic surfaces and don't cover Codex users.
- Codex users on the same team are invisible to every Anthropic surface: analytics, Team-visible sessions, agent view and Claude Tag all count Claude usage only.

### Gaps
- No launch dates found for agent view, Projects, channels or plugins/marketplaces (docs carry status, not dates).
- Whether Anthropic plans a native Linear or Jira delegate (beyond Claude Tag connections and Atlassian's "Claude Agent for Jira") is unknown.
- Anthropic's China-availability policy was not fetched from a primary source (only aggregators, see §9).

## 6. OpenAI: Codex cloud tasks, Codex in Slack/GitHub/Linear, team/enterprise admin, DevDay 2026

### Takeaway
Codex is a strong *single-vendor* team product. It offers cloud tasks triggered from Slack, Linear and GitHub (including as an Agent HQ partner) and Business/Enterprise admin (environment management, action monitoring, analytics/compliance APIs, RBAC, managed `requirements.toml`). DevDay 2026 (2026-09-29) added team-shareable reusable cloud environments, a CLI `/agents` view, Team Tasks, @ChatGPT in Slack/Teams, workspace connections and workspace-level "Agent Security" policies including approvals. There is still no shared cross-vendor work board; coordination happens in Slack, Linear or GitHub threads. Nearly all evidence here is snippet-level.

### Cited Findings
- **Codex GA on 2025-10-06** brought @Codex in Slack, the Codex SDK and admin tools (usage dashboards, workspace management). Slack and SDK are on Plus, Pro, Business, Edu and Enterprise; admin features on Business, Edu and Enterprise [S] — [OpenAI: Codex is now generally available](https://openai.com/index/codex-now-generally-available/), [InfoWorld](https://www.infoworld.com/article/4070541/openai-codex-adds-sdk-admin-tools-slack-integration.html), [OpenAI Devs on X](https://x.com/OpenAIDevs/status/1975274685056389312)
- Admins can "edit or delete Codex cloud environments in their workspace, monitor actions taken by Codex, monitor the quality of code reviews by Codex, and track Codex usage across CLI, IDE, and web". There are analytics and compliance APIs [S] — [OpenAI Developers: Codex admin setup](https://developers.openai.com/codex/enterprise/)
- **RBAC** works through custom roles, Groups and SCIM. **`requirements.toml`** is "an admin-enforced configuration file that constrains security-sensitive settings users cannot override", deployable as cloud-managed policies to app, CLI and IDE from a Codex Policies page [S-agg] — [Codex enterprise admin guide (D. Vaughan)](https://codex.danielvaughan.com/2026/03/27/codex-enterprise-admin-guide/), [managed configuration](https://codex.danielvaughan.com/2026/04/27/codex-cli-enterprise-managed-configuration-requirements-toml-admin-policies/)
- In **Linear**, assign an issue or @Codex and it creates a cloud task and reports progress; Linear changelog entry 2025-12-04 [S] — [OpenAI Developers](https://developers.openai.com/codex/integrations/linear), [Linear changelog](https://linear.app/changelog/2025-12-04-openai-codex-agent). On **GitHub**, Codex is a third-party agent in Agent HQ (public preview), assignable to issues and @-mentionable in PRs [P] — [GitHub Docs source](https://raw.githubusercontent.com/github/docs/main/content/copilot/concepts/agents/about-third-party-coding-agents.md). In **Jira**, Codex support is "forthcoming" as of 2026-07-15 [S] — [DevOps.com](https://devops.com/atlassian-extends-ai-reach-of-jira-into-agentic-engineering-workflows/)
- **Codex app**: macOS on 2026-02-02 ("manage multiple agents at once, run work in parallel", built-in worktrees, plan mode) [S] — [OpenAI: Introducing the Codex app](https://openai.com/index/introducing-the-codex-app/), [VentureBeat](https://venturebeat.com/orchestration/openai-launches-a-codex-desktop-app-for-macos-to-run-multiple-ai-coding); Windows on 2026-03-04 [S-agg] — [Wikipedia: Codex (AI agent)](https://en.wikipedia.org/wiki/Codex_(AI_agent))
- **DevDay 2026** was held 2026-09-29 in San Francisco [S] — [OpenAI: Announcing DevDay 2026](https://openai.com/index/devday-2026/), [dutchstartup.ai](https://www.dutchstartup.ai/en/news/openai-holds-devday-in-september-in-san-francisco-and-sends-teams-to-eight) [S-agg]. Announcements [S] — [OpenAI DevDay 2026 recap](https://openai.com/index/devday-2026-recap/), [The Decoder](https://the-decoder.com/openai-expands-codex-and-its-api-at-devday-with-security-scans-a-decisions-api-and-ultrafast/), [TechCityAuthority](https://www.techcityauthority.com/2026/09/openai-devday-2026-everything-announced.html) [S-agg]:
  - Codex in the cloud with reusable environments ("teams can use them to share one configuration with approved settings and permissions"), steerable from phone or another computer.
  - A refreshed CLI with voice, a new **`/agents` view** that "shows several tasks at once", `/usage` analytics and managed worktrees.
  - Codex repository security scanning.
  - **Team Tasks**: Business/Enterprise "teams" delegate recurring work that runs on a schedule or on events such as a new email or **Slack message**.
  - **@ChatGPT in Slack and Microsoft Teams**.
  - **Workspace connections**, so approved team workflows use company-managed accounts.
  - **Agent Security**: "workspace policies for agent tools, approvals, web access, files, sandboxing, and managed network access".

### Inferences
- OpenAI's team model is "admins govern, individuals delegate, Slack/Linear/GitHub are the shared surface". Team Tasks are ChatGPT-level recurring automations, not a shared engineering task board with claim/blocker states.
- The new CLI `/agents` view mirrors Claude's agent view: it shows *your* parallel tasks, not your teammates'.
- For a mixed team, Codex's best first-party shared surfaces (Linear delegate, Slack, Agent HQ) do not show Claude Code users' work, and vice versa.

### Gaps
- openai.com and developers.openai.com were blocked: no primary confirmation of DevDay 2026 feature status (GA vs preview) or plan gating, Codex cloud-task sharing links, or how Codex Slack/Linear tasks attribute identity.
- **Codex CLI hooks** (which Longtable relies on) were not verified.
- OpenAI's mainland-China restrictions come from aggregators only (§9).

## 7. Cursor: cloud/background agents, Slack/Linear/Jira/Teams, team features, Bugbot

### Takeaway
Cursor offers single-vendor cloud agents that can be triggered from almost every collaboration tool (Slack, Linear, Jira since 2026-05-19, Microsoft Teams, GitHub, Notion), plus team-admin infrastructure: shared dev environments with audit logs (2026-05-13), Team MCPs (2026-06-30), Bugbot, and Cursor 3's Agents Window (2026-04-02). It has no cross-vendor board and no human-confirmation gate beyond PR review, and its Teams pricing is $40–$120 per seat. All Cursor evidence is snippet-level because cursor.com was blocked.

### Cited Findings
- Cloud Agents are reachable from Cursor Web, Desktop, Slack, GitHub and Linear. **Automations** run cloud agents "on a schedule or in response to events from GitHub, GitLab, Slack, webhooks, Linear, and more" [S] — [Cursor Docs: Cloud Agents](https://cursor.com/docs/cloud-agent), [Automations](https://cursor.com/docs/cloud-agent/automations)
- **Linear**: delegate the issue or @Cursor; "you must be a Cursor admin" to connect [S] — [Cursor Docs: Linear](https://cursor.com/docs/integrations/linear). **Jira**: assign to Cursor or @Cursor; needs Rovo-enabled commercial cloud (changelog 2026-05-19) [S] — [Cursor Docs: Jira](https://cursor.com/docs/integrations/jira), [Cursor changelog](https://cursor.com/changelog/05-19-26). **Slack**: `@cursor` plus a prompt [S] — [Cursor Docs: Slack](https://cursor.com/docs/integrations/slack). **Microsoft Teams**: `@Cursor` in a channel delegates to a cloud agent [S] — [Cursor changelog](https://cursor.com/changelog/page/7)
- **Cursor 3** shipped 2026-04-02 with the Agents Window GA (local, cloud and remote-SSH agents in one view; local↔cloud handoff) [S-agg] — [DEV Community](https://dev.to/devtoolpicks/cursor-3-just-launched-with-an-ai-agents-window-what-changed-and-is-it-still-worth-it-496f), [Digital Applied](https://www.digitalapplied.com/blog/cursor-3-agents-window-complete-guide)
- **Development environments** for cloud agents arrived 2026-05-13: multi-repo environments; version history with rollback that admins can restrict; "audit logs capturing every action team members take on environments"; and secrets and egress scoped per environment [S] — [Cursor changelog 05-13-26](https://cursor.com/changelog/05-13-26). **Team MCPs** (2026-06-30) let admins configure MCP servers once for Cloud Agents and the Agents Window [S-agg] — [anycap.ai](https://anycap.ai/page/en-US/ai/cursor-ai-2026-new-features-guide)
- **Bugbot** dropped its $40/seat fee on 2026-05-11 in favour of usage billing (about $1.00–1.50 per run), effective at first renewal after 2026-06-08 [S] — [Cursor blog: May 2026 Bugbot changes](https://cursor.com/blog/may-2026-bugbot-changes), [Finout](https://www.finout.io/blog/what-happened-to-cursor-pricing-2026-guide-5-cost-cutting-tips) [S-agg]
- **Teams pricing** since 2026-06-01: Standard $40/user/month and Premium $120 (5× usage), 20% off annually [S-agg] — [StartupHub](https://www.startuphub.ai/ai-news/technology/2026/cursor-teams-upgrades-pricing-for-predictability), [nxcode](https://www.nxcode.io/resources/news/cursor-ai-pricing-plans-guide-2026)
- Cursor is an External Agent in Notion (§8) and a named Jira agent partner (§3) [S].

### Inferences
- Cursor maximizes the number of trigger surfaces, but each triggers *Cursor's* cloud agent. For a Claude Code + Codex team, Cursor is relevant mainly as the template Linear, Jira and Notion built their agent APIs around, not as a coordination layer.
- The environment audit logs and admin controls are infrastructure governance. No claim/blocker or commitment-confirmation model was found.

### Gaps
- cursor.com was blocked, so it is unknown which user's account and seat a Slack/Linear-triggered run bills to.
- Other unconfirmed items: whether non-admins can trigger runs, Bugbot details, and Cursor's restrictions in mainland China (aggregator-only, §9).

## 8. Google Jules, Microsoft (Teams / Azure Boards / Copilot) and Notion agents

### Takeaway
None of these is a cross-vendor human+agent board for small teams. Jules is Google's single-vendor async agent with an API and MCP connections (including Linear). Microsoft's relevant pieces route through **GitHub Copilot** (Azure Boards → Copilot; shared Copilot sessions in Teams, 2026-08-21) plus Cursor and @ChatGPT in Teams. **Notion** is the most interesting: an External Agents API (alpha, 2026-05-13) lets Claude Code, Codex, Cursor and Decagon be @-mentioned and assigned tasks from shared boards, with per-agent permissions.

### Cited Findings
**Google Jules**
- Jules is an async coding agent working in a cloud VM and opening PRs [S] — [Google blog: Jules](https://blog.google/innovation-and-ai/models-and-research/google-labs/jules/). The Jules API (Oct 2025) can connect Jules to "project management tools like Linear or Jira", alongside the Jules Tools CLI [S] — [Google blog: Jules Tools & API](https://blog.google/technology/google-labs/jules-tools-jules-api/), [Google Developers Blog](https://developers.googleblog.com/en/level-up-your-dev-game-the-jules-api-is-here/)
- "MCP support comes to Jules" on 2026-02-02, starting with Linear, Stitch, Neon, Tinybird, Context7 and Supabase [S] — [Jules changelog](https://jules.google/docs/changelog/2026-02-02/)
- Pricing is reported as Free, Pro $20, and a **Team plan at $40/user/month** with shared repos, team management and SSO [S-agg] — [MorphLLM](https://www.morphllm.com/comparisons/jules-google-coding-agent), [Agentcode](https://agentcode.ai/google-jules-pricing). These aggregator numbers conflict with each other on free-tier limits and are unverified.
- The **Gemini CLI GitHub Action** was among the agents compromised by issue/comment injection (PromptPwnd, Dec 2025; Comment and Control, April 2026) [S] — [Aikido](https://www.aikido.dev/blog/promptpwnd-github-actions-ai-agents); [P, secondary] — [Comment and Control case study](https://raw.githubusercontent.com/vectara/awesome-agent-failures/main/docs/case-studies/comment-and-control-prompt-injection.md)

**Microsoft**
- Azure Boards → Copilot coding agent: public preview 2025-09-18 [S] — [GitHub Changelog](https://github.blog/changelog/2025-09-18-assign-azure-boards-work-items-to-copilot-coding-agent-in-public-preview/). It later rolled out as GA with branch selection and "Kanban cards also surface Copilot status indicators ... which items are actively being worked on by AI and which are ready for review" [S] — [Azure DevOps blog](https://devblogs.microsoft.com/devops/github-copilot-for-azure-boards/). Custom-agent selection arrived in the Sprint 269 update (2026), with up to 2,000 connected repos [S] — [Azure DevOps release notes](https://learn.microsoft.com/en-us/azure/devops/release-notes/2026/boards/sprint-269-update)
- In Teams, "@GitHub in a channel, thread, or direct message" starts a Copilot cloud agent session where "anyone in the conversation can ask questions and add context, and participants with write access to the repository can trigger Copilot to make changes" (public preview 2026-08-21) [S] — [GitHub Changelog](https://github.blog/changelog/2026-08-21-shared-agentic-work-with-github-copilot-in-microsoft-teams/), [Microsoft 365 Dev Blog](https://devblogs.microsoft.com/microsoft365dev/build-collaborative-agents-where-work-happens/)
- On 2026-09-25 Microsoft relaunched Copilot as a unified app with **Home (incl. "Cowork")**, **Code** (built on GitHub Copilot tech) and **Autopilot** (always-on cloud agents that monitor email and Teams channels) [S] — [Official Microsoft Blog](https://blogs.microsoft.com/blog/2026/09/25/introducing-the-new-copilot-with-home-code-and-autopilot/), [Quartz](https://qz.com/microsoft-copilot-unified-app-coding-ai-agents-092526). "Visual Studio cloud agents now run inside GitHub Copilot" (2026-04-29) [S] — [Help Net Security](https://www.helpnetsecurity.com/2026/04/29/microsoft-visual-studio-cloud-agent-integration/)

**Notion**
- **Custom Agents** launched 2026-02-24 for Business and Enterprise. They were free through 2026-05-03 and have needed Notion Credits since 2026-05-04 ($10 per 1,000 credits) [S] — [Reworked](https://www.reworked.co/digital-workplace/notion-custom-agents-reach-general-availability/), [Notion blog](https://www.notion.com/blog/introducing-custom-agents)
- **Developer Platform / External Agents API (alpha), 2026-05-13**: Claude Code, Codex, Cursor and Decagon act as "first-class collaborators", and teams can "@mention these agents, assign them tasks from shared boards, and monitor progress in real time". The same release brought Notion Workers, a serverless runtime at $10 per 1,000 credits after 2026-08-11 [S] — [Notion releases 2026-05-13](https://www.notion.com/releases/2026-05-13), [Let's Data Science](https://letsdatascience.com/news/notion-integrates-claude-and-cursor-as-external-agents-7f0782c7) [S-agg]. In June 2026 Notion announced "External Agents in Notion: Claude + Cursor ... Assign them tasks from a board shared with your whole team. @-mention them like teammates. Watch them run" [S] — [Notion on X](https://x.com/NotionHQ/status/2069816393395012009), [AlternativeTo](https://alternativeto.net/news/2026/6/notion-launches-external-agents-with-claude-and-cursor-integrations/) [S-agg]
- Permissions are "set per agent and aren't inherited from whoever starts a run", at levels view & interact, edit, or full access; "Claude agents can only see what you share with them" [S] — [Notion Help: Use Claude agents in Notion](https://www.notion.com/help/use-claude-agents-in-notion), [Notion guide: Claude agents on your team's task board](https://www.notion.com/help/guides/how-to-set-up-claude-agents-on-your-teams-notion-task-board). A press headline warns "it'll cost you" [S] — [Android Authority](https://www.androidauthority.com/notion-getting-external-agents-support-3681305/)

### Inferences
- Notion External Agents is conceptually the closest big-platform product to Longtable: a board shared by the team, where several vendors' agents (Claude Code, Codex, Cursor) are assignable and visible. It is still *vendor-hosted runs triggered from Notion* (alpha) rather than each engineer's own local agent reporting into the board, and no claim, blocker or commitment-confirmation semantics were found.
- Microsoft's agent story for coding teams is effectively "use GitHub Copilot"; Teams is a chat surface for it.

### Gaps
- Google Antigravity (agent-first IDE / "Agent Manager") could not be researched after the search budget ran out.
- Microsoft Planner / Agent 365 agent-assignment features are unconfirmed.
- Unknown for Notion External Agents: approval gates, whose subscription runs the Claude Code / Codex job, and GA timing.
- notion.com, jules.google and the Microsoft blogs were blocked (snippets only).

## 9. Across all: what they do NOT do well for a small cross-vendor (Claude Code + Codex) China+US team, including prompt-injection defenses

### Takeaway
As of 2026-10-03, every big platform orchestrates **cloud runs that it (or a partner) hosts**: GitHub Agent HQ, Jira, Linear coding sessions, Notion External Agents, Slack bots. None turns each engineer's **local** Claude Code or Codex CLI session into a visible teammate on one board. None models human commitments (claim, accept, forward) with a human-only confirmation step. None has a "who is stuck, who is needed" primitive. None gates *other people's text* before it reaches *your* agent; they filter by repository permission or treat non-owner text as "information", and documented attacks keep succeeding. Most of the team features also sit behind Business/Enterprise tiers and vendors that don't officially serve mainland China.

### Cited Findings
**Prompt injection through shared work items: incidents**
- **Invariant Labs, May 2025**: a malicious public-repo issue hijacked an agent via the GitHub MCP server to leak private-repo data [S] — [Docker blog](https://www.docker.com/blog/mcp-horror-stories-github-prompt-injection/)
- **Cato "Living off AI", June 2025**: a Jira Service Management ticket injected instructions that an internal user's Claude executed through the Atlassian MCP [S] — [Cato Networks](https://www.catonetworks.com/blog/cato-ctrl-poc-attack-targeting-atlassians-mcp/)
- **Aikido "PromptPwnd", Dec 2025**: issues, PR text and commit messages fed into Gemini CLI, Claude Code or Codex in GitHub Actions/GitLab CI led to secret leakage; at least five Fortune 500 companies were affected. Remediation: restrict toolsets, don't inject untrusted input into prompts, treat AI output as untrusted [S] — [Aikido](https://www.aikido.dev/blog/promptpwnd-github-actions-ai-agents), [CSA research note](https://labs.cloudsecurityalliance.org/research/csa-research-note-ai-github-actions-security-20260503-csa-st/)
- **"Comment and Control", 2026-04-16**: CVSS 9.4 across Claude Code Security Review, Gemini CLI Action and the Copilot coding agent (hidden HTML comment in an issue); GitHub called it a "known architectural limitation" and paid $500 [P, secondary] — [case study](https://raw.githubusercontent.com/vectara/awesome-agent-failures/main/docs/case-studies/comment-and-control-prompt-injection.md); [S] — [VentureBeat](https://venturebeat.com/security/ai-agent-runtime-security-system-card-audit-comment-and-control-2026)

**Defenses that exist today**
- **GitHub**: comments from non-writers are never shown to the agent; hidden characters are filtered; workflows need approval; the agent can't approve or merge [S] — [GitHub Docs](https://docs.github.com/en/copilot/concepts/agents/cloud-agent/risks-and-mitigations). MCP **lockdown mode** filters public-repo content from authors without push access and is "not an authorization boundary" [P] — [server-configuration.md](https://github.com/github/github-mcp-server/blob/main/docs/server-configuration.md). App-identity PRs need an extra approval [P] — [GitHub Docs reusable](https://raw.githubusercontent.com/github/docs/main/data/reusables/copilot/cloud-agent/unattributed-additional-approval-note.md)
- **Anthropic**: Claude Tag treats others' posts as "information for the task rather than as instructions" when personal connectors are used; restricted members' replies are context only; guests cannot approve; Enterprise can require "review of every result" before posting [P] — [Claude Tag security](https://claude.com/docs/claude-tag/concepts/security-and-data), [restrict access](https://claude.com/docs/claude-tag/admins/restrict-access). Agent-team and cross-session messages "never count as your consent" [P] — [Cross-session messaging](https://code.claude.com/docs/en/cross-session-messaging). The older Slack integration only *warns* users to stay in trusted conversations [P] — [Claude Code Docs: Slack](https://code.claude.com/docs/en/slack)
- **Notion**: per-agent permissions that aren't inherited from whoever starts a run [S] — [Notion Help](https://www.notion.com/help/use-claude-agents-in-notion)
- **Linear**: a human remains assignee; agents are only delegates [S] — [Linear Docs](https://linear.app/docs/assigning-issues)

**Cost and tier gating (as of 2026-10-03)**
- Claude Tag: Team/Enterprise only, usage-billed [P] — [overview](https://claude.com/docs/claude-tag/overview)
- Claude Projects: Pro/Max only, not shareable [P] — [Projects](https://code.claude.com/docs/en/claude-projects)
- GitHub shared Slack/Teams sessions: Business/Enterprise preview [S] — [GitHub Changelog 2026-09-25](https://github.blog/changelog/2026-09-25-updates-to-github-copilot-for-slack-and-microsoft-teams/)
- Agents in Jira: paid Jira Cloud [S] — [SiliconANGLE](https://siliconangle.com/2026/07/15/atlassian-evolves-jira-orchestration-hub-developers-ai-agents/)
- Notion Custom/External Agents: Business/Enterprise plus credits [S] — [Reworked](https://www.reworked.co/digital-workplace/notion-custom-agents-reach-general-availability/)
- Codex admin features: Business/Edu/Enterprise [S] — [InfoWorld](https://www.infoworld.com/article/4070541/openai-codex-adds-sdk-admin-tools-slack-integration.html)
- Cursor Teams: $40–$120 per seat [S-agg] — [StartupHub](https://www.startuphub.ai/ai-news/technology/2026/cursor-teams-upgrades-pricing-for-predictability)
- Linear coding sessions: Basic+ plus AI credits [S] — [Linear Docs](https://linear.app/docs/coding-sessions)

**China accessibility**
- Anthropic and OpenAI first-party APIs are "not officially supported from mainland China per each provider's published supported-country lists" [S-agg] — [Blake Crosley](https://blakecrosley.com/blog/codex-vs-claude-code-2026), [Digital in Asia tracker](https://digitalinasia.com/which-llms-work-asia-accessibility-tracker/)
- Cursor reportedly restricts Claude models for users in China [S-agg] — [cursorpractice.com](https://cursorpractice.com/en/cursor-sharing/Cursor-Restricts-Claude-Usage-in-China-en)
- Claude Tag does not work in Slack Connect channels shared with another company [P] — [restrict access](https://claude.com/docs/claude-tag/admins/restrict-access)

### Inferences
Derived comparison, synthesized from the findings above:

| Platform (Oct 2026) | Claude + Codex both first-class? | Where agents run | Human claim / commitment gate | Team view of each person's agents | Blocker / help flow | Shared-text injection gate |
|---|---|---|---|---|---|---|
| GitHub Agent HQ / cloud agent | Yes (third-party agents in preview) | GitHub-hosted (Actions) | None; merge/workflow approvals only | Own + prompted sessions; Enterprise control plane | None | Repository write-access filter; MCP lockdown (best-effort) |
| Linear | Codex native; Claude via Linear Agent "coding sessions" or MCP | Vendor clouds / Linear sandbox | Human = assignee, agent = delegate (data model, not a confirmation step) | Agent session state on the issue | Standard issue relations only | None found |
| Jira (Rovo, agents in Jira) | Claude Code, Cursor, Copilot; Codex "forthcoming" | Vendor clouds / Rovo | Existing Jira permissions + audit | "Agent sessions in Jira" | None agent-specific found | None found; JSM proof-of-concept exploited |
| Slack (+ vendor bots, Slack Code) | Separate per-vendor bots | Each vendor's cloud | Per-bot (e.g., GitHub write-access gating) | Per-thread / code channel | Humans in channel | Vendor-specific; Anthropic warns to use trusted channels |
| Anthropic (Claude Code, Claude Tag) | Claude only | Local (agent teams, agent view) / Anthropic cloud | Claude Tag: guests and restricted members can't act; peer agents can't approve | Team-visible snapshots; analytics (Claude only) | "Needs input" / "Waiting on you" (single user) | Non-owner text treated as information (personal connectors); restricted members' text is context only |
| OpenAI Codex | Codex only | Local / OpenAI cloud | Admin "Agent Security" approval policies (DevDay 2026) | CLI `/agents` view (single user); admin dashboards | None | Not found |
| Cursor | Cursor only | Cursor cloud / local | PR review; admin-only integration setup | Agents Window (single user); environment audit logs | None | Not found |
| Notion External Agents (alpha) | Claude Code, Codex, Cursor | Vendor-hosted, triggered from Notion | Per-agent permissions | Shared board, runs visible | None found | Per-agent visibility scope |

- **White space Longtable occupies:**
  1. Local Claude Code *and* Codex CLI sessions report into one human-owned board through hooks. Every big platform instead launches its own cloud runs, and per-vendor local dashboards (Claude agent view, Codex `/agents`, Cursor Agents Window) are single-user.
  2. Explicit human-only commitment actions (accept, claim someone else's task, forward), with passkey confirmation. The nearest analogues are Linear's assignee/delegate split and GitHub's "agent cannot approve or merge" plus the extra approval for app-identity PRs.
  3. Blocker / "who is needed" / ask-for-help as first-class objects. Nothing equivalent was found on any platform.
  4. An *opt-in acceptance gate* before teammates' text reaches your agent. Platforms rely on permission-based filtering, which is meaningless in a 2–5 person repo where everyone has write access, or on model-side "treat as information" behaviour. GitHub itself calls the injection class an architectural limitation.
  5. WeChat / China-friendly notifications. Every reviewed surface is Slack, Teams, email or the vendor's own app; no WeChat or WeCom integration appeared in any source reviewed.
  6. Small-team price point. Most team or shared-agent features require Business/Enterprise tiers or usage-billed org balances.
- **Strategic risk:** the fastest-moving overlaps are Notion External Agents (shared board plus Claude Code/Codex/Cursor, alpha since May 2026), Jira agent sessions (July 2026), GitHub's shared Slack/Teams sessions (August 2026), and Slack Code channels (Dreamforce 2026). All four are converging on "shared surface where humans see and steer multiple vendors' agents". Their gap is that they assume vendor-hosted runs and enterprise admins.
- **Integration opportunity:** Claude Code agent-team hooks (`TaskCreated` / `TaskCompleted` / `TeammateIdle`) and the cross-session messaging consent rules show Anthropic exposes hook points that Longtable could mirror. The GitHub MCP server's lockdown and read-only modes and the Claude Tag "information, not instructions" rule are reference designs worth citing in Longtable's security story.

### Gaps
- Unconfirmed, because primary pages were blocked:
  - Codex CLI hook coverage;
  - whether Notion External Agents or Jira agent sessions can ingest progress from *locally run* CLI agents, e.g. via their APIs/MCP;
  - whether any platform added an explicit "accept before your agent reads it" gate after Comment and Control.
- Mainland-China availability of Linear, Notion, Slack and Atlassian Cloud was not researched, and Anthropic's and OpenAI's China restrictions rest on aggregators rather than the providers' own pages.
- Universe 2026 (GitHub) and later Dreamforce/Atlassian events may change preview → GA statuses after 2026-10-03.
