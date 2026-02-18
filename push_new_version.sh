#!/bin/bash
# Release current version: commit [Unreleased] as release, tag, bump version, push.
# Usage: ./push_new_version.sh [patch|minor|major]   (default: patch)

set -e
BUMP="${1:-patch}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Read current version
CURRENT=$(cat VERSION | tr -d ' \n')
if [[ ! "$CURRENT" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  echo "ERROR: Invalid VERSION format. Expected semver (e.g. 1.0.0)"
  exit 1
fi

# Bump version for next release
IFS='.' read -r MAJOR MINOR PATCH <<< "$CURRENT"
case "$BUMP" in
  major) MAJOR=$((MAJOR+1)); MINOR=0; PATCH=0 ;;
  minor) MINOR=$((MINOR+1)); PATCH=0 ;;
  patch) PATCH=$((PATCH+1)) ;;
  *) echo "ERROR: bump must be patch|minor|major"; exit 1 ;;
esac
NEXT="${MAJOR}.${MINOR}.${PATCH}"

# Update CHANGELOG: replace [Unreleased] with [CURRENT], add new [Unreleased] template
TODAY=$(date +%Y-%m-%d)
python3 << PYEOF
with open("CHANGELOG.md", "r") as f:
    content = f.read()

# Replace [Unreleased] header with [CURRENT] - date
old_header = "## [Unreleased]"
new_header = f"## [${CURRENT}] - ${TODAY}"
new_content = content.replace(old_header, new_header, 1)

# Insert new [Unreleased] section before the release we just created
template = f"""## [Unreleased]

### Added
- (add changes here)

### Changed
- (add changes here)

### Fixed
- (add fixes here)

---

"""
# Insert template before the first ## [X.Y.Z] - date
insert_before = new_header
if insert_before in new_content:
    new_content = new_content.replace(insert_before, template + insert_before, 1)

with open("CHANGELOG.md", "w") as f:
    f.write(new_content)
PYEOF

# Update VERSION for next development cycle
echo "$NEXT" > VERSION

# Commit and tag (stages all changes: new, modified, deleted, moved/renamed files)
git add -A
git status
echo ""
read -p "Commit and create tag v${CURRENT}? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
  echo "Aborted. Restore CHANGELOG.md and VERSION if needed."
  exit 1
fi

git commit -m "Release v${CURRENT}"
git tag -a "v${CURRENT}" -m "Release v${CURRENT}"

echo ""
echo "Pushing..."
git push origin main
git push origin "v${CURRENT}"

echo ""
echo "Done. Released v${CURRENT}. Next version: ${NEXT}"
echo "Edit CHANGELOG.md [Unreleased] as you make changes."
