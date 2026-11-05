#!/usr/bin/env bash
# Run as agent in the image. Uses the remote LTS list, not Node Current.
set -euo pipefail
: "${FNM_DIR:=$HOME/.local/share/fnm}"
command -v fnm >/dev/null
lts="$(fnm list-remote --lts --latest | awk '/^v[0-9]+/ {print $1; exit}')"
if [[ ! "$lts" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  echo "Cannot resolve the latest published Node LTS: $lts" >&2
  exit 1
fi
fnm install "$lts"
fnm default "$lts"
node_bin="$FNM_DIR/node-versions/$lts/installation/bin"
test -x "$node_bin/node"
ln -sfn "$node_bin" "$FNM_DIR/current-bin"
"$FNM_DIR/current-bin/node" -p 'process.version'
