#!/usr/bin/env bash
# Prepare a scoped external review on the owner's machine (Git Bash on Windows
# or any POSIX shell). Run from the repository root:
#
#   tools/review.sh <topic> [branch] [base]
#
# Fetches the branch, checks it out detached (so the reviewer can run tests),
# writes reviews/_diff.patch (excluding notes/, reviews/, dashboard/,
# 99-status.md, and lockfiles so author rationale, earlier dispositions, and
# generated files do not reach the reviewer), and prints the review commands.
set -euo pipefail

topic="${1:?usage: tools/review.sh <topic> [branch] [base]}"
branch="${2:-}"
base="${3:-origin/main}"
today="$(date -u +%Y-%m-%d)"

request="$(ls -1 reviews/requests/*"${topic}"*.md 2>/dev/null | grep -v TEMPLATE | tail -n 1 || true)"
if [ -z "${request}" ]; then
  echo "No review request matching '${topic}' in reviews/requests/." >&2
  exit 1
fi

start_ref="$(git rev-parse --abbrev-ref HEAD)"
git fetch --prune origin
if [ -n "${branch}" ]; then
  git switch --detach "origin/${branch}"
fi

git diff "${base}...HEAD" -- . \
  ':!dashboard/index.html' \
  ':!dashboard/register.toml' \
  ':!99-status.md' \
  ':!notes/' \
  ':!reviews/' \
  ':!*.lock' \
  ':!package-lock.json' \
  --output=reviews/_diff.patch

lines="$(wc -l < reviews/_diff.patch | tr -d ' ')"

prompt="Follow AGENTS.md and reviews/BRIEF.md. The review request is ${request}. Review reviews/_diff.patch against the directives and pass rule it names. Modify nothing except writing reviews/findings/${today}-${topic}-gemini.md in the brief's output format."

cat <<MSG

Request:  ${request}
Diff:     reviews/_diff.patch (${lines} lines, ${base}...HEAD, filtered)

1. Google Antigravity App (recommended, Gemini 4 Argon High):
   Open this repository in Antigravity, choose Request Review, and type:
     /review ${topic}

2. Google Antigravity CLI (headless):
   agy -p "${prompt}" < /dev/null
   (the agent writes the findings file itself; do not redirect stdout into it)

You are on a detached HEAD at the reviewed commit (you started on ${start_ref}).
After the review, commit and push the findings:
  git switch -c review/${today}-${topic}
  git add reviews/findings/${today}-${topic}-gemini.md
  git commit -m "review: ${topic}"
  git push -u origin HEAD
  git switch ${start_ref}
MSG
