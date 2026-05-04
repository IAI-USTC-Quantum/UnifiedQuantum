---
name: uniqc-release
description: "Create a new UnifiedQuantum release: generates release notes, updates CHANGELOG.md, creates a release branch, and opens a PR to main. After merge, creates and pushes a git tag, creates a GitHub Release, and deletes the release branch."
---

# UnifiedQuantum Release Skill

Use this skill when a maintainer wants to create a new release. The release workflow has two phases: PR creation and post-merge publication.

**Note**: PyPI publishing is automatic via GitHub Actions when a `v*` tag is pushed. GitHub Release is created as part of the post-merge workflow.

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

### Step 4: Update Documentation Release Notes

1. Read current `docs/source/releases/index.md`
2. Add a new version section under `## 版本解读` with:
   - **Version heading**: `### v{x.y.z}`
   - **Summary paragraph**: Brief description of the release theme
   - **Changes list**: Key additions, changes, and fixes
   - **Migration notes**: If breaking changes exist, add upgrade guidance
   - **Known gaps**: Document any unverified features
   - **Verification results**: Link to test report if available
3. Update the header section:
   - Change "当前建议先看哪个版本" to point to the new version
   - Update the version description to reflect the new release

Example structure:
```markdown
### `v{x.y.z}`

这是一个[X类]版本，核心主题是**主题描述**。

本版主要变更：
- **变更1**：描述
- **变更2**：描述

如果你正在从 `v{prev}` 迁移，主要变更对用户透明：
- 变更说明

已知缺口（不阻塞发布）：
- 缺口描述

**发布验证结果**：验证结果摘要。
```

### Step 5: Create Release Branch

```bash
git checkout -b release/<version>
```

### Step 6: Commit Changes

```bash
git add CHANGELOG.md docs/source/releases/index.md
git commit -m "$(cat <<'EOF'
docs(release): prepare v{x.y.z} release

- Update CHANGELOG.md with release notes
- Move [Unreleased] changes to [{x.y.z}] section
- Add release notes to docs/source/releases/index.md

Co-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>
EOF
)"
```

### Step 7: Push and Create PR

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

**IMPORTANT**: After the PR is merged, ask the user to confirm before proceeding.

### Step 1: Confirm User Intent

Ask the user: "The PR has been merged. Do you want me to proceed with creating the tag, GitHub Release, and cleaning up?"

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

GitHub Actions will automatically:
1. Build wheels for Ubuntu and Windows
2. Validate wheel ABI
3. Publish to PyPI

### Step 4: Create GitHub Release

```bash
gh release create v{x.y.z} \
  --title "v{x.y.z}" \
  --notes-file <(cat <<'EOF'
## Changes

See CHANGELOG.md for details.

## What's Changed

[Summary from release notes]

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)
```

Or use the GitHub web UI to create the release after the tag is pushed.

### Step 5: Delete Release Branch

```bash
git branch -D release/v{x.y.z}
git push origin --delete release/v{x.y.z}
```

### Step 6: Verify

```bash
# Check the tag exists
git fetch --tags
git tag -l "v{x.y.z}*"
```

Monitor the release at:
- GitHub Actions: https://github.com/IAI-USTC-Quantum/UnifiedQuantum/actions
- GitHub Releases: https://github.com/IAI-USTC-Quantum/UnifiedQuantum/releases
- PyPI: https://pypi.org/project/unified-quantum/

## Error Handling

- If CHANGELOG.md is missing or malformed, create a minimal release note
- If the branch already exists, offer to delete and recreate or use existing
- If tag push fails, retry or inform the user
- If GitHub Release creation fails, inform user to create it manually at the releases page

## Example Conversation Flow

1. User: `/uniqc-release`
2. Assistant: "What version would you like to release? (Current: 0.0.9)"
3. User: "0.0.10"
4. Assistant: Creates release PR...
5. User merges PR
6. Assistant: "PR merged! Shall I create the tag, GitHub Release, and clean up?"
7. User: "Yes"
8. Assistant: Creates tag → GitHub Actions publishes to PyPI → Creates GitHub Release → Deletes release branch
