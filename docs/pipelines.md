# CI/CD Pipelines

This project uses two GitHub Actions workflows that together form a lightweight but complete delivery pipeline.

```
feature branch  ──PR──▶  main  ──push──▶  GitHub Release
                   │               │
              [premerge]      [postmerge]
              runs tests      tags + releases
```

---

## Pre-merge (`premerge.yml`)

**Trigger:** every pull request whose target branch is `main` or `master`.

### Purpose
Act as a gate that blocks bad code from landing on the default branch. The job must be green before GitHub will permit a merge (configure this under **Settings → Branches → Branch protection rules → Require status checks**).

### Matrix
Tests run in parallel across **Python 3.11, 3.12, and 3.13** so regressions on any supported interpreter are caught immediately.

### Concurrency
`cancel-in-progress: true` is set so that pushing a new commit to an open PR cancels the still-running check for the previous commit. This keeps CI feedback fast and avoids wasting runner minutes.

### Steps
| Step | Action | Notes |
|---|---|---|
| Checkout | `actions/checkout@v4` | |
| Install uv | `astral-sh/setup-uv@v5` | Caches deps by `uv.lock` hash |
| Set up Python | `actions/setup-python@v5` | Pinned to matrix version |
| Install deps | `uv sync --frozen --group test` | Fails if `uv.lock` is stale |
| Run tests | `uv run pytest -v --tb=short` | All 41 tests must pass |

---

## Post-merge (`postmerge.yml`)

**Trigger:** every push to `main` or `master` (i.e. whenever a PR is merged or a direct commit lands).

### Purpose
Automatically version and publish the codebase so every merge to `main` produces a traceable, downloadable release — with zero manual tagging.

### Versioning — Conventional Commits + SemVer

Version numbers follow [Semantic Versioning](https://semver.org) (`MAJOR.MINOR.PATCH`) and are derived **automatically** from commit messages using the [Conventional Commits](https://www.conventionalcommits.org) specification.

| Commit message prefix | Version bump | Example |
|---|---|---|
| `fix: …` | Patch | `v1.2.3` → `v1.2.4` |
| `feat: …` | Minor | `v1.2.3` → `v1.3.0` |
| `feat!: …` or body contains `BREAKING CHANGE:` | Major | `v1.2.3` → `v2.0.0` |
| Anything else (no prefix) | Patch (default) | `v1.2.3` → `v1.2.4` |

The first release starts at `v0.1.0` (the action's default when no previous tag exists).

#### Writing good commit messages

```
feat: add sector allocation table to allocation script
fix: handle missing TOTP secret gracefully
feat!: rename compare subcommand flags

BREAKING CHANGE: --period flag replaced by positional argument
```

### Steps
| Step | Action | Notes |
|---|---|---|
| Checkout (full depth) | `actions/checkout@v4` | `fetch-depth: 0` gives the tag action the full git history |
| Bump version + push tag | `mathieudutour/github-tag-action@v6.2` | Reads commits, bumps semver, pushes git tag |
| Create GitHub Release | `softprops/action-gh-release@v2` | Creates a release on the new tag with an auto-generated changelog |

### Permissions
The job declares `permissions: contents: write` which is the minimum required to push tags and create releases. No other permissions are granted.

---

## Branch protection setup (recommended)

To enforce the pre-merge gate, go to **Settings → Branches** and add a protection rule for `main`:

- **Require a pull request before merging** ✓
- **Require status checks to pass before merging** ✓
  - Add `Test (Python 3.11)`, `Test (Python 3.12)`, `Test (Python 3.13)` as required checks
- **Require branches to be up to date before merging** ✓
- **Do not allow bypassing the above settings** ✓ (optional but recommended)

---

## Workflow summary

```
Developer opens PR
       │
       ▼
[premerge] runs pytest × 3 Python versions
       │
       ├─ any failure → PR blocked, developer fixes and pushes again
       │
       └─ all green → PR can be merged
                │
                ▼
           Merge to main
                │
                ▼
       [postmerge] reads commits since last tag
                │
                ▼
       Determines semver bump (patch / minor / major)
                │
                ▼
       Pushes git tag  (e.g. v1.3.0)
                │
                ▼
       Creates GitHub Release with changelog
```
