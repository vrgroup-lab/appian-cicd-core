# Contributing

Scope
- Keep changes focused on the Core’s responsibilities: reusable workflows, composite actions, and API CLIs for Appian Deployment v2.
- Do not embed environment‑specific secrets or URLs in this repo.

Code style
- Python: prefer small, single‑purpose modules under `.github/actions/*`. Avoid adding external dependencies.
- Logging: concise, stderr; include machine‑readable status tokens (e.g., `deploy.status=`).
- Errors: raise `RuntimeError` with enough context for operators.

PR process
- Open PRs against `develop`. Keep changes minimal and well‑scoped.
- Include short description of endpoints touched and any new env vars.
- If you update workflows or action inputs/outputs, also update docs under `/docs`.

Tests and validation
- Prefer real environment validation via dry‑run toggles where applicable.
- For API paths/headers, cross‑check against Appian Deployment v2 documentation.

Add a new target environment
- Add base URL to `.github/actions/_config/appian_base_urls.env`.
- Ensure a corresponding GitHub Secret exists (e.g., `APPIAN_<ENV>_API_KEY`).
- Update wrapper workflows to list the new `env`/`target_env` option if needed.

Release hygiene
- Version actions via tags in the Core once stabilized; consumers should pin to tags rather than branches.

