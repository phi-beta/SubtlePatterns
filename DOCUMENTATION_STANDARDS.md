# Documentation standards

This project follows the documentation style set by
[RustyMatrix/DOCUMENTATION_STANDARDS.md](https://github.com/PhilippeRBeauchamp/RustyMatrix/blob/main/DOCUMENTATION_STANDARDS.md).
Highlights:

* **Every public API has a doc comment.** The doc comment is the API contract.
* **Every new file has a top-of-file comment** explaining its purpose.
* **Mathematical/algorithmic content has a "rationale" section** — not just code.
* **Examples in docstrings must be runnable** (or at least syntactically valid).
* **README updates go alongside code changes** that affect user-visible behaviour.

## When writing a new pattern

1. Open `src/subtle_patterns/patterns/<family>.py`.
2. Add a module-level docstring explaining what the family produces and the variants it offers.
3. Decorate the implementation with `@register("family_name")`.
4. Honour these rules (mirrored from `patterns/__init__.py`):
   * No background fills.
   * Pack repetitive geometry into a single `<path>` where possible.
   * Honour `cfg.density` (multiplicative on element count or spacing).
   * Honour `cfg.jitter` (0 = perfectly regular, 1 = max-jitter).
   * Use `make_rng(seed, "family", cfg.variant, ...)` for per-layer streams.
5. Add a docstring section to `docs/REFERENCE.md` listing the family, variants, and parameters.
6. Add a test in `tests/test_patterns.py` (parametrize over variants).
7. Add a preset in `src/subtle_patterns/presets.py` if it ships by default.
8. Update `README.md` if it's a headline feature.

## When changing the public API

1. Update the relevant docstrings and `docs/REFERENCE.md`.
2. Add a test that pins the new behaviour.
3. Bump the version in `pyproject.toml` and the `__version__` string in `src/subtle_patterns/__init__.py`.

## Style

* **Type annotations on every public symbol.**
* **Doc comments use reST-style** (Google-style `:param x:` is also fine; the codebase uses `:param` sparingly).
* **Errors are `ValueError` for bad data, `TypeError` for wrong types, `KeyError` for missing keys, `FileNotFoundError` for missing files.** Don't invent custom exception classes unless the user needs to catch them.
* **No `# noqa` comments without a justification comment** above the line.
