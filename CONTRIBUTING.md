# Contributing to Soniox Pro SDK

Thank you for your interest in contributing to the Soniox Pro SDK! This
document provides guidelines and instructions for contributing.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Making Changes](#making-changes)
- [Testing](#testing)
- [Submitting Changes](#submitting-changes)
- [Style Guide](#style-guide)
- [Release Process](#release-process)

## Code of Conduct

This project adheres to a code of conduct. By participating, you are expected
to uphold this code. Please report unacceptable behaviour to the project
maintainers.

### Our Standards

- Be respectful and inclusive
- Accept constructive criticism gracefully
- Focus on what is best for the community
- Show empathy towards other community members

## Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:

   ```bash
   git clone https://github.com/YOUR-USERNAME/soniox-pro-sdk.git
   cd soniox-pro-sdk
   ```

3. **Add upstream remote**:

   ```bash
   git remote add upstream https://github.com/CodeWithBehnam/soniox-pro-sdk.git
   ```

## Development Setup

### Prerequisites

- Python 3.12 or higher
- [uv](https://github.com/astral-sh/uv) package manager

### Installation

1. **Install dependencies**:

   ```bash
   uv sync --all-extras
   ```

2. **Install pre-commit hooks**:

   ```bash
   uv run pre-commit install
   ```

3. **Set up API key for testing** (optional):

   ```bash
   cp .env.example .env
   # Edit .env and add your SONIOX_API_KEY
   ```

### Project Structure

```text
soniox-pro-sdk/
├── src/soniox/          # Main SDK code
│   ├── client.py        # Synchronous HTTP client
│   ├── async_client.py  # Asynchronous client
│   ├── realtime.py      # WebSocket real-time client
│   ├── types.py         # Pydantic models
│   ├── errors.py        # Custom exceptions
│   ├── config.py        # Configuration management
│   └── utils.py         # Utility functions
├── tests/               # Test suite
├── examples/            # Example scripts
└── docs/                # Documentation
```

## Making Changes

### Workflow

1. **Create a new branch** from `main`:

   ```bash
   git checkout -b feature/your-feature-name
   # or
   git checkout -b fix/your-bug-fix
   ```

2. **Make your changes** following the style guide

3. **Test your changes**:

   ```bash
   # Run tests
   uv run pytest

   # Run linting
   uv run ruff check src/soniox

   # Run type checking
   uv run mypy src/soniox

   # Run all pre-commit hooks
   uv run pre-commit run --all-files
   ```

4. **Commit your changes**:

   ```bash
   git add .
   git commit -m "feat: add new feature"
   ```

### Commit Message Format

We use [Conventional Commits](https://www.conventionalcommits.org/):

```text
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `perf`: Performance improvements
- `test`: Adding or updating tests
- `chore`: Maintenance tasks
- `ci`: CI/CD changes

**Examples:**

```bash
feat(client): add support for custom headers
fix(realtime): handle WebSocket connection timeout
docs(readme): update installation instructions
test(types): add validation tests for Token model
```

## Testing

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=soniox --cov-report=html

# Run specific test file
uv run pytest tests/test_client.py

# Run specific test
uv run pytest tests/test_client.py::test_client_initialization
```

### Writing Tests

- Place tests in the `tests/` directory
- Use descriptive test names: `test_<what>_<condition>_<expected_result>`
- Aim for high coverage of new code
- Mock external API calls
- Test both success and failure paths

Example:

```python
def test_client_handles_authentication_error() -> None:
    """Test client raises AuthenticationError for 401 responses."""
    # Test implementation
```

## Submitting Changes

### Pull Request Process

1. **Update your branch** with latest main:

   ```bash
   git fetch upstream
   git rebase upstream/main
   ```

2. **Push to your fork**:

   ```bash
   git push origin feature/your-feature-name
   ```

3. **Create a Pull Request** on GitHub

4. **Fill in the PR template** with:
   - Description of changes
   - Related issue number (if applicable)
   - Testing performed
   - Breaking changes (if any)

5. **Wait for review** and address feedback

### PR Checklist

Before submitting, ensure:

- [ ] Code follows the style guide
- [ ] Tests pass locally
- [ ] New tests added for new functionality
- [ ] Documentation updated (if needed)
- [ ] CHANGELOG updated (for significant changes)
- [ ] Pre-commit hooks pass
- [ ] No merge conflicts with main

## Style Guide

### Python Style

We follow [PEP 8](https://pep8.org/) with these tools:

- **Ruff** for linting and formatting
- **mypy** for type checking (strict mode)
- **Line length**: 100 characters

### Code Conventions

1. **Type Hints**: Use type hints for all functions

   ```python
   def transcribe(file_id: str, model: str = "stt-async-v3") -> Transcription:
       """Transcribe an audio file."""
   ```

2. **Docstrings**: Use Google-style docstrings

   ```python
   def upload_file(self, file_path: Path) -> File:
       """
       Upload an audio file to Soniox.

       Args:
           file_path: Path to the audio file

       Returns:
           File object with metadata

       Raises:
           FileNotFoundError: If file doesn't exist
       """
   ```

3. **British English**: Use British spelling in documentation
   - "colour" not "color"
   - "optimise" not "optimize"
   - "behaviour" not "behavior"

4. **Imports**: Organise imports with isort

   ```python
   # Standard library
   import os
   from pathlib import Path

   # Third-party
   import httpx
   from pydantic import BaseModel

   # Local
   from soniox.errors import SonioxError
   from soniox.types import Token
   ```

### Documentation Style

- Use clear, concise language
- Provide code examples
- Link to related documentation
- Keep README.md up to date

## Release Process

### Version Numbering

We use [Semantic Versioning](https://semver.org/):

- **MAJOR**: Breaking changes
- **MINOR**: New features (backwards compatible)
- **PATCH**: Bug fixes

### Creating a Release

Maintainers will:

1. Update version in `pyproject.toml`
2. Update `CHANGELOG.md`
3. Create a git tag
4. Publish to PyPI via GitHub Actions

## Questions?

- **Issues**: Open an issue for bugs or feature requests
- **Discussions**: Use GitHub Discussions for questions
- **Email**: Contact maintainers for private matters

## Recognition

Contributors will be recognised in:

- CHANGELOG.md
- GitHub contributors page
- Release notes (for significant contributions)

Thank you for contributing to Soniox Pro SDK! 🎉
