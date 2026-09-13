# Roadmap

Forward-looking only. `CHANGELOG.md` records what's shipped; this records what might be next —
and it's not just bindings. Anything with real design detail gets its own file under
[`design/`](./design/), linked from here; anything smaller stays a line item. No status here
implies a commitment or a date — this is a place to put things down, not a promise.

## In design

- **The harness-binding mechanism** — the `runtime/bindings/<harness>/` discovery mechanism
  both bindings below sit on, including the deliberate decision that Claude Code's own wiring
  stays outside it. Build this first; it's how either binding below gets proven, not just
  proposed. [design/harness-binding-mechanism.md](./design/harness-binding-mechanism.md)
- **Google Antigravity binding** — now the priority (flipped 2026-09-13; see below). A third
  harness, on Antigravity's own (materially different) hook system; how many of the five it can
  answer is still open. [design/antigravity-binding.md](./design/antigravity-binding.md)
- **Gemini CLI binding** — paused, not abandoned. Design-wise it had fewer open unknowns than
  Antigravity, but personal Google-account sign-in to Gemini CLI is currently being rejected
  server-side, reproduced twice on 2026-09-13 — Google's own message points individual accounts
  at Antigravity instead. Paying for a metered API key would route around it but is a separate
  cost decision, declined for now. Revisit if that access situation changes.
  [design/gemini-cli-binding.md](./design/gemini-cli-binding.md)

## Considered, not started

- **A model-agnostic front end** (something that routes between Claude/Gemini/others under one
  session) needs no new Permanence work of its own once a harness has a binding — Permanence
  binds to *whatever runs the session* (hooks, shell, a global config file), not to the model
  behind it. Worth remembering if this comes up again: it's not a fourth binding, it's a
  consequence of the first three.
- F27 — `templates/` ships four of `SPEC.md`'s six canonical files (no `STRATEGY.md` or stream
  `README.md` skeleton). Logged in `CHANGELOG.md`'s `v1.3.0` entry as deliberately deferred.

## Explicitly out of scope for now

- **Gemini Mac app** ("Gemini Spark", relaunched 2026-07-01). Verified 2026-09-13: it runs
  agentic work on Google's own cloud servers against Workspace APIs, not local shell/git
  execution — architecturally unlike Claude Code/Cowork. Falls into the same manual-pointer tier
  as any plain chat surface today. Revisit only if that architecture changes.
- **Remote / multi-user support.** `SPEC.md`'s data model is explicitly single-owner
  (invariant 8 says this outright for programme groups too). A real redesign question, not an
  addition to slot in — not attempted here.
