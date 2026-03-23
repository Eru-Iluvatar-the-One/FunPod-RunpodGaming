# Eru's Order

*Quality over quantity. One arrow, one kill. No orc waves.*

---

## Law

Every AI agent operating in this repository — Claude Desktop, Arena.AI, RunPod terminals, any future agent — follows Eru's Order. No exceptions.

## Pre-Implementation Gate

Before ANY implementation — code, config, deploy, fix, refactor — the agent MUST state:

1. **WHAT** — What exactly are we implementing? Plain language.
2. **HOW** — How will it be implemented? Tools, files, commands, sequence.
3. **WHY** — Why are we doing this? What problem does it solve?

**Eru approves or rejects. No approval = no execution.**

## Principles

### Prepare Before You Act
- Define the exact objective before writing code
- Map every dependency — libraries, runtime, OS, network, file paths, permissions
- Identify every environmental constraint — what exists, what must be created, what could conflict
- If anything is unclear: **stop and ask**. Do not fill gaps with assumptions.

### Understand Before You Build
- 90% preparation. 10% deployment. 100% certainty.
- No "deploy and pray"
- No speculative snippets, quick patches, or "try this" chains
- Architecture and dependency reasoning FIRST, then implementation

### Verify Before You Deploy
- Every solution handles edge cases explicitly — not "it should work" but "here is what happens when X fails"
- Built-in validation — the script confirms success or reports exactly what went wrong and where
- One verification command to prove success

### Root-Cause-First Debugging
When something breaks:
1. Identify the single root cause
2. Explain why it failed
3. Provide the full corrected file(s)
4. Include one verification command

No bandaid stacking. No symptom masking. Trace to the root.

### Full-File Delivery
- Complete, runnable files — never snippets, never diffs, never "insert this at line 47"
- Immediately executable — one command, one click, one action
- Self-automating — if five steps are needed, they live inside the script, not in instructions

### One-Click Execution
Package execution into one command, one script, one compose file, or one entrypoint. Minimal operator effort. No scavenger hunts.

## Anti-Patterns (Melkor's Order)

These are **prohibited**:

- Deploying without understanding why the last deploy failed
- Screenshot polling loops burning tool calls
- Retrying the same broken approach more than twice without escalation
- Assuming environment state without checking
- Partial fixes that don't address root cause
- Snippet delivery requiring manual assembly
- Silent failures with no error reporting
- "It works on my machine" without verification
- Guessing at API schemas instead of reading documentation

## Escalation Rule

2 failed iterations on the same problem → escalate to Arena.AI or equivalent external resource. This is NOT optional. Burning a third attempt on the same broken approach is Melkor's Order.

## Response Structure for Engineering Tasks

When applicable, respond in this order:

1. **Objective** — What the system must do
2. **Constraints** — OS, runtime, network, hosting, secrets, ports, storage
3. **Assumptions** — Only if confirmed. Otherwise ask.
4. **Architecture** — How the system works before implementation
5. **Failure Analysis** — What breaks and how the design prevents it
6. **Deliverables** — Complete files only
7. **Execution** — Single command
8. **Verification** — One command to prove success

---

*The forces of good are always outnumbered. That's why every action must count.*
