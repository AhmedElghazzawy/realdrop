#!/usr/bin/env bash
# PostToolUse hook: format the file Claude just edited. Always exits 0 so it never blocks work.
# Receives the tool event as JSON on stdin; we only need tool_input.file_path.
set -u

file="$(python3 -c 'import json,sys; print(json.load(sys.stdin).get("tool_input",{}).get("file_path",""))' 2>/dev/null)"
[ -n "$file" ] && [ -f "$file" ] || exit 0

root="${CLAUDE_PROJECT_DIR:-$(pwd)}"

case "$file" in
  */apps/api/*.py)
    (cd "$root/apps/api" && uv run ruff format "$file" >/dev/null 2>&1; uv run ruff check --fix "$file" >/dev/null 2>&1)
    ;;
  */apps/web/*.ts|*/apps/web/*.tsx|*/apps/web/*.css|*/apps/web/*.json)
    (cd "$root/apps/web" && pnpm exec prettier --write "$file" >/dev/null 2>&1)
    ;;
esac

exit 0
