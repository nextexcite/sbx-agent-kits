#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
: "${IMAGE_REFERENCE:?Set IMAGE_REFERENCE to one OCI runtime image reference}"
# Accept a deliberately narrow OCI reference alphabet; reject YAML and sed injection.
[[ "$IMAGE_REFERENCE" =~ ^[a-zA-Z0-9][a-zA-Z0-9._:/@-]*$ ]] || {
  echo "Invalid image reference" >&2; exit 2;
}
DEST="${1:-dist/v2}"
mkdir -p "$DEST"
sed "s|@IMAGE_REFERENCE@|$IMAGE_REFERENCE|g" kits/v2/spec.yaml.in > "$DEST/spec.yaml"
! grep -q '@IMAGE_REFERENCE@' "$DEST/spec.yaml"
echo "Staged v2 descriptor"
