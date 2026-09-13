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

PATHS=(runtime .githooks templates SPEC.md README.md QUICKSTART.md CHANGELOG.md ROADMAP.md design)   # machinery + the template's own planning docs
CURRENT=$(tr -d '[:space:]' < "$PERMA/_meta/VERSION" 2>/dev/null || echo "")
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

if [ -n "$LATEST_TAG" ] && [ "$CURRENT" = "$LATEST_TAG" ]; then
  echo "Already up to date."
  exit 0
fi

echo ""
echo "Changed machinery files (HEAD..$TARGET):"
CHANGED=$(git -C "$PERMA" diff --name-status HEAD "$TARGET" -- "${PATHS[@]}" 2>/dev/null)
if [ -z "$CHANGED" ]; then
  echo "  (none)"
else
  echo "$CHANGED" | sed 's/^/  /'
fi

# Individual changed files — everything below works file-by-file from here on, not by the
# top-level PATHS entry a file happens to live under. The old design skipped an entire directory
# (e.g. all of runtime/, every one of its ~20 scripts) from being applied just because ONE file in
# it conflicted; per-file tracking means only the actually-conflicting files are held back.
#
# Deletions (status D — the template no longer ships this path) are tracked separately and never
# go through conflict detection below: if the template removed it, it's removed on upgrade,
# customized or not. The alternative (treat a customized deleted file as a negotiated conflict,
# like a modified one) sounds more careful but isn't — conflict detection here is purely
# per-file with no concept of "feature", so a multi-release upgrade could surface several
# unrelated customized files as one flat, ungrouped list to reason about individually. Tolerable
# for an ordinary modified file; not worth it for a file the template doesn't support at all
# anymore. It's still visible either way, in the "Changed machinery files" diff printed above.
CHANGED_FILES=()
DELETED_FILES=()
while IFS=$'\t' read -r status path; do
  [ -n "${path:-}" ] || continue
  if [ "$status" = "D" ]; then
    DELETED_FILES+=("$path")
  else
    CHANGED_FILES+=("$path")
  fi
done <<< "$CHANGED"

# --- conflict detection: did YOUR history touch a changed path since your recorded version? ---
CONFLICTS=()
if [ "$CURRENT" != "unknown" ] && git -C "$PERMA" rev-parse -q --verify "$CURRENT" >/dev/null 2>&1; then
  for path in "${CHANGED_FILES[@]:-}"; do
    [ -n "$path" ] || continue
    if ! git -C "$PERMA" diff --quiet "$CURRENT" HEAD -- "$path" 2>/dev/null; then
      CONFLICTS+=("$path")
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
  echo ""
  echo "Dry run only — nothing changed. Re-run with --apply to fetch and commit the non-conflicted machinery changes."
  exit 0
fi

# --- apply: only the non-conflicted FILES; conflicted ones are left for /perma-upgrade to negotiate ---
APPLY_FILES=()
for f in "${CHANGED_FILES[@]:-}"; do
  [ -n "$f" ] || continue
  conflicted=false
  for c in "${CONFLICTS[@]:-}"; do
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
chmod +x "$PERMA/runtime/"*.sh "$PERMA/.githooks/"* 2>/dev/null
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
