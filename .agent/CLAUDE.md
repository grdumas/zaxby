# CLAUDE.md — Agent operating instructions
<!-- Template: ~/workspace/agent/CLAUDE.md
     Copy to the root of each project repo, place plan.yaml at .agent/plan.yaml,
     and fill in the PROJECT_* placeholders before first use. -->

## Project identity

| Field | Value |
|---|---|
| **Jira project key** | `PROJECT_KEY` |
| **Repo (SSH)** | `git@github.com:ORG/REPO.git` |
| **Default branch** | `main` |
| **Plan file** | `.agent/plan.yaml` (machine-readable; tracked in git) |
| **Authoritative plan doc** | `docs/plan.md` (human-authored narrative; read-only for agent) |
| **Plan schema** | `~/workspace/schemas/plan-schema.json` (read-only for agent) |

---

## Role

You are an autonomous coding agent operating inside a KVM sandbox on an HP Z2 workstation
(Fedora 44, 4 vCPU, 16 GiB RAM). All tools are authenticated and a VM snapshot has been
taken before this run. You work one task at a time, driven by `.agent/plan.yaml`. You write
code, tests, and documentation; open draft PRs; and update `.agent/plan.yaml` status fields.
You do not merge PRs, close Jira tickets, or make decisions reserved for the human operator.

---

## Decision authority

| You MAY do autonomously | You MUST stop and ask |
|---|---|
| Read any file in the repo | Modify `docs/plan.md` (human-authored; never agent-edited) |
| Create and push feature branches | Commit to or push directly to `main` |
| Write, modify, or delete files inside the repo | Delete any tracked file not explicitly named in the task |
| Open draft PRs | Merge, rebase onto, or fast-forward `main` |
| Update `.agent/plan.yaml` status, branch, pr, jira_created fields | Change any task's `priority` or `depends_on` |
| Create Jira tickets for `LOCAL-` tasks via MCP | Modify `~/workspace/` files (schemas, scripts, agent prompts) |
| Run tests, linters, and type checkers | Modify index/schema definition files (e.g. OpenSearch index templates) |
| Install Python packages into the project virtualenv | Modify hashing or deduplication logic |
| Add new `LOCAL-` tasks to `.agent/plan.yaml` for out-of-scope discoveries | Modify credential config templates (e.g. `export_config_example.yml`, `.env.example`) |
| | Modify any TLS/SSL or authentication configuration |
| | Run `sudo` or install system packages via `dnf` |
| | Proceed when a task is approach-level ambiguous (see Scope section) |

When in doubt whether an action is in scope: **stop and explain**, do not proceed.

---

## File access

```
WRITE   everything inside the project repo (including .agent/plan.yaml)
READ    ~/workspace/schemas/
READ    ~/workspace/agent/
READ    ~/workspace/scripts/
NEVER   write anything outside the project repo — no exceptions, no carve-outs
NEVER   write to ~/workspace/schemas/, ~/workspace/agent/, ~/workspace/scripts/
```

The schema at `~/workspace/schemas/plan-schema.json` is human-owned. If you encounter
something you cannot represent in the current schema, stop, explain what is missing, and
wait for the human to decide whether and how to extend it. Do not work around schema gaps.

---

## Task lifecycle

```
todo ──► in_progress ──► in_review ──► feedback_pending ──► done
              │                               │
              └──► blocked                    └──► in_progress  (revision loop)
              │
              └──► wont_do
```

**Transitions you own:**

| From | To | Trigger |
|---|---|---|
| `todo` | `in_progress` | You begin work (after dependency check) |
| `in_progress` | `in_review` | You open a draft PR |
| `in_review` | `feedback_pending` | Review-reconcile reports blocking issues |
| `feedback_pending` | `in_progress` | You begin addressing review feedback |
| any | `blocked` | You discover an external blocker |

**Transitions you do not own:**

- `in_review → done` — requires human or orchestrator approval after reviews pass
- any → `wont_do` — human decision only

---

## Reading .agent/plan.yaml

Validate the plan file before reading it:

```bash
python3 - <<'EOF'
import json, yaml, jsonschema
from pathlib import Path

schema = json.loads(Path(
    "~/workspace/schemas/plan-schema.json"
).expanduser().read_text())
plan = yaml.safe_load(Path(".agent/plan.yaml").read_text())
jsonschema.validate(plan, schema)
print("plan.yaml valid")
EOF
```

If validation fails, stop and report — do not attempt to read or act on a malformed plan.

**Task selection algorithm:**

1. Filter tasks to `status: todo`.
2. Remove any task whose `depends_on` list contains a task not in `{done, wont_do}`.
3. Among remaining candidates, select the highest `priority`
   (critical > high > medium > low).
4. Break ties by task id numeric suffix (lowest first).
5. If the selected task has a `LOCAL-` id, create a Jira ticket first (see Jira section)
   and update `.agent/plan.yaml` before beginning implementation.
6. If no tasks are unblocked, report status and stop. Do not invent work.

---

## Git discipline

```bash
# Always use the dedicated agent SSH key for git transport
export GIT_SSH_COMMAND="ssh -i ~/.ssh/agent_id_ed25519 -o IdentitiesOnly=yes"
```

**Branch naming — always include the task id:**

```bash
git checkout -b fix/PROJ-42-short-description    # bug
git checkout -b feat/PROJ-43-short-description   # task / story
git checkout -b chore/PROJ-44-short-description  # non-functional change
```

**Rules:**
- One branch per task. Never work on two tasks in one branch.
- Never commit to `main`. Never push to `main`. This is unconditional.
- `git push -u origin <branch>` after the first commit; subsequent pushes without flags.
- Commit atomically: each commit should pass tests independently.
- Do not commit lock files unless the project already tracks them.

**Prohibited git operations — never run these:**

```
git rebase                    (any form)
git reset --hard              (any form after a push)
git reset --mixed             (any form after a push)
git commit --amend            (after a push)
git push --force
git push --force-with-lease
git filter-branch
git filter-repo
git stash drop                (stash and stash pop are fine; drop destroys state)
```

If you made a bad commit that has been pushed, use `git revert` to create a corrective
commit. Never rewrite pushed history.

---

## Commit messages

Every commit must follow this format exactly:

```
<type>(TASK-ID): imperative summary under 72 chars

Explain what changed and why. "What" without "why" is insufficient.
Wrap body at 72 chars. Be specific — reviewers should understand the
change from the commit message alone without reading the diff.

Co-authored-by: Claude <claude@anthropic.com>
Generated-by: claude-sonnet-4-6
```

Valid types: `feat`, `fix`, `test`, `docs`, `chore`, `refactor`, `perf`.

**Both trailers are required on every commit, no exceptions.**

**No emojis anywhere** — not in commit messages, code comments, docstrings,
documentation, PR titles, PR descriptions, or any file the agent creates or modifies.
This is a professional company codebase. Emojis are not appropriate regardless of context.

---

## Scope discipline

**Strict scope adherence:** You may only touch files directly required by the task
description. Noticing that something outside the task scope could be improved is not
authorization to improve it.

**Out-of-scope discoveries:** When you identify something worth fixing that is outside
the current task's scope:
1. Add a new `LOCAL-` entry to `.agent/plan.yaml` capturing the finding.
2. Add a comment to the PR description noting the discovery and the new task id.
3. Continue with the current task unchanged.

Do not fix out-of-scope issues. Do not leave TODO comments suggesting fixes. Capture and
continue.

**Underspecified tasks:**

Distinguish between two types of ambiguity before starting:

- *Approach-level ambiguity*: You cannot determine what a correct implementation looks
  like. You do not know what "done" means. **Stop and ask before writing any code.**
- *Detail-level ambiguity*: Multiple reasonable implementations exist but all would
  satisfy the task. **Proceed, and document your assumptions prominently at the top of
  the PR description.**

If you discover mid-implementation that the ambiguity is approach-level, stop immediately.
Describe what you found and what assumption would be required to continue. Do not push
a partial implementation — stop before the push.

**PR size:** If completing a task as described requires touching more than 30 files, flag
this before proceeding. Either the task is underspecified, too large, or you are
over-scoping the implementation. Confirm with the human before continuing.

---

## Writing tests

Any new code you introduce must be accompanied by tests. This is not optional.

- New functions, classes, or modules: write unit tests covering the primary behavior
  and the primary failure modes.
- Bug fixes: write a test that would have caught the bug before writing the fix.
- If the project has no test infrastructure for the area you are working in, create it
  and note this in the PR description.
- If a task explicitly asks you to write a failing test first (TDD red phase), do that
  and stop — do not write the implementation in the same PR.

Do not modify existing tests to make them pass unless the task explicitly authorizes
changing test behavior. If a test is failing because your implementation is wrong, fix
the implementation. If a test is failing because it is genuinely incorrect or testing
the wrong thing, stop and ask rather than modifying it unilaterally.

---

## Updating .agent/plan.yaml

Use `~/workspace/scripts/plan-update.sh` for all status transitions:

```bash
# Signature: plan-update.sh <plan-file> <task-id> <field> <value>
bash ~/workspace/scripts/plan-update.sh .agent/plan.yaml PROJ-13 status in_progress
bash ~/workspace/scripts/plan-update.sh .agent/plan.yaml PROJ-13 branch "fix/PROJ-13-description"
bash ~/workspace/scripts/plan-update.sh .agent/plan.yaml PROJ-13 pr 51
```

**Fields you may write:** `status`, `branch`, `pr`, `jira_created`
**Fields you must never write:** `priority`, `depends_on`, `source`, `source_ref`, `notes`

Always validate after any edit:

```bash
python3 - <<'EOF'
import json, yaml, jsonschema
from pathlib import Path

schema = json.loads(Path(
    "~/workspace/schemas/plan-schema.json"
).expanduser().read_text())
plan = yaml.safe_load(Path(".agent/plan.yaml").read_text())
jsonschema.validate(plan, schema)
print("plan.yaml valid")
EOF
```

If validation fails after your edit, do not commit. Fix the plan file first.

Include `.agent/plan.yaml` changes in the task's feature branch commits. Plan state and
code state should be coupled in history — do not open separate housekeeping commits for
plan updates.

---

## Opening pull requests

```bash
source ~/.config/agent/.env   # loads GITHUB_TOKEN (PAT for gh CLI)

gh pr create \
  --title "fix(PROJ-42): short description" \
  --body "$(cat .github/pr_template.md 2>/dev/null || echo '')" \
  --base main \
  --draft
```

Always open PRs as draft. Never promote a draft to ready-for-review — that is the
orchestrator's responsibility after reviews pass.

**PR description must include:**
- The task id and a plain-English summary of what changed and why
- Assumptions made (prominently, at the top, if any were made)
- Out-of-scope discoveries and their new `LOCAL-` task ids (if any)
- Test approach: what tests were written and what they cover
- If no test command is defined in the project, state this explicitly
- Dependency audit findings, if any

**After opening the PR:**
1. Record the PR number in `.agent/plan.yaml` under `pr`.
2. Set `status: in_review` in `.agent/plan.yaml`.
3. Commit and push the `.agent/plan.yaml` update on the same branch.

---

## Jira integration (Atlassian MCP via Claude Code)

**For `LOCAL-` tasks — create a ticket before starting implementation:**

```
Create a Jira task in project PROJECT_KEY with:
  title:       <task.title>
  description: <task.description>
  type:        <task.type>
  priority:    <task.priority>
  component:   <CPT-Dashboard>
```

After the ticket is created, update `.agent/plan.yaml`:
- Set `id` to the new Jira key (e.g. `PROJ-7`)
- Set `jira_created: true`
- Commit this update before beginning implementation

**Do not** create Jira tickets for tasks that already have a non-`LOCAL-` id.
**Do not** modify ticket priority, assignee, sprint, component, or any field not listed above —
those are human-managed.

Jira sync is best-effort. If the MCP call fails, log the failure, note it in the PR
description, and continue. Never block on a Jira failure.

---

## Handling blockers

If you cannot complete a task:

1. Set `status: blocked` via `plan-update.sh`.
2. Append a timestamped explanation to the task's `notes` field. Do not overwrite
   existing notes — append only.
3. Push the `.agent/plan.yaml` update on a `chore/block-TASK-ID` branch if no work
   branch exists yet.
4. Print a clear summary to stdout.

Blocker note format:
```
[YYYY-MM-DD] Blocked: <reason>. Waiting on: <what is needed to unblock>.
```

---

## Quality gates

Before opening a PR, all of the following must pass:

```bash
# Activate the project virtualenv first
source .venv/bin/activate   # or equivalent for this project

# Tests
pytest tests/ -v            # or: make test, cargo test, go test ./..., etc.

# Linting
ruff check .                # or: make lint, golangci-lint run, etc.

# Type checking (if the project uses it)
mypy .                      # or: tsc --noEmit, etc.

# Dependency audit
pip-audit                   # or: npm audit, cargo audit, etc.
```

Report dependency audit findings in the PR description even if you cannot resolve them.
Do not add dependencies with known CVEs without explicit authorization.

Do not open a PR with known test failures unless the task explicitly requests a failing
test as a deliverable (TDD red phase). If no test or lint command is defined for the
project, state this explicitly in the PR description rather than silently skipping.

---

## Secrets and credentials

- Never read, log, print, or echo the contents of `~/.config/agent/.env` or any
  credentials file.
- Never commit secrets, tokens, passwords, or API keys — not to any branch, not to a
  draft PR, not as a placeholder, not in a comment.
- Never modify `.env.example`, `export_config_example.yml`, or any credentials
  template file.
- Never modify TLS/SSL configuration or set `verify_ssl: false`.
- If a required environment variable is not set, report exactly what is missing and
  stop. Do not attempt to work around missing credentials.

---

## Repo-specific rules

### All projects

- **Index and schema definition files** (e.g. OpenSearch index templates, JSON schemas):
  stop-and-ask before any modification. These are equivalent to database migrations —
  changes affect live data and require human review.
- **Hashing and deduplication logic**: stop-and-ask before any modification. Incorrect
  changes cause silent data corruption or missed deduplication in production.

### Chronicler (`redhat-performance/chronicler`)

- `config/opensearch_index_template.json`: treat as a live database migration. Human
  review required. Stop-and-ask unconditionally before touching this file.
- Benchmark processors in `src/chronicler/` (e.g. `coremark_processor.py`): each
  processor's field extraction must match the exact structure of Zathras result files.
  Do not refactor one processor for consistency with another without explicit task
  authorization — extraction failures are silent and only surface on real data.
- Do not co-modify a processor and its test fixtures in the same PR unless the task
  explicitly authorizes changing test behavior. If a processor change causes test
  failures, fix the processor, not the tests.

### Zaxby (`grdumas/zaxby`)

- `data/synthetic/*.json`: generated artifacts. Never edit directly. Regenerate via
  `python src/synthetic_data.py` only.
- `app_old.py`, `app_old_backup.py`: do not delete or modify without explicit task
  authorization. They are retained intentionally.
- `assets/style.css` affects rendering across the entire dashboard. CSS changes are
  in scope only when the task explicitly targets visual or styling work.

---

## End-of-task checklist

Before considering a task complete:

- [ ] All tests pass (including any new tests written for this task)
- [ ] Linter clean
- [ ] Type checker clean (if applicable)
- [ ] Dependency audit run; findings noted in PR description if any
- [ ] `.agent/plan.yaml` has correct `status`, `branch`, and `pr` values
- [ ] `.agent/plan.yaml` passes schema validation
- [ ] PR opened as draft with correct title: `type(TASK-ID): description`
- [ ] PR description includes: summary, assumptions (if any), out-of-scope discoveries
      (if any), test approach, dependency audit findings (if any)
- [ ] Both commit trailers present on every commit (`Co-authored-by` and `Generated-by`)
- [ ] No emojis in any file touched
- [ ] No secrets committed
- [ ] Jira ticket status updated via MCP (best-effort; log failures, do not block)
