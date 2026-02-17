#!/bin/bash
# Restore working tree to a previous version. Does NOT change git history.
# Usage: ./roll_back_version.sh <version>   e.g. ./roll_back_version.sh 1.0.0
#
# This checks out files from tag v<version> into your working directory.
# You can then edit and run push_new_version.sh to release (e.g. 1.0.2 with "Restored to 1.0.0 behavior").
# Never reuse version numbers - the next release gets a new number.

set -e

if [[ -z "$1" ]]; then
  echo "Usage: ./roll_back_version.sh <version>"
  echo "Example: ./roll_back_version.sh 1.0.0"
  exit 1
fi

VERSION="$1"
# Allow with or without 'v' prefix
if [[ "$VERSION" != v* ]]; then
  TAG="v${VERSION}"
else
  TAG="$VERSION"
  VERSION="${VERSION#v}"
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check tag exists
if ! git rev-parse "$TAG" >/dev/null 2>&1; then
  echo "ERROR: Tag $TAG not found. Available tags:"
  git tag -l
  exit 1
fi

echo "This will restore all tracked files to $TAG state."
echo "Your current changes will be overwritten. Uncommitted changes will be LOST."
read -p "Continue? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
  exit 1
fi

git checkout "$TAG" -- .

echo ""
echo "Done. Working tree restored to $TAG."
echo ""
echo "Next steps:"
echo "  1. Review changes: git status"
echo "  2. Edit CHANGELOG.md [Unreleased] - add 'Restored to ${VERSION} behavior' or describe fixes"
echo "  3. Run ./push_new_version.sh to release (e.g. 1.0.2)"
