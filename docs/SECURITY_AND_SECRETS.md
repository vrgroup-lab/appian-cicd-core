# Security and Secrets

Secret storage and injection
- Secrets live in GitHub Secrets at the org or repository level (wrapper repos).
- Core workflows read them via `secrets: inherit` from the wrapper and map to env vars based on selected environment.
- No secrets are stored in this repository.

Secrets used
- `APPIAN_DEV_API_KEY`, `APPIAN_QA_API_KEY`, `APPIAN_PROD_API_KEY`, `APPIAN_DEMO_API_KEY` (optional).
- Masking: actions mask keys in logs (`::add-mask::...`).

Base URLs
- Resolved from `.github/actions/_config/appian_base_urls.env` by target env; do not hardcode per-repo.
- Example placeholders: `<BASE_URL_DEV>`, `<BASE_URL_QA>`, `<BASE_URL_PROD>`.

Rotation guidance
- Rotate API keys regularly in Appian Admin Console and update corresponding GitHub Secrets.
- Use GitHub Environments for `qa` and `prod` with required reviewers to gate usage of privileged secrets.
- Avoid printing raw API responses that may include sensitive structure; logs should remain concise.

Redaction policy
- Before sharing with third parties (including Appian Support), replace secrets and URLs with placeholders `<API_KEY>`, `<BASE_URL_ENV>`, and redact object names if sensitive.

Access control
- Service account should have the minimum roles needed (typically System Administrator for deployment operations) and be segregated from human users.

