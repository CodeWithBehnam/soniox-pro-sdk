# PyPI Trusted Publishing Setup Guide

This guide will help you set up automated PyPI publishing from GitHub using Trusted Publishing (the most secure method).

## What is Trusted Publishing?

Trusted Publishing is PyPI's recommended way to publish packages from CI/CD without using API tokens. It uses OpenID Connect (OIDC) to verify that the package is being published from your GitHub repository.

**Benefits:**
- ✅ No API tokens to manage or rotate
- ✅ More secure (tokens can't leak)
- ✅ Works automatically with GitHub Actions
- ✅ PyPI's recommended method

## Setup Steps

### Step 1: Configure PyPI Trusted Publishing

1. **Go to PyPI** and log in: https://pypi.org/

2. **Navigate to your project**: https://pypi.org/manage/project/soniox-pro-sdk/

3. **Go to Publishing settings**:
   - Click on "Publishing" in the left sidebar
   - Scroll to "Trusted Publishers" section

4. **Add GitHub as a Trusted Publisher**:
   - Click "Add a new publisher"
   - Select "GitHub" as the publisher type
   - Fill in the following details:
     ```
     Owner: CodeWithBehnam
     Repository name: soniox-pro-sdk
     Workflow name: publish.yml
     Environment name: (leave empty)
     ```
   - Click "Add"

### Step 2: How It Works

Now when you want to publish a new version:

#### Method 1: Create a Git Tag (Recommended)
```bash
# 1. Bump version in pyproject.toml
# Edit pyproject.toml and change version to 1.2.0

# 2. Commit the change
git add pyproject.toml
git commit -m "chore: Bump version to 1.2.0"
git push origin main

# 3. Create and push a tag
git tag v1.2.0
git push origin v1.2.0

# GitHub Actions will automatically:
# - Build the package
# - Publish to PyPI using Trusted Publishing
```

#### Method 2: Create a GitHub Release
```bash
# 1. Bump version in pyproject.toml (same as above)
# 2. Commit and push

# 3. Create GitHub release
gh release create v1.2.0 \
  --title "v1.2.0 - New Features" \
  --notes "Release notes here"

# GitHub Actions will automatically publish to PyPI
```

### Step 3: Remove Old API Token (Optional but Recommended)

Once Trusted Publishing is set up and working:

1. Delete the `PYPI_API_TOKEN` secret from GitHub:
   - Go to: https://github.com/CodeWithBehnam/soniox-pro-sdk/settings/secrets/actions
   - Delete `PYPI_API_TOKEN`

2. Remove the token from PyPI:
   - Go to: https://pypi.org/manage/account/token/
   - Delete the old API token

3. Remove from `.env` file (keep local copy if needed for manual testing)

## Testing the Workflow

### Test with a Pre-release Version

```bash
# 1. Bump to a pre-release version
# Edit pyproject.toml: version = "1.1.1rc1"

# 2. Commit and tag
git add pyproject.toml
git commit -m "chore: Test release 1.1.1rc1"
git push origin main
git tag v1.1.1rc1
git push origin v1.1.1rc1

# 3. Check GitHub Actions
# Go to: https://github.com/CodeWithBehnam/soniox-pro-sdk/actions

# 4. Verify on PyPI
# Check: https://pypi.org/project/soniox-pro-sdk/
```

## Troubleshooting

### Error: "Trusted publishing exchange failure"

**Cause:** PyPI Trusted Publisher not configured correctly

**Fix:** Double-check the publisher configuration on PyPI:
- Owner must be exactly: `CodeWithBehnam`
- Repository must be exactly: `soniox-pro-sdk`
- Workflow must be exactly: `publish.yml`
- Environment should be empty (unless you use GitHub environments)

### Error: "Workflow does not have 'id-token: write' permission"

**Cause:** Missing permissions in workflow file

**Fix:** Already included in the updated `publish.yml`:
```yaml
permissions:
  id-token: write  # Required for PyPI Trusted Publishing
  contents: read
```

### Error: "File already exists"

**Cause:** Version already published to PyPI

**Fix:** Bump the version number in `pyproject.toml` before publishing

## Complete Publishing Workflow Example

Here's the complete workflow for publishing a new version:

```bash
# 1. Make your changes
# ... code changes ...

# 2. Run tests locally
uv run pytest

# 3. Bump version in pyproject.toml
# Change: version = "1.1.0" → version = "1.2.0"

# 4. Update CHANGELOG or release notes (optional)

# 5. Commit changes
git add .
git commit -m "feat: Add new feature X

- Implemented feature X
- Added tests for feature X
- Updated documentation"

# 6. Push to main
git push origin main

# 7. Create and push tag
git tag v1.2.0
git push origin v1.2.0

# 8. (Optional) Create GitHub release with notes
gh release create v1.2.0 \
  --title "v1.2.0 - Feature X" \
  --notes "Added feature X that does Y and Z"

# 9. Monitor GitHub Actions
# https://github.com/CodeWithBehnam/soniox-pro-sdk/actions

# 10. Verify on PyPI (after ~2 minutes)
# https://pypi.org/project/soniox-pro-sdk/
```

## Benefits of This Workflow

1. **Automatic Publishing**: Just push a tag, GitHub handles the rest
2. **No Token Management**: No need to rotate or secure API tokens
3. **Audit Trail**: All publishes are tied to GitHub commits
4. **Version Control**: Tags in git match PyPI versions
5. **Rollback Safety**: Can always republish from any git tag

## Current Status

- ✅ GitHub Actions workflow updated (`publish.yml`)
- ⏳ **Action Required**: Set up Trusted Publisher on PyPI (see Step 1)
- ⏳ **Action Required**: Test with next version bump

## References

- [PyPI Trusted Publishing Documentation](https://docs.pypi.org/trusted-publishers/)
- [GitHub Actions PyPI Publish Action](https://github.com/marketplace/actions/pypi-publish)
- [Packaging Python Projects](https://packaging.python.org/tutorials/packaging-projects/)
