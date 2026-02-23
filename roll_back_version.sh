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

echo "This will restore the working tree to exact $TAG state."
echo "  - Tracked files: reverted to $TAG"
echo "  - Files added after $TAG: removed"
echo "  - Untracked files: removed (except .env)"
echo "Uncommitted changes will be LOST."
read -p "Continue? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
  exit 1
fi

# 1. Restore tracked files to TAG state
git checkout "$TAG" -- .

# 2. Remove files that were added after TAG (exist in HEAD but not in TAG)
for f in $(git diff --diff-filter=A --name-only "$TAG" HEAD 2>/dev/null || true); do
  [[ -e "$f" ]] && rm -f "$f"
done

# 3. Remove untracked files and dirs (preserve .env)
git clean -fd -e .env -e .env.local

echo ""
echo "Done. Working tree restored to $TAG."
echo ""
echo "Next steps:"
echo "  1. Review changes: git status"
echo "  2. Edit CHANGELOG.md [Unreleased] - add 'Restored to ${VERSION} behavior' or describe fixes"
echo "  3. Run ./push_new_version.sh to release (e.g. 1.0.2)"
