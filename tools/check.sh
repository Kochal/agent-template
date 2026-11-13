#!/usr/bin/env bash
# Repository verification suite. Run before every push (AGENTS.md section 7).
# Install as a pre-push hook once per clone: git config core.hooksPath tools/hooks
set -euo pipefail
cd "$(dirname "$0")/.."

# Pick an interpreter that actually runs and has tomllib. On Windows, `python3`
# can be the Microsoft Store stub, which exists on PATH but exits with 49.
PYTHON_BIN=""
for candidate in python3 python py; do
  if "$candidate" -c 'import sys; sys.exit(sys.version_info < (3, 11))' >/dev/null 2>&1; then
    PYTHON_BIN="$candidate"
    break
  fi
done
if [ -z "$PYTHON_BIN" ]; then
  echo "check.sh: need Python 3.11+ as python3, python, or py" >&2
  exit 1
fi

"$PYTHON_BIN" tools/check_text.py
"$PYTHON_BIN" tools/build_dashboard.py --check

# Project-specific checks (uncomment or extend during WP-S0):
# uv run ruff check . --quiet
# uv run ruff format --check . --quiet
# uv run mypy src
# uv run pytest -q

echo "all checks passed"
