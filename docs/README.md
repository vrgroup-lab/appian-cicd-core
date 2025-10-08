# Appian CI/CD Core: Overview

This repository centralizes reusable CI/CD building blocks for Appian Deployment API v2. It provides composite GitHub Actions, small Python CLIs, and shared configuration to drive a two‑repo promotion model:

- App repos: one per Appian application (export packages, call reusable workflows).
- Core repo (this): common actions and CLIs that call Appian APIs (export, inspect+poll, import) and handle logging, retries, and errors.

Key capabilities
- Reusable workflows: `.github/workflows/export.yml`, `.github/workflows/promote.yml` (export.yml ahora publica el ZIP principal y los artefactos opcionales: scripts SQL, customization file/template y plugins).
- Composite actions: `.github/actions/appian-export`, `.github/actions/appian-promote`, `.github/actions/appian-resolve-package`.
- API CLIs: `.github/actions/appian-promote/inspect_cli.py`, `import_cli.py`, `appian_cli.py` and `.github/actions/appian-export/appian_cli.py`.
- Central config: `.github/actions/_config/appian_base_urls.env` and `appian_promote.env`.


## Quick Start

Prerequisites
- Appian Admin Console: Deployment Management v2 enabled; CI service account with System Administrator rights; API key created for each environment.
- GitHub Secrets (org or repo level): `APPIAN_DEV_API_KEY`, `APPIAN_QA_API_KEY`, `APPIAN_PROD_API_KEY` (and `APPIAN_DEMO_API_KEY` if used).
- Base URLs set in `.github/actions/_config/appian_base_urls.env`.

Run locally
- Inspect (real API) using Core CLI:
  - `python .github/actions/appian-promote/appian_cli.py inspect --base-url <BASE_URL_QA> --api-key <API_KEY_QA> --package-path /path/to/pkg.zip`
- Import (real API) using Core CLI:
  - `python .github/actions/appian-promote/appian_cli.py import --base-url <BASE_URL_QA> --api-key <API_KEY_QA> --package-path /path/to/pkg.zip`
- Export (real API) using Core CLI:
  - `python .github/actions/appian-export/appian_cli.py export --base-url <BASE_URL_DEV> --api-key <API_KEY_DEV> --kind package --rid <PACKAGE_UUID> --outdir artifacts`

Run via GitHub Actions (recommended)
- Wrapper repo calls Core reusable workflows with `secrets: inherit`.
- Export from Dev, then Promote to QA/Prod:
  - Use `.github/workflows/export.yml` to publicar el paquete ZIP y, si existen, scripts SQL, customization file/template y plugins como artifacts separados.
  - Use `.github/workflows/promote.yml` to import that ZIP into the target environment.

Minimal wrapper example
- See `README.md` (root) for a complete wrapper example. Core workflows resolve API keys and base URLs based on `env`/`target_env` inputs.


## Where to Look
- API calls and polling logic:
- `.github/actions/appian-promote/inspect_cli.py`
- `.github/actions/appian-promote/import_cli.py`
- `.github/actions/appian-export/appian_cli.py` (coordinación de export y descargas opcionales)
- `.github/actions/appian-resolve-package/appian_cli.py`
- HTTP and multipart helpers: `.github/actions/appian-promote/utils.py:15`, `:56`.

All credentials shown in examples must be redacted or replaced with placeholders such as `<API_KEY_QA>` and `<BASE_URL_PROD>` when sharing externally.
