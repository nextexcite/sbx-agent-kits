#!/usr/bin/env bash
# Assembles v3's self-contained build context without duplicating toolchain source.
# Kit v3 frontend uses the descriptor's directory as the build context root.
set -euo pipefail
cd "$(dirname "$0")/.."
DEST="${1:-dist/v3}"
mkdir -p "$DEST/scripts"
cp kits/v3/amp.yaml kits/v3/amp.dockerfile kits/v3/amp-context.md "$DEST/"
for name in install-toolchains.sh refresh-node-lts.sh verify-runtime.sh; do
  cp "scripts/$name" "$DEST/scripts/$name"
  chmod 0755 "$DEST/scripts/$name"
done
echo "Staged OCI Kit v3 build context in $DEST"
