# GitHub Copilot Instructions — Python Project Standards

This repository requires the following coding standards. Please follow them on every contribution.

## Language Version
- Python 3.11 or newer is required.

## Type Hinting (Required)
- All functions and methods must have complete type annotations for parameters and return types.
- Use `from __future__ import annotations` for forward references when needed.

## Docstrings (Required — reStructuredText / ReST)
- All public functions, methods, and classes must include docstrings in ReST format.
- Docstrings should include: short description, `:param:`/`Args` for parameters, `:returns:`/`Returns`, and `:raises:`/`Raises` when applicable.

## Imports
- ALWAYS place imports at the top of each file.
- Order imports as: `from __future__`, standard library, third-party, local/relative imports.

## Formatting & Linting
- Use `ruff` as the primary linter/formatter. Ruff is configured to be Black-compatible (line length 88, compatible formatting rules).
- Do NOT run `black` in CI; rely on `ruff` formatting.
- Keep `ruff` configuration in `pyproject.toml`.

## Complexity & Static Analysis
- Use `pylint` to enforce style and code quality; project includes a recommended `.pylintrc`.
- Use `mccabe` (McCabe complexity) threshold of 10; functions exceeding this should be refactored.

## Examples
- Type hints and ReST docstring example:

def compute_total(prices: list[float]) -> float:
    """Compute the sum of prices.

    :param prices: Sequence of numeric prices.
    :returns: The total price as a float.
    :raises ValueError: If `prices` is empty.
    """
    if not prices:
        raise ValueError("prices must not be empty")
    return sum(prices)

## CI Enforcement
- Branches and PRs must pass the repository CI checks which include: `ruff check`, `pylint`, McCabe complexity checks, and `pytest`.

## Migration Notes
- For legacy modules that predate these rules, create focused PRs to incrementally adopt the standards.

## Developer Tooling (pre-commit, Commitizen)
- Use `pre-commit` to run formatting and basic linting locally before commits. The repository includes a `.pre-commit-config.yaml` with the `ruff` hook configured to auto-fix issues.
- Install pre-commit and enable hooks locally:

```bash
python -m pip install --upgrade pip
python -m pip install pre-commit
pre-commit install
pre-commit run --all-files
```

- Commit message validation: this repo uses `commitizen` to standardize commit messages. A `commit-msg` hook is configured via `.pre-commit-config.yaml` to validate messages.
- Install Commitizen for local use (dev dependency in `pyproject.toml`):

```bash
python -m pip install commitizen
cz init  # if you want to reinitialize locally
```

## CI vs pre-commit: recommended setup
- Use `pre-commit` for fast, local, automatic fixes (format & basic linting) to improve developer feedback loop.
- Keep CI checks (GitHub Actions) to enforce the full pipeline (formatting, `ruff check`, `pylint`, McCabe complexity, and `pytest`) on every push/PR. CI should *not* auto-fix — it should fail the run so contributors correct issues locally.

## Project configuration notes
- `pyproject.toml` contains:
    - `requires-python = ">=3.13"`
    - `tool.ruff` configuration (line length and lint selection)
    - `tool.pylint` configuration (complexity thresholds)
    - `project.optional-dependencies` -> `dev` includes `commitizen`
- Keep these settings in sync between local dev tools and CI.

If you have questions about applying these rules to specific code, open an issue and tag the maintainers.
