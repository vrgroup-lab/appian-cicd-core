# Workflows and Actions

This repository exposes reusable workflows and composite actions that implement the promotion flow.

Reusable workflows
- `.github/workflows/export.yml`: exports una aplicación/paquete desde un entorno, descarga todos los recursos asociados (ZIP principal, scripts SQL, customization file/template, plugins) y los publica como artifacts.
- `.github/workflows/promote.yml`: downloads a ZIP artifact and imports it into the target environment.
- `.github/workflows/check-org-secret.yml`: utility to verify presence of required organization secrets.

Composite actions
- `.github/actions/appian-export`: calls Appian export (multipart POST with `Action-Type: export`), polls, and downloads the ZIP.
- `.github/actions/appian-promote`: orchestrates optional inspection and import.
- `.github/actions/appian-resolve-package`: resolves a package UUID by name in an application.

Mapping steps to CLIs
- Inspect CLI: `.github/actions/appian-promote/inspect_cli.py`
- Import CLI: `.github/actions/appian-promote/import_cli.py`
- Promote entrypoint (dispatches to inspect/import): `.github/actions/appian-promote/appian_cli.py`
- Export CLI: `.github/actions/appian-export/appian_cli.py`

Workflow inputs/outputs (summary)
- export.yml (workflow_call)
  - inputs: `env`, `deploy_kind`, `app_uuid`, `package_name` (opcional), `app_name` (opcional), `dry_run`
  - outputs: `artifact_name`, `artifact_path`, `artifact_dir`, `manifest_path`, `raw_response_path`, `deployment_uuid`, `deployment_status`
- promote.yml (workflow_call)
  - inputs: `source_env`, `target_env`, `artifact_name`, `dry_run`

Conditions and environments
- `promote.yml` sets `environment: <target_env>` so approvals and protection rules apply in the caller repo.
- Dry runs propagate to underlying CLIs to avoid real API calls.

Configuration resolution
- Base URLs resolved from `.github/actions/_config/appian_base_urls.env` inside actions.
- API keys sourced from GitHub Secrets based on `env/target_env` selection.
