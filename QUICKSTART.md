# QUICKSTART

Six steps to a working Permanence. ~10 minutes.

## 1. Put it at `~/permanence`

From GitHub:

```bash
git clone https://github.com/lotusboy/permanence.git ~/permanence
cd ~/permanence && rm -rf .git && git init && git add -A && git commit -m "My Permanence"
```

Or, if you were handed a copy of the folder rather than the link:

```bash
cp -R <the-folder> ~/permanence
cd ~/permanence && rm -rf .git && git init && git add -A && git commit -m "My Permanence"
```

**The install location is always `~/permanence`** — every script assumes it. (Override with
`PERMA_DIR` only if you genuinely need it elsewhere.)

**Why `.git` gets thrown away.** Your Permanence fills with private notes about real projects and real
people, so it becomes *your* repository with *your* history — not a fork of the template, and never
something you'd push back upstream. The initial commit matters too: it's what arms the git hooks and
lets the install stamp a version on the commands. You can still pull future template improvements —
`/perma-upgrade` reads the upstream URL from `runtime/.update-source`, a tracked file, not from the git
remote you just removed.

> **Platform notes.** Works on macOS and Linux with no changes. On **Windows**, use Claude Code with
> **Git for Windows** installed (it bundles Git Bash, which Claude Code uses to run these scripts
> automatically) — `~/permanence` resolves correctly under Git Bash the same way it does on macOS/Linux.
> If your Windows profile is redirected into a OneDrive-synced folder, consider moving `~/permanence`
> somewhere not continuously cloud-synced — a git repo and a sync client both wanting to touch the same
> files can cause odd behavior.

## 2. Back up before you forget

**This is the point where it matters most, so it's worth doing now rather than "eventually."** The
`.git` history you just created is local-only — there's no remote, and nothing here sets one up.
`runtime/make-backup.sh` gives you an encrypted, round-trip-verified backup **on this machine**, ready
to copy somewhere else: it bundles the whole history, encrypts it to a key only you hold, verifies it
restores before trusting it, and keeps the last three locally in `~/Backups`. **Copying that file off
the machine is the step it can't do for you** — put it on your Drive (or equivalent) and keep three
there; a blob sitting in `~/Backups` dies with the laptop like everything else. The one-time setup and
restore steps are in the comment at the top of the script itself.

It needs the `age` encryption tool, which isn't preinstalled:

```bash
brew install age                                  # or your package manager's equivalent
age-keygen -o ~/.config/age/perma-backup.key      # one-time — store this key safely, separately from the backup
~/permanence/runtime/make-backup.sh
```

It writes **two** files: your Permanence history, and a small second blob of the `~/.claude` state
`install.sh` can't rebuild (settings, memory files, any skill credentials) — treat both as secrets.

It's **not** run automatically — `install.sh` doesn't schedule it, and it checks your working tree
before bundling, telling you plainly if anything's uncommitted (run `/perma-shutdown` first, or commit
by hand, for a backup that covers everything). Re-run it any time; a weekly cron/launchd entry alongside
the nightly consolidate is a reasonable default once you've got real notes worth losing. If this machine
is the only copy and something happens to it, losing the machine loses everything — getting the result
off it is the whole difference.

## 3. Explore the example

Open `~/permanence/example/` and read a stream or two (`home/bathroom`, `home/kitchen`) — that's the
shape and the conventions in action. Worth a proper look now: `example/.consolidation/REPORT-example.md`
shows what a real `/perma-consolidate` pass actually produces, and `example/_meta/emergent.md` shows what
`/perma-orchestrate` finds. Keep it around through step 6 below — you'll want it again.

## 4. Install the machinery

```bash
~/permanence/runtime/install.sh
```

This sets up everything global and hands-off. Specifically, it:

- copies the `/perma-*` commands into `~/.claude/commands/`
- points this repo's `core.hooksPath` at `.githooks` (the people-rule guard + contents refresh)
- schedules the nightly consolidate (05:30)
- merges two hooks and the `~/permanence` permission into `~/.claude/settings.json` — **SessionStart**
  (`session-start.sh`) and **UserPromptSubmit** (`session-load.sh`, the one that actually forces the
  read on your first message)
- adds a delimited `<!-- perma:begin … end -->` block to your global `~/.claude/CLAUDE.md`, and the
  same block to `~/.config/agents/AGENTS.md` (plus Codex/droid/Amp's global `AGENTS.md` if those are
  installed) — never a project's own committed `AGENTS.md`

Every one of these is a merge, not an overwrite: your other settings are left alone, files are backed
up before any in-place edit, and it's safe to re-run any time. *(Without `python3` it prints the
settings.json snippet for you to paste instead.)*

## 5. Register your first project

How this works depends on what you're using — pick the one that matches you:

**Using Claude Code, via VS Code or the CLI (probably you, if you're a software engineer).** Your
working directory already *is* your project — open the project as your VS Code workspace, or `cd` into
it before running `claude`. No extra step needed: just open the project and say **"register this
project"**.

**Using a desktop app with local file access (Claude Desktop, ChatGPT Desktop, or similar).** Don't rely
on the app's own folder/workspace concept — it varies by app, and Permanence doesn't know about it
either way. If there's a real folder for this project, just say its path: **"register this project at
`/Users/you/path/to/it`"**. That works identically no matter how the app itself scopes file access. If
there's no folder at all — a topic you just want to think out loud about — a name is enough: **"start a
new project called kitchen renovation"**. No path, no folder to think about; Permanence picks a real
folder for you (under `~/Permanence Projects/`) and tells you where, in case you ever want it.

**Either way**, from there it's the same:

> **"Register this project in Permanence"** — and point it at the README if there is one: *"…here's the README: `<path>`"* (or the explicit path, if you're using a desktop app per above).

You don't need to tell it where Permanence is (always `~/permanence`) or run any command — Claude already knows to offer this. It reads the README, creates the stream seeded from it (PROJECT/LOG/QUESTIONS/PEOPLE), adds it to the registry, and confirms. No README? Just describe it ("set up a stream for doing up the bathroom") and it builds the stream from that.

That's it. **Next time you open that project, Permanence loads its context automatically.**

A couple of things worth knowing:

- **If you skip setting a real project path, the session lands in your home folder**, and registering *that* would make every home-defaulted session load a meaningless stream. Permanence now refuses to register a home/container folder and tells you to set the folder instead — but replacing `/Users/you` with your real home path in `_meta/REGISTRY.md`'s `perma-meta` row is still worth doing, so home sessions cleanly get brief-level access.
- **Deleting a session is safe.** A session is just the conversation — deleting it leaves the folder, its files, your Permanence stream and the registry untouched. Point a new session at the same folder and it picks straight up. That's rather the point.
- **A project isn't tied to one app.** Once it's registered, the same project is reachable both ways — open its folder in VS Code, or just say its name in a desktop app — it's the same stream either way, no extra setup per app.
- **Desktop-app users: `/perma-startup` and `/perma-shutdown` take a project name *or* a path** — say *"good morning Permanence, kitchen renovation"* or give the folder path, whichever you remember, instead of relying on the app's folder to pick the project for you. Not sure of the exact name? Ask to **"list my Permanence projects"** first (`/perma-list`). Switching projects mid-conversation is just calling it again with a different name — Permanence will check first if the one you're leaving still has anything worth winding down.

## 6. Then just use it

**Talk to Claude about the project as you work** — it keeps the stream updated. Run `/perma-brief` of a morning for the across-everything picture; `/perma-consolidate` occasionally to tidy. Ignore `/perma-orchestrate` until you've got a few streams.

**`/perma-help` any time you've forgotten what's available** — it lists every command and shows which background pieces are actually switched on for *your* machine, so you're never guessing.

**A daily pair worth trying early:** `/perma-shutdown` when you stop (it gets the day's open loops out of your head and into the stream, with exact resume points), and `/perma-startup` when you start (where you left off, plus a couple of candidates for what's next). They're the two that make Permanence feel like it's carrying something for you rather than being another thing to maintain.

**Optional — a weekday reminder.** `~/permanence/runtime/shutdown-nudge.sh --install 17:00` pings you Mon–Fri to run `/perma-shutdown` (`--uninstall` to stop). Worth it in week one, while the habit is still new.

**The nightly tidy needs a token.** `install.sh` schedules a nightly consolidate (05:30) that runs Claude unattended. Scheduled jobs get no shell config, so it can't see your normal login — give it a token of its own:

```bash
claude setup-token                       # prints a token
mkdir -p ~/.config/perma
echo 'export CLAUDE_CODE_OAUTH_TOKEN=<paste-it-here>' > ~/.config/perma/claude-code-oauth-token.env
chmod 600 ~/.config/perma/claude-code-oauth-token.env
```

Keep it in that file rather than your shell profile — in your profile it can leak into other tools and override your normal Claude Code login. Already keep it somewhere else? Set `PERMA_TOKEN_ENV` to that path instead. Skip this and the nightly run simply aborts each night with a message telling you the same thing — it will **never** fall back to an API key.

**Optional — cross-project events.** Once you've got two or more projects you switch between, you can let one quietly tell the others when something material happens (`/perma-emit`), so the Claude in your other open project picks it up next time you type there. *Emitting* works out of the box; *receiving* is opt-in — `install.sh` prints the **two** `settings.json` hook lines to enable it; add both, since they share one cursor so a message still arrives exactly once (both run on every prompt, so they're left for you to switch on deliberately). Skip this until you actually feel the "I changed X over here and forgot to tell the other project" pain.

**Programme groups, for a tech lead tracking a team's repos (`/perma-register-group`).** No setup step to skip here — it's just a command that sits inert until you actually use it, not a toggle. Still one owner's own Permanence, tracking several repos from one vantage point (clone them locally so `/perma-register-group` can read each one's `git log`) — nobody else on the team needs to run Permanence at all. `/perma-shutdown` in *any* member repo then refreshes one shared plan-and-status folder in the coordinating repo, written for a reader who isn't in the work (a manager or director) — it converges, so you never have to be in the "right" repo. (Not for coordinating different people's own laptops — see the README for why.) Reach for this only once a programme spans more than one repo and somebody outside the work keeps asking where things are.

---

**The honest bit:** the real payoff is *your own* Permanence after a week or two, once it's holding state you'd otherwise lose. The example is just the bridge across the "empty Permanence, can't see the point yet" valley. Get one real stream going and let it accumulate.

Once it has — you don't need the example anymore:

```bash
rm -rf ~/permanence/example
```
