# Code Quality Tools Setup

This project now includes ruff for linting/formatting and ty for type checking.

## Tools Added

### Ruff (Linting & Formatting)
- **Fast Python linter and formatter** (written in Rust)
- Replaces: black, isort, and flake8
- Line length: 100 characters
- Includes: import sorting, naming conventions, code simplification, and more

### ty (Type Checking)
- **Fast type checker from Astral** (written in Rust)
- Modern alternative to mypy
- Faster type checking with better error messages
- Automatically discovers packages in active virtual environment

## Installation

```bash
# Install all dev tools including ruff and ty
uv sync --all-extras

# Or just install quality tools
uv sync
uv add --dev ruff ty pre-commit
```

## Quick Commands

### Format Code
```bash
ruff format
```

### Lint & Auto-fix Issues
```bash
ruff check --fix
```

### Run Type Checker
```bash
ty check
```

### Run All Quality Checks
```bash
ruff format && ruff check --fix && ty check
```

### Set Up Pre-commit Hooks (Optional)
```bash
pre-commit install
pre-commit run --all-files  # Run on all files
```

## Configuration

All configuration is in `pyproject.toml`:

### Ruff Configuration
- **Line length**: 100 characters
- **Target version**: Python 3.11
- **Linting rules**: Errors, warnings, Pyflakes, import sorting, naming, upgrades, bugbear, comprehensions, unused arguments, simplification
- **Formatting**: Double quotes, space indentation, auto line-ending
- **First-party modules**: `agents` (for proper import sorting)

### ty Configuration
- **Python version**: 3.11
- **Excludes**: `.venv`, `venv`, `.git`, `dist`, `build`, `*.egg-info`, `htmlcov`
- **Module discovery**: Automatic via virtual environment

## Pre-commit Hooks

The project includes `.pre-commit-config.yaml` with hooks for:
- **ruff**: Auto-fixes linting issues
- **ruff-format**: Formats code
- **ty**: Type checking
- **trailing-whitespace**: Removes trailing whitespace
- **end-of-file-fixer**: Ensures files end with newline
- **check-yaml**: Validates YAML files
- **check-added-large-files**: Prevents large file commits
- **check-merge-conflict**: Detects merge conflicts

## Why These Tools?

1. **Ruff**: All-in-one linter/formatter - faster than running multiple tools
2. **ty**: Modern type checker - faster than mypy, better UX
3. **Both from Astral**: Same team that built uv, proven quality and performance

## IDE Integration

Most IDEs support both tools:
- **VS Code**: Ruff and mypy extensions (ty may need manual configuration)
- **PyCharm**: Built-in support via plugins
- **Neovim/Vim**: Supported via LSP plugins

## CI/CD

To add these to CI/CD pipelines:

```bash
# In GitHub Actions or similar
ruff check
ruff format --check
ty check
```
