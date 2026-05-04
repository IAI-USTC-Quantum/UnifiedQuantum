---
name: uniqc-release
description: "Create a new UnifiedQuantum release: generates release notes, updates CHANGELOG.md, creates a release branch, and opens a PR to main. After merge, handles git tag creation and PyPI publication."
---

# UnifiedQuantum Release Skill

Use this skill when a maintainer wants to create a new release. The release workflow has two phases: PR creation and post-merge publication.

## Version Number

**IMPORTANT**: If the user does NOT provide a version number, you MUST ask them for one before proceeding.

Valid version formats:
- `vx.y.z` (e.g., `v0.0.10`)
- `x.y.z` (e.g., `0.0.10`)

The version will be normalized to `vx.y.z` format.

## Phase 1: Pre-Merge (Release PR)

### Step 1: Check Preconditions

1. Confirm we're on `main` branch and worktree is clean:
   ```bash
   git status
   git branch
   ```

2. Check current version from `uniqc/_version.py`:
   ```bash
   grep "__version__" uniqc/_version.py
   ```

3. Verify CHANGELOG.md has `[Unreleased]` section with content.

### Step 2: Generate Release Notes

Run the release notes generator (if available):
```bash
uv run python scripts/generate_release_notes.py <version> 2>/dev/null || echo "No release notes generator found"
```

If no generator exists, manually draft release notes from:
- `CHANGELOG.md` `[Unreleased]` section
- Recent commit messages: `git log --oneline --since="2 weeks ago"`

### Step 3: Update CHANGELOG.md

1. Read current `CHANGELOG.md` to find the `[Unreleased]` section
2. Add the new version section with today's date:
   ```
   ## [x.y.z] - YYYY-MM-DD

   [Content from Unreleased section]
   ```
3. Update the `[Unreleased]` section to be empty (or add placeholder)

### Step 4: Create Release Branch

```bash
git checkout -b release/<version>
```

### Step 5: Commit Changes

```bash
git add CHANGELOG.md
git commit -m "$(cat <<'EOF'
docs(release): prepare v{x.y.z} release

- Update CHANGELOG.md with release notes
- Move [Unreleased] changes to [{x.y.z}] section

Co-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>
EOF
)"
```

### Step 6: Push and Create PR

```bash
git push -u origin release/<version>
gh pr create --title "Release v{x.y.z}" --body "$(cat <<'EOF'
## Release v{x.y.z}

### Changes
[Summary of changes from CHANGELOG.md]

### Pre-release Testing
- [x] `/uniqc-test-before-release` completed
- [x] Test report reviewed and approved
- [x] All blocking issues resolved

### Release Checklist
- [ ] PR merged to main
- [ ] GitHub Actions CI passes
- [ ] Tag created and pushed
- [ ] PyPI publication confirmed

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

## Phase 2: Post-Merge (Publication)

**IMPORTANT**: After the PR is merged, ask the user to confirm before proceeding with publication.

### Step 1: Confirm User Intent

Ask the user: "The PR has been merged. Do you want me to proceed with creating the git tag and publishing to PyPI?"

### Step 2: Fetch and Checkout Main

```bash
git fetch origin main
git checkout main
git pull origin main
```

### Step 3: Create and Push Tag

```bash
git tag -a v{x.y.z} -m "Release v{x.y.z}"
git push origin v{x.y.z}
```

### Step 4: Publish to PyPI

```bash
# Build the package
uv build

# Publish to PyPI (requires API token)
uv publish --token $PYPI_TOKEN
```

### Step 5: Verify

```bash
# Check the tag exists
git fetch --tags
git tag -l "v{x.y.z}*"

# Check PyPI (optional - requires network)
curl -s https://pypi.org/pypi/unified-quantum/json | grep '"version"' | head -1
```

## Error Handling

- If CHANGELOG.md is missing or malformed, create a minimal release note
- If the branch already exists, offer to delete and recreate or use existing
- If PyPI publish fails, provide manual instructions for the user

## Example Conversation Flow

1. User: `/uniqc-release`
2. Assistant: "What version would you like to release? (Current: 0.0.9)"
3. User: "0.0.10"
4. Assistant: Creates release PR...
5. User merges PR
6. Assistant: "PR merged! Would you like me to create the git tag and publish to PyPI?"
7. User: "Yes"
8. Assistant: Proceeds with tag creation and PyPI publication
