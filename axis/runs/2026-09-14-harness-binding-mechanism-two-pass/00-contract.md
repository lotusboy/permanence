# Axis Contract — harness-binding-mechanism Two-Pass review

```
AXES:         Pass 1: Seven Factors of Awakening + Genba, Fowler's Refactoring Catalog + SOLID,
              Pre-mortem + Muda, MECE + Pyramid Principle
              Pass 2: Genba + Shoshin, Andon + Chaos Engineering, Poka-yoke
TARGET:       PR #13 — the full diff from `main` (81eef19) to `add-roadmap-and-adapter-designs`
              (1a43d4c) in /Users/lotusboy/workspaces/permanence. 33 files, ~2,700 insertions,
              41 commits. Primary: the mechanism and its five implementations —
              runtime/lib/block-merge.sh, runtime/install.sh, runtime/bindings/**/* (detect/wire
              scripts and hook translators for claude-code, antigravity, devin, cursor),
              .github/workflows/ci.yml. Secondary: design/*.md, docs/TOOL-SUPPORT.md, SPEC.md,
              CHANGELOG.md — check these for internal consistency and claims the code doesn't
              support, not for re-verifying live-fire testing that already happened outside a
              repo diff.
STRUCTURE:    Pyramid — BLUF, then findings ranked by severity, most severe first
EVIDENCE:     file:line for every finding, verbatim snippet where the defect is non-obvious
ASSUMPTIONS:  Maintain a Verified/Unknown ledger. Flag anything asserted in docs/commit messages
              that isn't independently checkable by reading the code.
STOP:         Andon — halt and flag immediately on any data-loss or security defect found (e.g. a
              write that can clobber user data without backup, a credential handled unsafely, a
              destructive operation without confirmation)
```

## Why this PR gets a Two-Pass, not a single pass

Architecture-review scale: this PR changes how *every* AI-tool binding gets wired
(`install.sh` reduced to a generic discovery loop) and migrates Claude Code's own wiring — the one
binding every install depends on — into that same generic mechanism. It touches shared
infrastructure (`install.sh`, a shared library, CI) and adds five independent binding
implementations, each parsing/writing a different tool's own JSON config format. This is exactly
the profile `two-pass-strategy.md` names for Two-Pass over single-pass: "architecture reviews...
anything touching shared infrastructure."

## Isolation

Pass 1 and Pass 2 run as separate, freshly-spawned subagents with no shared context and no access
to each other's conversation. Pass 2's prompt (`02-pass2-prompt.md`) does not mention Pass 1's
findings and Pass 2 is explicitly instructed not to read anything under `axis/runs/` before
writing its own output. This is enforced structurally, not just by instruction — each pass is a
genuinely separate agent invocation.
