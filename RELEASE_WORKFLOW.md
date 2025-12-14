# Quick Release Workflow

This is a quick reference for publishing new versions of `soniox-pro-sdk`.

## Prerequisites (One-time Setup)

1. ✅ Trusted Publishing configured on PyPI (see [PYPI_TRUSTED_PUBLISHING_SETUP.md](PYPI_TRUSTED_PUBLISHING_SETUP.md))
2. ✅ GitHub Actions workflow set up (already done)

## Publishing a New Version (Simple Version)

```bash
# 1. Bump version in pyproject.toml
vim pyproject.toml  # Change version = "1.1.0" to "1.2.0"

# 2. Commit
git add pyproject.toml
git commit -m "chore: Bump version to 1.2.0"
git push origin main

# 3. Tag and push
git tag v1.2.0
git push origin v1.2.0

# Done! GitHub Actions will automatically publish to PyPI
```

## Publishing with Release Notes

```bash
# Steps 1-2 same as above (bump version, commit, push)

# 3. Create release with notes
gh release create v1.2.0 \
  --title "v1.2.0 - Brief Title" \
  --notes "## What's New
- Feature A
- Feature B
- Bug fix C"

# Done! GitHub Actions will publish to PyPI
```

## Version Numbering Guide

Use [Semantic Versioning](https://semver.org/): `MAJOR.MINOR.PATCH`

- **MAJOR** (1.0.0 → 2.0.0): Breaking changes, API incompatibility
- **MINOR** (1.1.0 → 1.2.0): New features, backward compatible
- **PATCH** (1.1.1 → 1.1.2): Bug fixes only

Examples:
- Added HTTP/2 support: `1.0.1 → 1.1.0` (new feature)
- Fixed type annotations: `1.1.0 → 1.1.1` (bug fix)
- Changed API signature: `1.1.0 → 2.0.0` (breaking change)

## Common Tasks

### Preview build locally
```bash
uv build
# Check dist/ directory
ls -lh dist/
```

### Test installation locally
```bash
pip install dist/soniox_pro_sdk-1.2.0-py3-none-any.whl
```

### Delete a tag (if you made a mistake)
```bash
git tag -d v1.2.0              # Delete locally
git push origin :refs/tags/v1.2.0  # Delete remotely
```

### Monitor GitHub Actions
https://github.com/CodeWithBehnam/soniox-pro-sdk/actions

### Check PyPI
https://pypi.org/project/soniox-pro-sdk/

## Troubleshooting

**Q: Publishing failed with "File already exists"**
A: That version is already on PyPI. Bump the version number and try again.

**Q: How do I test before publishing?**
A: Use a pre-release version: `1.2.0rc1`, `1.2.0a1`, `1.2.0b1`

**Q: Can I unpublish from PyPI?**
A: No! PyPI doesn't allow deletion. Use a new patch version instead.

## Full Example with All Steps

```bash
# Make changes
git checkout -b feature/new-feature
# ... make your changes ...
uv run pytest  # Test locally

# Merge to main
git checkout main
git merge feature/new-feature

# Bump version (1.1.0 → 1.2.0)
sed -i '' 's/version = "1.1.0"/version = "1.2.0"/' pyproject.toml

# Commit and tag
git add pyproject.toml
git commit -m "chore: Bump version to 1.2.0"
git push origin main
git tag v1.2.0
git push origin v1.2.0

# Create release
gh release create v1.2.0 \
  --title "v1.2.0 - New Feature" \
  --notes "Added support for feature X"

# Monitor progress
gh run list --limit 3
gh run watch  # Watch latest run

# Verify
open https://pypi.org/project/soniox-pro-sdk/
```

That's it! 🚀
