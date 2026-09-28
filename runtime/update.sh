#!/usr/bin/env bash
# update.sh — the mechanical engine behind /perma-upgrade: tag-aware dry-run diff + conflict
# detection, then (only with --apply) refresh Permanence's MACHINERY from the template repo.
# Leaves your personal streams + registry + notes untouched, always.
#
# ONE-TIME SETUP: put your template git URL in ~/permanence/runtime/.update-source (already
# pre-filled if you cloned the public template) — or export PERMA_UPDATE_SOURCE.
#
# Usage:
#   update.sh              # dry-run (default): show what would change, exit 0, no writes
#   update.sh --apply      # fetch + apply the non-conflicted machinery changes, commit, bump VERSION
#
# It only ever touches machinery paths (runtime/, .githooks/, templates/, SPEC/README/QUICKSTART/
# CHANGELOG); it never touches your streams, _meta/REGISTRY, design notes, or gitignored runtime
# state (logs, search index, events outbox). A clean apply is committed to your Permanence's own
# git history (so it's revertable) and updates _meta/VERSION.
#
# Conflict detection: a machinery file is flagged, not overwritten, if YOUR history has touched it
# since the version recorded in _meta/VERSION — i.e. you customized it. /perma-upgrade negotiates
# those; this script only ever applies the clean paths.
#
# Migration notes (CHANGELOG.md sections that may need stream-content changes, not just machinery)
# are deliberately NOT parsed here — reading and proposing those against your actual streams needs
# judgment, which is /perma-upgrade's job, not this script's.
set -uo pipefail
PERMA="${PERMA_DIR:-$HOME/permanence}"
BRANCH="${PERMA_UPDATE_BRANCH:-main}"
SRC="${PERMA_UPDATE_SOURCE:-$(tr -d '[:space:]' < "$PERMA/runtime/.update-source" 2>/dev/null)}"
MODE="dry-run"
[ "${1:-}" = "--apply" ] && MODE="apply"

[ -n "$SRC" ] || { echo "No update source set. Put your template git URL in $PERMA/runtime/.update-source (or export PERMA_UPDATE_SOURCE)."; exit 1; }
git -C "$PERMA" rev-parse --git-dir >/dev/null 2>&1 || { echo "$PERMA is not a git repo."; exit 1; }
if [ "$MODE" = "apply" ] && { ! git -C "$PERMA" diff --quiet || ! git -C "$PERMA" diff --cached --quiet; }; then
  echo "Your Permanence has uncommitted changes — commit or stash them first, then re-run --apply (so the machinery update lands cleanly)."
  exit 1
fi

PATHS=(runtime .githooks templates SPEC.md README.md QUICKSTART.md CHANGELOG.md design)   # machinery + the template's own planning docs
# 2>/dev/null must come before the < redirect: bash reports a missing input file's "No such file
# or directory" to whatever stderr is in effect at the moment the < redirect is processed, in
# left-to-right order — with 2>/dev/null written after it (the original order here), that report
# already escaped to the real terminal/log before the suppression took effect. Verified
# empirically, not just reasoned about. Found by adversarial review, 2026-09-28
# (axis/runs/2026-09-28-v1.5.0-update-sh-review) — pre-existing since before v1.5.0, out of that
# PR's own diff, fixed here anyway since it's the same file and the same review pass.
CURRENT=$(tr -d '[:space:]' 2>/dev/null < "$PERMA/_meta/VERSION" || echo "")
[ -n "$CURRENT" ] || CURRENT="unknown"

echo "fetching from $SRC ($BRANCH) ..."
# Explicit if/else, not `get-url && set-url || add`: that chain falls through to `add` (which then
# fails — "remote already exists") whenever the remote exists but set-url itself fails for an
# external reason (a git config lock, a malformed URL) — not just when the remote is genuinely absent.
if git -C "$PERMA" remote get-url _machinery >/dev/null 2>&1; then
  git -C "$PERMA" remote set-url _machinery "$SRC"
else
  git -C "$PERMA" remote add _machinery "$SRC"
fi
# --force on the tags: _machinery is single-purpose (only ever used to check for updates), so its
# tags are always authoritative here — nothing in this install relies on a *local* tag under one of
# these names (_meta/VERSION is the real version record). Without --force, a fetch fails outright,
# with a generic "check the URL/access" message, if a local tag of the same name ever points at a
# different commit than upstream's — which reads as a network/auth problem but is neither: it can
# happen after any source-side history rewrite (rebase, filter-repo, a force-pushed tag), or just an
# old install that tagged something locally before ever pulling upstream's tags.
git -C "$PERMA" fetch -q --force --tags _machinery "$BRANCH" || { echo "Fetch failed — check the URL/branch and your access to the repo."; exit 1; }

LATEST_TAG=$(git -C "$PERMA" tag --merged FETCH_HEAD --sort=-v:refname 2>/dev/null | head -1)
TARGET="${LATEST_TAG:-FETCH_HEAD}"
echo "installed: $CURRENT  →  latest: ${LATEST_TAG:-"(untagged, using $BRANCH HEAD)"}"

# --no-renames: a rename line has TWO tab-separated paths ("R100<TAB>old<TAB>new"), which the
# `read -r status path` loop below took as one path containing a tab. Checkout of that path failed
# silently (`|| true`), so upstream's templates/*.md -> *.template.md rename never landed and nothing
# said so. Without rename detection it arrives as D old + A new, and each half is handled normally.
CHANGED=$(git -C "$PERMA" diff --no-renames --name-status HEAD "$TARGET" -- "${PATHS[@]}" 2>/dev/null)

# Deliberately no early-exit on CURRENT == LATEST_TAG alone — that string comparison is exactly
# what let the tracked-path bug this file's own history records go undetected: _meta/VERSION can
# claim the target while real content for a newly-tracked path still hasn't landed. Confirm
# against the actual diff instead, every time; it's a cheap local git operation once already
# fetched, not worth trusting a cached string to skip.
if [ -z "$CHANGED" ]; then
  echo ""
  echo "Already up to date."
  exit 0
fi

echo ""
echo "Changed machinery files (HEAD..$TARGET):"
echo "$CHANGED" | sed 's/^/  /'

# Individual changed files — everything below works file-by-file from here on, not by the
# top-level PATHS entry a file happens to live under. The old design skipped an entire directory
# (e.g. all of runtime/, every one of its ~20 scripts) from being applied just because ONE file in
# it conflicted; per-file tracking means only the actually-conflicting files are held back.
#
# Deletions (status D — the template no longer ships this path) are tracked separately from the
# CHANGED_FILES conflict detection below, but a customized path that the template deletes or
# renames away IS routed into CONFLICTS (see the check inside the loop) rather than applied blind
# — the same "you changed it, so it needs review" rule every other bucket in this file already
# follows. Only a deletion of a path you never touched applies automatically.
CHANGED_FILES=()
DELETED_FILES=()
KEPT_FILES=()
CONFLICTS=()
while IFS=$'\t' read -r status path; do
  [ -n "${path:-}" ] || continue
  if [ "$status" = "D" ]; then
    # HEAD..TARGET shows a path as "D" whenever HEAD has it and TARGET does not — which is true both
    # when the template removed it AND when you added it yourself. Only the first is a deletion. A
    # path counts as template-deleted only if the template shipped it at your recorded version
    # ($CURRENT). Anything else is yours, and is kept. Found 23 September 2026: a v1.2.1 -> v1.4.0
    # dry run would have deleted 8 files the owner had added (a personal role file, a set of
    # scripts) although the template deleted nothing in that range.
    if [ "$CURRENT" != "unknown" ] && git -C "$PERMA" cat-file -e "$CURRENT:$path" 2>/dev/null; then
      # The template shipped this path at your recorded version and no longer does — a genuine
      # deletion (or rename-away) candidate. But if YOU changed this path since $CURRENT, applying
      # that unconditionally would silently destroy your edit — no flag, no warning — exactly the
      # case a modified-but-not-deleted file is already protected from below. Route it to
      # CONFLICTS instead. Found by adversarial review, 2026-09-28
      # (axis/runs/2026-09-28-v1.5.0-update-sh-review), live-reproduced twice: a template deletion
      # and a template rename-away of a file the owner had customised were both previously applied
      # silently.
      if git -C "$PERMA" diff --quiet "$CURRENT" HEAD -- "$path" 2>/dev/null; then
        DELETED_FILES+=("$path")
      else
        CONFLICTS+=("$path")
      fi
    else
      KEPT_FILES+=("$path")
    fi
  else
    CHANGED_FILES+=("$path")
  fi
done <<< "$CHANGED"

if [ "${#KEPT_FILES[@]}" -gt 0 ]; then
  echo ""
  echo "🛡  ${#KEPT_FILES[@]} file(s) you added are not in the template and will be KEPT, not deleted:"
  printf '  %s\n' "${KEPT_FILES[@]}"
fi

# --- conflict detection: three buckets, decided per file against your recorded version ---
#   you changed it, the template changed it   -> CONFLICTS  (negotiated in /perma-upgrade)
#   you changed it, the template did NOT      -> YOURS      (left exactly as it is; nothing to decide)
#   the template changed it, you did NOT      -> applied
# Before v1.5.0 the middle case was flagged as a conflict: every customised file was reported as
# "needs review" on every run, even when already up to date, so real conflicts hid among permanent
# false ones. It must NOT simply fall through to "applied" either — that would overwrite your
# customisation with a template version that has not changed. Hence its own bucket.
# CONFLICTS is declared and possibly already populated above (customized deletions/renames) —
# not re-initialized here, so those entries survive.
YOURS_FILES=()
if [ "$CURRENT" != "unknown" ] && git -C "$PERMA" rev-parse -q --verify "$CURRENT" >/dev/null 2>&1; then
  for path in "${CHANGED_FILES[@]:-}"; do
    [ -n "$path" ] || continue
    if ! git -C "$PERMA" diff --quiet "$CURRENT" HEAD -- "$path" 2>/dev/null; then
      if git -C "$PERMA" diff --quiet "$CURRENT" "$TARGET" -- "$path" 2>/dev/null; then
        YOURS_FILES+=("$path")
      else
        CONFLICTS+=("$path")
      fi
    fi
  done
else
  # No usable recorded version, so there is no way to tell "you customized this" from "the
  # template changed this" — treat every changed file as needing review rather than applying
  # anything blind. SPEC.md's guarantee is "negotiated per file, never silently overwritten";
  # failing open here (apply everything, since nothing LOOKS conflicted) would break that
  # guarantee the moment VERSION goes missing or points at a commit this clone doesn't have.
  if [ "$CURRENT" = "unknown" ]; then
    echo "  (note: no recorded version — treating all ${#CHANGED_FILES[@]} changed file(s) as needing review, not applying any blind)"
  else
    echo "  (note: recorded version $CURRENT isn't a known ref here — treating all ${#CHANGED_FILES[@]} changed file(s) as needing review, not applying any blind)"
  fi
  CONFLICTS=("${CHANGED_FILES[@]:-}")
fi

if [ "${#YOURS_FILES[@]}" -gt 0 ]; then
  echo ""
  # "left exactly as they are" is accurate for the ordinary case (path unchanged); if you renamed
  # or removed this path yourself since $CURRENT (the template never touched it either way), this
  # script made no change to it — nothing lost, your content survives wherever you put it, but the
  # path below may no longer exist here. Wording loosened after adversarial review, 2026-09-28
  # (axis/runs/2026-09-28-v1.5.0-update-sh-review) found the old blanket phrasing was inaccurate
  # for that case.
  echo "🛡  ${#YOURS_FILES[@]} file(s) you customised that the template did not change — this script made no change to them (if you've since renamed or removed one yourself, that's untouched too — it just may not exist at the path below anymore):"
  printf '  %s\n' "${YOURS_FILES[@]}"
fi

if [ "${#CONFLICTS[@]}" -gt 0 ]; then
  echo ""
  echo "⚠️  ${#CONFLICTS[@]} file(s) need review before being applied (customized locally, or the customization check itself was unavailable):"
  printf '  %s\n' "${CONFLICTS[@]}"
fi

if git -C "$PERMA" diff --name-only HEAD "$TARGET" -- CHANGELOG.md 2>/dev/null | grep -q .; then
  echo ""
  echo "📋 CHANGELOG.md changed in this range — check it for a Migration notes section before applying."
fi

if [ "$MODE" = "dry-run" ]; then
  if printf '%s\n' "${CHANGED_FILES[@]:-}" | grep -qx "runtime/update.sh"; then
    echo ""
    echo "ℹ️  runtime/update.sh itself is in this range — --apply may take one extra internal step"
    echo "   (re-checking with the updated script) before everything above is fully delivered."
  fi
  echo ""
  echo "Dry run only — nothing changed. Re-run with --apply to fetch and commit the non-conflicted machinery changes."
  exit 0
fi

# Only chmod the files THIS run actually checks out — the previous unscoped
# `chmod +x "$PERMA/runtime/"*.sh "$PERMA/.githooks/"*` set the same executable bit on every
# runtime/.githooks file whether this run touched it or not (KEPT, YOURS, untouched alike),
# leaving the working tree dirty after every --apply and blocking the very next --apply (which
# refuses to run over uncommitted changes) — exactly the "resolve a conflict, then re-run"
# workflow this release is built around. Found by adversarial review, 2026-09-28
# (axis/runs/2026-09-28-v1.5.0-update-sh-review), live-reproduced.
chmod_applied_scripts() {  # chmod_applied_scripts <path>...
  local f
  for f in "$@"; do
    case "$f" in
      runtime/*.sh|.githooks/*) [ -f "$PERMA/$f" ] && chmod +x "$PERMA/$f" ;;
    esac
  done
}

# --- apply: only files the template changed and you did not; conflicts wait for /perma-upgrade, YOURS stay put ---
APPLY_FILES=()
for f in "${CHANGED_FILES[@]:-}"; do
  [ -n "$f" ] || continue
  conflicted=false
  for c in "${CONFLICTS[@]:-}" "${YOURS_FILES[@]:-}"; do
    [ -n "$c" ] && [ "$c" = "$f" ] && { conflicted=true; break; }
  done
  $conflicted || APPLY_FILES+=("$f")
done

# Guard the expansion itself, not just its contents: bash 3.2 (still macOS's /bin/bash) raises
# "unbound variable" under set -u on "${arr[@]}" when arr is a DECLARED-BUT-EMPTY array — not a
# hypothetical, reproduced on this machine. Checking length first sidesteps the bug entirely for
# every array below, rather than relying on the `:-` fallback (which itself needs the `-n` guards
# above to skip the one spurious empty-string element it introduces).
if [ "${#APPLY_FILES[@]}" -gt 0 ]; then
  git -C "$PERMA" checkout -q "$TARGET" -- "${APPLY_FILES[@]}" 2>/dev/null || true
fi
# Deletions always apply, unconditionally — see the note where DELETED_FILES is built above.
if [ "${#DELETED_FILES[@]}" -gt 0 ]; then
  git -C "$PERMA" rm -q -- "${DELETED_FILES[@]}" 2>/dev/null || true
fi

# If update.sh itself just landed, everything computed above (PATHS, CHANGED_FILES, CONFLICTS)
# came from the OLD script and no longer reflects the truth — a release that adds a whole new
# tracked path (not just changes an existing one) means the OLD PATHS array never even looked
# for it, so this run's view of "what changed" is incomplete by construction, not just stale.
# Left alone, the block below would still write VERSION = LATEST_TAG (nothing in the CURRENT
# CONFLICTS list blocks it) — falsely claiming full currency while the untracked-until-now paths
# are silently never delivered: the next run sees CURRENT == LATEST_TAG and stops at "Already up
# to date" before ever looking again. Reproduced directly (not reasoned about): a scratch install
# genuinely reached that false "up to date" state with a real new top-level path missing.
# Fix: commit only what THIS run found (never VERSION — that would be the false claim), then
# re-exec the just-updated script so it re-checks from a clean slate against its own current path
# list. Depth-guarded, though this should resolve in exactly one hop: after the commit below,
# update.sh's checked-out content already matches TARGET, so the re-exec's own diff won't see
# itself as changed a second time.
self_updated=false
for f in "${APPLY_FILES[@]:-}"; do
  [ "$f" = "runtime/update.sh" ] && self_updated=true && break
done
if $self_updated; then
  chmod_applied_scripts "${APPLY_FILES[@]:-}"
  git -C "$PERMA" add "${APPLY_FILES[@]}" 2>/dev/null
  if ! git -C "$PERMA" diff --cached --quiet; then
    git -C "$PERMA" commit -q -m "perma-upgrade: machinery refreshed (update.sh itself changed — continuing with the updated script) ($SRC)"
  fi
  DEPTH="${_PERMA_UPDATE_REEXEC_DEPTH:-0}"
  if [ "$DEPTH" -ge 3 ]; then
    echo "update.sh kept changing across $DEPTH re-runs without settling — stopping rather than looping forever. Run /perma-upgrade again by hand to continue." >&2
    exit 1
  fi
  echo ""
  echo "runtime/update.sh itself just changed — re-checking with the updated script to see what it now tracks ..."
  export _PERMA_UPDATE_REEXEC_DEPTH=$((DEPTH + 1))
  exec bash "$PERMA/runtime/update.sh" --apply
fi

chmod_applied_scripts "${APPLY_FILES[@]:-}"
echo "re-running install.sh (re-wires hooks + commands) ..."
bash "$PERMA/runtime/install.sh"
mkdir -p "$PERMA/_meta"

# Only advance the recorded version when EVERY changed file in this range actually landed. A
# partial apply (some files held back as conflicts) is real progress, but it is not "you're now
# at LATEST_TAG" — bumping VERSION anyway would make the next run's up-to-date short-circuit
# (above) report "Already up to date" forever, hiding the still-outstanding files for good.
if [ "${#CONFLICTS[@]}" -eq 0 ]; then
  printf '%s' "${LATEST_TAG:-$TARGET}" > "$PERMA/_meta/VERSION"
  git -C "$PERMA" add "$PERMA/_meta/VERSION" 2>/dev/null
fi
if [ "${#APPLY_FILES[@]}" -gt 0 ]; then
  git -C "$PERMA" add "${APPLY_FILES[@]}" 2>/dev/null
fi

# install.sh (just called above) chmod's every runtime/.githooks/bindings script unconditionally
# as its own regular-install behavior — real, useful there, but it can leave mode-only noise on
# machinery paths this run didn't otherwise touch. The working tree was guaranteed clean when
# this script started (the uncommitted-changes guard at the top), so anything dirty now was
# caused by this run; stage it, scoped to the machinery paths this script is allowed to touch, so
# it lands in this same commit instead of blocking the very next --apply. Found by adversarial
# review, 2026-09-28 (axis/runs/2026-09-28-v1.5.0-update-sh-review), live-reproduced.
#
# `git add -A -- <pathspecs>` is all-or-nothing: ONE pathspec in the list that matches nothing
# (a genuinely empty PATHS entry, e.g. no design/ on an older install) makes git stage NOTHING at
# all from the whole list, silently, since this call is `2>/dev/null` — found live while verifying
# this very fix, not assumed. Filter to paths that actually exist first.
EXISTING_PATHS=()
for p in "${PATHS[@]}"; do
  [ -e "$PERMA/$p" ] && EXISTING_PATHS+=("$p")
done
if [ "${#EXISTING_PATHS[@]}" -gt 0 ]; then
  git -C "$PERMA" add -A -- "${EXISTING_PATHS[@]}" 2>/dev/null
fi

if git -C "$PERMA" diff --cached --quiet; then
  if [ "${#CONFLICTS[@]}" -gt 0 ]; then
    echo "Nothing applied — every changed file is flagged for review above; none applied blind."
  else
    echo "Already up to date — no machinery changes."
  fi
elif [ "${#CONFLICTS[@]}" -eq 0 ]; then
  git -C "$PERMA" commit -q -m "perma-upgrade: machinery refreshed to ${LATEST_TAG:-$TARGET} ($SRC)"
  echo "✅ Machinery updated to ${LATEST_TAG:-$TARGET} and committed; your streams are untouched. Start a fresh session so the new hooks load."
else
  git -C "$PERMA" commit -q -m "perma-upgrade: partial machinery update, ${#CONFLICTS[@]} file(s) left for review ($SRC)"
  echo "✅ ${#APPLY_FILES[@]} non-conflicting file(s) updated and committed; recorded version stays $CURRENT until the ${#CONFLICTS[@]} flagged file(s) below are resolved."
fi
if [ "${#CONFLICTS[@]}" -gt 0 ]; then
  echo ""
  echo "⚠️  ${#CONFLICTS[@]} file(s) left for review (see above) — resolve them with /perma-upgrade, then re-run to finish and advance the version."
fi
