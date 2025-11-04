# Troubleshooting

Decision tree (typical failures)
- 401/403 authentication/authorization
  - Verify GitHub Secret for target env is set and non-empty.
  - Confirm Admin Console API key is valid and not expired.
  - Check service account role (System Administrator or sufficient privileges).
- Inspection UUID returned but GET /inspections/{uuid} returns 500 (no info)
  - Expected transient condition `APNX-1-4552-005`. The Core retries automatically.
  - If persistent beyond max retries, re-run inspection; consider waiting 1–2 minutes between attempts.
- Inspection GET returns 404 repeatedly
  - Eventual consistency window exceeded. Try again; if persistent, validate that the inspection POST succeeded and package is valid ZIP.
- Import stuck in PENDING_REVIEW or REJECTED
  - Review Deployment Management settings and environment approvals.
- Import FAILED or COMPLETED_WITH_*_ERRORS
  - Review deployment log tail (Core prints last ~200 lines) and full log via API.
- Permissions mismatches despite System Admin role
  - Check object-level permissions, environment security restrictions, and plug-in/platform version compatibility.

Admin Console validation checklist
- Deployment Management v2 enabled for API use.
- API key created for CI user and associated to the correct account.
- Allow importing Admin Console Settings and plug-ins if used by your deployments.
- Cross-environment considerations (source vs target) match your governance.

Re-run locally para aislar problemas
- Export:
  - `python .github/actions/appian-export/appian_cli.py export --base-url <BASE_URL_DEV> --api-key <API_KEY_DEV> --kind package --rid 00000000-0000-0000-0000-000000000000 --outdir artifacts`
- Promote:
  - `python .github/actions/appian-promote/appian_cli.py import --base-url <BASE_URL_QA> --api-key <API_KEY_QA> --package-path artifacts/<zip_real>.zip`
- Inspect:
  - `python .github/actions/appian-promote/appian_cli.py inspect --base-url <BASE_URL_QA> --api-key <API_KEY_QA> --package-path /path/to/pkg.zip`

What to attach for Appian Support
- ZIP the following (redact secrets and sensitive data):
  - CLI stderr/stdout logs from failed run (with timestamps).
  - The exact endpoints called and UUIDs (inspection/deployment), e.g., `/inspections/<UUID>`, `/deployments/<UUID>`.
  - Deployment log text (tail or full) from `/deployments/<UUID>/log`.
  - Environment summary: `<BASE_URL_TARGET>`, target environment name, approximate time window (UTC).
  - Package metadata: package file name and size; do not include the package ZIP unless requested.

Placeholders for redaction
- Replace values with `<API_KEY>`, `<BASE_URL_ENV>`, `<APP_UUID>`, `<PACKAGE_UUID>`, `<INSPECTION_UUID>`, `<DEPLOYMENT_UUID>`.
