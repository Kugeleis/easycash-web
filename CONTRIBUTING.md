# Contributing to EasyCash&Tax Web

## Commit Message Convention

All commits must follow the **Conventional Commits** specification:

```
type(scope): short description

optional body

optional footer
```

**Allowed types:**
- `feat` — new feature
- `fix` — bug fix
- `docs` — documentation only changes
- `style` — formatting, missing semicolons, etc.; no code change
- `refactor` — code change that neither fixes a bug nor adds a feature
- `test` — adding missing tests or correcting existing tests
- `chore` — changes to the build process or auxiliary tools
- `build` — changes that affect the build system or external dependencies
- `ci` — changes to CI configuration files and scripts
- `perf` — performance improvements
- `deps` — dependency updates
- `revert` — reverting a previous commit

**Examples:**
```
feat: add VAT rate validity dates
fix(api): handle missing client on upload
docs: add AfA mode documentation
test: add money helper unit tests
chore: add prek hook configuration
```

**Example with scope:**
```
feat(storage): add migration chain for format_version
```

## Pre-commit Hooks

Before every commit, prek runs:

1. `trailing-whitespace` — remove trailing whitespace
2. `end-of-file-fixer` — ensure files end with newline
3. `check-added-large-files` — reject large binary files
4. `ruff-check` — lint Python code
5. `ruff-format` — format Python code
6. `ty-check` — type-check with ty
7. `pytest` — run the test suite

All checks must pass before a commit is accepted.

## Slice-based Development

Work is delivered in small, testable slices. Each slice:
- Adds a minimal set of tests that initially fail (red)
- Implements the feature (green)
- Refactors while keeping tests green (refactor)
- Commits as a single semantic commit
