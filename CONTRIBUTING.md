# Contributing
- `pip install -e ".[dev]" reportlab`
- `ruff check src tests` and `python -m pytest -q` must pass.
- Truthfulness rules: never commit fabricated metrics, unrun test claims, or
  unverified capability statements. Mark unverified adapters as unverified.
