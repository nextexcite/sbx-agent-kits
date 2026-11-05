#!/usr/bin/env bash
# OCI smoke test. Does not call authenticated Amp endpoints or start a browser.
set -euo pipefail
for c in amp mise uv agent-browser pnpm fnm pi bun deno skills gh node npm chromium; do
  command -v "$c" >/dev/null || { echo "MISSING:$c" >&2; exit 1; }
done
[[ "$(id -u)" -eq 1000 ]] || { echo "Expected nonroot agent uid 1000" >&2; exit 1; }
node -e 'const v = process.versions.node.split(".").map(Number); if (v[0] < 24 || !process.release.lts) process.exit(1);'
echo "PASS: all requested executables present, agent UID=1000, Node >=24 with an LTS release marker (installed via fnm)"
for c in amp mise uv agent-browser pnpm fnm pi bun deno skills gh node npm chromium; do
  printf '%s => %s\n' "$c" "$(command -v "$c")"
done
