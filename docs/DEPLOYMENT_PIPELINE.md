# Deployment Pipeline

This pipeline promotes Appian packages across environments using composite actions.

Actors and triggers
- Wrapper repo: invoca las composite actions del Core directamente (`uses: vrgroup-lab/appian-cicd-core/.github/actions/...`).
- Manual dispatch en el wrapper: selecciona `deploy_kind`, `app_uuid`, `package_name` y el plan (Dev→QA, Dev→Prod, Dev→QA→Prod).
- Approvals: siguen definidos en el wrapper mediante GitHub Environments (`environment: <target_env>`).

Artifacts
- Export ZIP name: generado por `appian-export` y publicado como artifact.
- Artifact naming: `appian-<deploy_kind>-<resource>-<run_id>` donde `<resource>` deriva de `package_name` o el UUID resultante.

Step-by-step
- Export step:
  - Resolver API key para `env` a partir de `APPIAN_<ENV>_API_KEY`.
  - Resolver package UUID cuando `deploy_kind=package` mediante `.github/actions/appian-resolve-package`.
  - Ejecutar `.github/actions/appian-export` para disparar la exportación y descargar ZIP + metadata.
  - Publicar artifacts y exponer `artifact_name` y rutas asociadas.
- Promote step:
  - Resolver `APPIAN_API_KEY_TARGET` con el mismo helper (`resolve_api_key.py`) incluido en `appian-promote`.
  - Descargar artifact ZIP, opcionalmente preparar scripts (`appian-prepare-db-scripts`) y construir ICF (`appian-build-icf`).
  - Ejecutar inspección/importación mediante `.github/actions/appian-promote` con retries y manejo de estados.

State machine and retries
- Inspection (`inspect_cli.py`):
  - Polls GET `/inspections/{uuid}` until `COMPLETED` or `FAILED`.
  - Retries on 404 (registration lag), 500 `APNX-1-4552-005` (no info yet), or transient network errors, bounded by `APPIAN_PROMOTE_INSPECTION_RETRIES` and `APPIAN_PROMOTE_MAX_WAIT`.
- Import (`import_cli.py`):
  - Polls GET `/deployments/{uuid}` until one of: `COMPLETED`, `COMPLETED_WITH_ERRORS`, `COMPLETED_WITH_IMPORT_ERRORS`, `COMPLETED_WITH_PUBLISH_ERRORS`, `FAILED`, `PENDING_REVIEW`, `REJECTED`.
  - POST import retries on transient errors (HTTP 500, timeouts) based on `APPIAN_PROMOTE_IMPORT_RETRIES` and `APPIAN_PROMOTE_RETRY_DELAY`.
- Export (`appian-export/appian_cli.py`):
  - Polls until `COMPLETED` or `COMPLETED_WITH_EXPORT_ERRORS` or `FAILED`.
  - Attempts multiple known download URLs when `results.packageZip` is missing.

Configuration knobs
- `.github/actions/_config/appian_promote.env` controls inspection enablement.
- Poll intervals and timeouts via env vars (see CONFIGURATION.md).
