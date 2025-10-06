# Configuration

This section lists configuration points, env vars, and secrets for the Core.

Central files
- `.github/actions/_config/appian_base_urls.env`: maps logical env to base URLs.
  - Example: `DEV=<BASE_URL_DEV>`, `QA=<BASE_URL_QA>`, `PROD=<BASE_URL_PROD>`, `DEMO=<BASE_URL_DEMO>`.
- `.github/actions/_config/appian_promote.env`: toggles promote behavior.
  - `APPIAN_PROMOTE_ENABLE_INSPECTION=true|false` (default: true if not set).

GitHub Secrets (in wrapper repos)
- `APPIAN_DEV_API_KEY=<API_KEY_DEV>`
- `APPIAN_QA_API_KEY=<API_KEY_QA>`
- `APPIAN_PROD_API_KEY=<API_KEY_PROD>`
- `APPIAN_DEMO_API_KEY=<API_KEY_DEMO>` (optional)

Resolved environment variables (by workflows)
- `APPIAN_BASE_URL` per target env via `.github/actions/_config/appian_base_urls.env`.
- `APPIAN_API_KEY` or `APPIAN_API_KEY_TARGET` resolved from GitHub Secrets.

CLI/environment knobs
- Inspection/import polling
  - `APPIAN_PROMOTE_MAX_WAIT` (seconds, default 1800)
  - `APPIAN_PROMOTE_POLL_INTERVAL` (seconds, default 5)
  - `APPIAN_PROMOTE_INSPECTION_RETRIES` (default 5)
- Import POST retry
  - `APPIAN_PROMOTE_IMPORT_RETRIES` (default 3)
  - `APPIAN_PROMOTE_RETRY_DELAY` (seconds, default 10)
- Export polling
  - `APPIAN_EXPORT_MAX_WAIT` (seconds, default 900)
  - `APPIAN_EXPORT_POLL_INTERVAL` (seconds, default 5)

Admin Console checklist (per environment)
- Deployment Management v2 enabled.
- Create API key for the CI/CD service account and store it as GitHub Secret.
- Service account has System Administrator role or needed privileges for deployments.
- If importing Admin Console Settings or plug-ins via deployment, allow those features per governance.

Switching target environment safely
- Use wrapper inputs to select `env` (export) and `target_env` (promote).
- Core resolves base URLs and keys; do not hardcode URLs/keys in app repos.
- Protect environments in GitHub (required reviewers) to gate `prod` promotions.

Redaction
- Replace actual values with placeholders when sharing: `<BASE_URL_DEV>`, `<API_KEY_QA>`, etc.

