# Claude Code: A Working Reference

A practical guide for using Claude Code across the development lifecycle. Opinionated, minimal, and meant to be re-read.

---

## The core mental model

Three things determine whether Claude Code works well:

1. **Plan before you build.** Vibe-coding produces code that solves the wrong problem. Plan Mode (`Shift+Tab`) is the cheapest insurance you have.
2. **Manage context like a budget.** Context degradation is the primary failure mode. Every token in your context competes with every other token.
3. **Keep it simple.** Low-level tools plus a few good abstractions beat heavy frameworks. LLMs are fragile; complexity makes debugging exponential.

Everything below is a corollary of these three.

---

## The six phases

### 1. Research & SOTA exploration

- Use **Plan Mode** as your default — it reads files and answers questions without making changes.
- Spin up a dedicated session with `/rename` (e.g., `sota-vector-db`). Treat sessions like branches.
- Connect MCP servers for real sources (web search, Notion, internal Glean) instead of relying on Claude's training priors.
- Push back. Don't accept the first synthesis. *"Steelman three competing approaches, then argue against each from a production perspective."*
- Save research output to `docs/research/*.md` — it becomes context for every later phase.
- For deep reasoning, use `/effort` or the `ultrathink` keyword.

### 2. Experiment setup for prototyping

- Use `git worktree add ../proj-experiment-a experiment-a` so each prototype gets its own directory and Claude session.
- Write a minimal `CLAUDE.md` for the experiment — explicit goals, **what's out of scope**, and what "done" looks like. The out-of-scope list is what stops gold-plating.
- Force smallest-runnable-thing-first: a single script with fake data before any abstractions.
- Don't install heavy frameworks for prototypes.

### 3. Design for a software component

The four-phase loop:

1. **Explore** — *"Read /src/auth and explain how sessions and login work."*
2. **Plan** — *"I want to add Google OAuth. What files change? What's the session flow? Produce a detailed plan."* Edit the plan directly before execution.
3. **Critique** — the step most people skip. *"What are three things wrong with this design? What would a senior engineer push back on?"* When the suggestion is wrong, tell Claude *why* it's wrong — don't tweak the plan yourself.
4. **Persist** — save the final design to `docs/design/<component>.md`.

For non-trivial designs, use a subagent or a separate session as an adversarial reviewer before you build.

### 4. Coding & testing — incremental development

- One unit of work = one verifiable behavior. Test → fail → implement → pass → commit. Then move on.
- Commit very frequently. Trivial rollback points; useful history for Claude.
- Use `/clear` aggressively between unrelated tasks.
- Have Claude run the tests itself after each change. Don't trust "it should work."
- Auto-Accept (`Shift+Tab`) is for boring, well-scoped grinds. For anything novel, stay in the loop.
- Adversarial check at the end of each unit: *"Diff against main and prove this works. List edge cases you didn't handle."*

### 5. Debugging

Debugging is where Claude's agentic loop shines — open-ended paths benefit most from dynamic tool use.

- Pipe failing output in directly: `cat build-error.txt | claude -p 'concise root cause'`
- For flaky tests/race conditions: *"Form three hypotheses, then design a minimal experiment to disprove each."* Stops latching onto the first plausible answer.
- Give Claude the tools to verify: shell, logs, the ability to loop the failing test.
- For UI bugs: attach a Playwright MCP server so Claude can reproduce in a real browser.
- When stuck, ask Claude to `git bisect` — it's surprisingly good at this.
- A spinning Claude is a stuck Claude. After a few minutes without convergence: stop, summarize, `/clear`, restart with tighter scope.

### 6. CI/CD pipeline

Headless mode is everything. The `-p` flag (`--print`) is non-interactive — processes the prompt, outputs to stdout, exits. Forget it and your job will hang.

```yaml
- name: Install Claude Code
  run: npm install -g @anthropic-ai/claude-code
- name: Review PR
  env:
    ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
  run: |
    git diff origin/main...HEAD | \
      claude -p "Review this diff. Output JSON: {issues: [...], severity: ...}" \
      --output-format json \
      --max-turns 5 > review.json
```

What matters once you go past the toy example:

- **`--max-turns`** — bounds runaway loops. A 5-turn session typically uses 15K–40K tokens.
- **`--allowedTools`** — least privilege. Read-only review jobs should not have write access.
- **`--output-format json`** — downstream steps parse with `jq`, not regex.
- **`--resume <session_id>`** — multi-step pipelines preserve context across jobs.
- **Repo `CLAUDE.md` is your CI config** — define review criteria once; every headless run inherits it.
- **Quality gates as scripts** — score the diff 0–100, fail if below threshold. Cheap, fast, effective.
- **Good places to start:** PR review on `pull_request`, scheduled security audit on `cron`, CHANGELOG generation from `git log`, AI-suggested test cases for changed files.

For the GitHub-native path, run `/install-github-app` inside an interactive session — it sets up the `@claude` mention workflow and the secret in one go.

---

## CLAUDE.md — the always-loaded briefing

Lives at the repo root. Loads on every session. Highest leverage and most expensive — every token competes with the conversation.

**Aim for under 200 lines. Some teams run with under 60.**

The test for every line: *"Would removing this cause Claude to make mistakes?"* If no, cut it.

### What belongs

- **Project orientation** — one-line description, tech stack with versions, top-level directory map with purposes.
- **Commands** — exact install/run/test/lint/build/deploy commands, especially anything non-obvious.
- **Conventions Claude can't infer from code** — branching model, where new endpoints go, what's off-limits, "no SSR," "no barrel exports," repository-pattern requirements.
- **Hard prohibitions** — "never commit secrets," "never modify `db/migrations/applied/`." Use `IMPORTANT:` or `YOU MUST` sparingly; if everything is important, nothing is.
- **`@` imports to deeper docs** — `@docs/architecture/auth.md` instead of inlining the content.
- **Compaction hints** — *"When compacting, always preserve the list of modified files and test commands."*

### What does NOT belong

- **Code style rules.** Use a linter. LLMs doing linter work waste tokens and degrade context.
- **Generic best practices Claude already knows** ("write tests," "handle errors").
- **Task-specific procedures** — those go in skills.
- **Personal preferences** — put in `CLAUDE.local.md` and gitignore it.

### The feedback loop

When Claude makes a mistake, tell it to update CLAUDE.md so it doesn't repeat the error. Over months this becomes a living record of every quirk, written by the tool that consumes it.

---

## .claude/skills/ — load-on-demand expertise

Each skill is a folder with a `SKILL.md` (YAML frontmatter: `name` + `description`) and optional supporting files.

**Mechanic:** only the metadata pre-loads at startup. The body loads only when the description matches the current task. You can have dozens of skills without bloating context.

### Good candidates for skills

- Multi-step procedures with strict ordering ("create a new migration," "publish a release").
- Domain-specific generation patterns (your team's exact React component shape).
- Codified review checklists (security, performance — with your specific thresholds).
- External system playbooks (querying the warehouse with table schemas and gotchas).
- Project conventions too detailed for CLAUDE.md (a 300-line "how we write integration tests").

### The two fields that determine whether a skill ever fires

- **`name`** — lowercase, hyphenated, gerund form (`creating-migrations`).
- **`description`** — third person, includes both *what it does* and *when to use it*. Bad: "Helps with database stuff." Good: "Use when creating, modifying, or rolling back PostgreSQL migrations. Triggers on mentions of migrations, schema changes, or `db/migrations/`."

### Rule of thumb

If you'd write the same instructions into multiple PR descriptions, it's a skill. If it belongs in the project README's "About" section, it's CLAUDE.md.

Skills can often replace MCP servers, with the bonus of being readable and auditable instead of black-box.

---

## How to start your day

1. **Pick one thing.** State the goal in one sentence before opening Claude. If you can't, you're not ready to start a session.
2. **Open the right session.** New work → fresh session. Continuing → `claude --resume` or the named session from yesterday.
3. **Re-orient Claude in 30 seconds.** *"We're continuing the OAuth migration. Read `docs/design/oauth.md` and the last 3 commits. Tell me what you understand the next step to be."* This catches drift before it costs you an hour.
4. **Enter Plan Mode** for anything bigger than a one-line change.
5. **Set a stop condition.** *"By lunch I want X merged."* Without one, sessions sprawl.

## How to end your day

1. **Commit or stash everything.** No work-in-progress hanging in Claude's context overnight.
2. **Update CLAUDE.md** with anything Claude got wrong today. One line per mistake.
3. **Write a `NEXT.md` (or a comment in the open PR).** Three bullets: what's done, what's next, what's blocking. Tomorrow-you and tomorrow-Claude both need this.
4. **Save research/design artifacts.** If a session produced something worth keeping, write it to `docs/`. Otherwise it dies with the session.
5. **`/clear` or close the session.** Don't carry stale context into tomorrow.

---

## What NOT to do

- **Don't skip Plan Mode** for multi-file or unfamiliar work. Five minutes of planning saves an hour of confidently-wrong code.
- **Don't let one session run for hours across unrelated topics.** Context degrades. Use `/clear` between topics.
- **Don't trust "it should work."** Make Claude run the test, build, or script. Verification is cheap.
- **Don't accept the first plan.** Force a critique pass.
- **Don't let CLAUDE.md grow unboundedly.** Every quarter, delete lines whose absence wouldn't cause mistakes.
- **Don't put style rules in CLAUDE.md.** That's what linters are for.
- **Don't run headless without `--max-turns`.** Loops can burn budget fast.
- **Don't grant write tools to read-only jobs.** Least privilege applies to AI agents too.
- **Don't hardcode API keys.** Always secrets. Always.
- **Don't paste long files into the prompt.** Use `@path/to/file` so Claude reads it as context — far cheaper and more accurate.
- **Don't ignore Claude when it apologizes for an instruction it "missed."** The instruction is probably ambiguous. Rewrite it.
- **Don't build multi-agent systems before you need them.** A single Claude with a good plan beats three Claudes coordinating badly.

---

## Saving tokens

- **Keep CLAUDE.md lean.** Every line costs on every turn of every session.
- **Use `@file` references** instead of pasting file contents.
- **Use `/clear` between unrelated tasks.** A fresh session is faster *and* cheaper.
- **Use `/btw`** for quick side-questions — answer appears in an overlay and doesn't enter conversation history.
- **Match effort to task.** Don't burn high-reasoning tokens on a variable rename. Use `/effort` to dial down for simple work, up for hard work.
- **Skills over MCP** when both could work. MCP servers add tool definitions to context on every turn; skills are zero-cost until triggered.
- **In headless: cap `--max-turns`** and prefer focused prompts over kitchen-sink ones.
- **Compact deliberately.** `/compact <instructions>` is better than waiting for auto-compaction. *"Focus on the API changes; drop everything else."*
- **Use subagents for research-heavy tangents** — *"use subagents to investigate X."* The subagent's exploration doesn't pollute your main context.
- **Delete dead exploration.** If a path didn't pan out, summarize it in one line and `/clear`. Don't keep dead branches alive in context.

---

## Avoiding context loss & drift

Drift = Claude slowly stops following the rules. Loss = the conversation grows past what Claude can effectively use.

### Prevent drift

- **Re-anchor periodically.** Every ~30 minutes of a long session: *"Restate the plan in your own words. What's done, what's next?"* Mismatches surface fast.
- **Pin invariants in CLAUDE.md, not in the conversation.** Anything in a chat message can fade; anything in CLAUDE.md re-loads next session.
- **Repeat critical constraints.** Right before a code-generation step: *"Remember: no new dependencies, no changes outside `src/api/v2/`."*
- **Watch for apology-and-redo loops.** If Claude is repeatedly fixing the same kind of mistake, the rule isn't sinking in — rewrite it more clearly or move it from chat into CLAUDE.md.

### Prevent loss

- **Persist intermediate artifacts.** Plans → `docs/`. Decisions → ADRs. Anything that took thinking belongs in a file, not a chat.
- **Use named sessions.** `/rename oauth-migration` so you can return to the right context.
- **Compact before you have to.** Manual `/compact` with instructions beats auto-compaction.
- **Use `Esc + Esc` or `/rewind`** to roll back to a known-good checkpoint when a session has wandered into a bad state.
- **Branch sessions for tangents.** A new session for "let me just check this one thing" keeps the main session clean.
- **The interview trick for big features.** *"Interview me using the AskUserQuestion tool. Ask about implementation, UI, edge cases, tradeoffs — dig into the hard parts. Then write the spec to SPEC.md. I'll start a fresh session to execute it."* Clean context, written spec — far better than trying to hold the whole thing in one session.

---

## One-line summary

CLAUDE.md tells Claude *who it is on this project*. Skills tell Claude *how to do specific jobs*. `docs/` is the reference material both point to. Plan Mode is when Claude thinks. `/clear`, `/compact`, and named sessions are how Claude stays sharp. Headless mode is how Claude scales. The rest is discipline.
