# CI/CD Status

## Overview

This document tracks the CI/CD pipeline status for the Advanced Compliance app.

## GitHub Actions Workflows

### ✅ Linters
**Status**: Active
**Triggers**: Pull requests, pushes to main/version-* branches
**Jobs**:
- Pre-commit hooks (trailing whitespace, YAML/JSON validation, merge conflicts)
- Semgrep static analysis (Frappe rules + Python correctness)

### ✅ Server Tests (MariaDB)
**Status**: Active
**Triggers**: Pull requests, pushes to main/version-* branches, manual dispatch
**Test Matrix**:
- Frappe/ERPNext v15 (2 parallel containers)
- Frappe/ERPNext v16 Beta (2 parallel containers)

**Total Jobs per Run**: 4 parallel test jobs

## Code Quality Tools

- **Ruff**: Python linting and formatting (110 char line length, tab indentation)
- **Prettier**: JavaScript/Vue/SCSS formatting
- **ESLint**: JavaScript linting
- **Semgrep**: Security and code quality static analysis

## Coverage

Coverage reports are uploaded to Codecov with version-specific flags:
- `server-version-15`
- `server-version-16`

## Pre-commit Hooks

Pre-commit hooks are configured and run locally before each commit.

To install: `pre-commit install`
To run manually: `pre-commit run --all-files`

## Marketplace Compliance

✅ **Linters CI**: Passing
✅ **Server Tests CI**: Configured for v15 and v16
✅ **Code Quality**: Automated with Ruff, Prettier, ESLint
✅ **Security**: Semgrep static analysis

---

Last Updated: 2026-01-05
