#!/usr/bin/env bash
set -euo pipefail

# Create a portable source archive of the Labreport application.
# The archive will contain tracked files (excluding Git metadata) and
# will be placed under the dist/ directory for easy sharing.

ROOT_DIR=$(git rev-parse --show-toplevel)
cd "$ROOT_DIR"

DIST_DIR="$ROOT_DIR/dist"
mkdir -p "$DIST_DIR"

ARCHIVE_NAME="labreport-$(date +%Y%m%d).tar.gz"
ARCHIVE_PATH="$DIST_DIR/$ARCHIVE_NAME"

echo "Creating archive: $ARCHIVE_PATH"

# Use git archive to include only tracked files, ensuring the bundle
# matches the repository contents available on GitHub.
git archive --format=tar.gz -o "$ARCHIVE_PATH" HEAD

echo "Done. Archive saved to $ARCHIVE_PATH"
