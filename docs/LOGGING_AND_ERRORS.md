# Logging and Errors

Logging
- All CLIs log to stderr via a simple helper for streaming logs in Actions.
  - Helper: `.github/actions/appian-promote/utils.py:11` (`log`)
- Status lines are concise and grep‑friendly, e.g. `inspect.status=COMPLETED uuid=<...>` or `deploy.status=COMPLETED uuid=<...>`.
- Import action tails the deployment log when the final state is error‑like.
  - Implementation: `.github/actions/appian-promote/import_cli.py:157` and `:160`.

Error handling
- HTTP errors are surfaced as `RuntimeError("HTTP <code> on <url>: <body>")`.
  - Implementation: `.github/actions/appian-promote/utils.py:24`
- Network/timeout errors are surfaced as `RuntimeError("Network error on <url>:")`.
  - Implementation: `.github/actions/appian-promote/utils.py:26`
- Inspection GET special cases (transient):
  - 404 after POST: considered eventual consistency; retried with interval until max wait.
  - 500 `APNX-1-4552-005`: “inspection completed with no information”; retried up to `APPIAN_PROMOTE_INSPECTION_RETRIES`.
  - Implementation: `.github/actions/appian-promote/inspect_cli.py:72`.

Known error codes (catalog)
- APNX-1-0000-000: “User Does Not Have Rights to Perform this Operation”. Usually indicates missing role or API key privileges. Validate Admin Console and service account permissions.
- APNX-1-4552-005: “Inspection completed with no information”. The Core retries this during inspection polling.

Example error snippets (redacted)
- HTTP auth/rights
  - `HTTP 403 on <BASE_URL>/...: {"title":"APNX-1-0000-000","message":"User Does Not Have Rights..."}`
- Inspection transient 500
  - `HTTP 500 on <BASE_URL>/.../inspections/<UUID>: {"title":"APNX-1-4552-005",...}`
- Network/transient
  - `Network error on <BASE_URL>/...: <urlopen error timed out>`

Retry strategy (summary)
- Inspection polling: retries on 404/500 APNX/Network up to a bounded count and max wait.
- Import POST: retries on HTTP 500/Network with bounded attempts and delay.
- Export polling: loops until terminal states; download attempts multiple candidate URLs.

Redaction policy
- When sharing logs externally, replace keys and URLs with placeholders: `<API_KEY>`, `<BASE_URL_ENV>`, `<UUID>`.

