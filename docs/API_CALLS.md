# API Calls (Appian Deployment Management v2)

This document enumerates all endpoints used by the Core, with method, URL templates, headers, request structure, example calls, and error handling.

Base
- Base URL per environment: see `.github/actions/_config/appian_base_urls.env`.
- Header `appian-api-key: <API_KEY>` is required for all calls.


## 1) Create Inspection
- Method: POST
- URL: `<BASE_URL>/suite/deployment-management/v2/inspections`
- Headers: `appian-api-key`, `Accept: application/json`, `Content-Type: multipart/form-data`
- Body (multipart):
  - Part `json`: `{ "packageFileName": "<fileName.zip>" }`
  - File `packageFileName`: binary ZIP
  - Optional file `customizationFileName`: `.properties`
  - Optional file `adminConsoleSettingsFileName`: ZIP
- Response: `{ "uuid": "<insp_uuid>", "url": "<status_url>", ... }`
- Code refs: `.github/actions/appian-promote/inspect_cli.py:19`

Example (curl)
```
curl -X POST \
  -H "appian-api-key: <API_KEY_QA>" \
  -H "Accept: application/json" \
  -F 'json={"packageFileName":"my_pkg.zip"};type=application/json' \
  -F 'packageFileName=@/path/to/my_pkg.zip;type=application/zip' \
  <BASE_URL_QA>/suite/deployment-management/v2/inspections
```


## 2) Get Inspection by UUID
- Method: GET
- URL: `<BASE_URL>/suite/deployment-management/v2/inspections/{uuid}` (or `url` from create response)
- Headers: `appian-api-key`, `Accept: application/json`
- Response: `{ "status": "PENDING|COMPLETED|FAILED", "summary": { "problems": { ... } } }`
- Code refs: `.github/actions/appian-promote/inspect_cli.py:41`

Example (curl)
```
curl -H "appian-api-key: <API_KEY_QA>" -H "Accept: application/json" \
  <BASE_URL_QA>/suite/deployment-management/v2/inspections/<UUID>
```

Error handling
- 404 after creation is treated as eventually consistent and retried.
- 500 with code `APNX-1-4552-005` is treated as transient “no information” and retried.
- Network/timeouts retried with backoff. See `.github/actions/appian-promote/inspect_cli.py:72`.


## 3) Create Deployment (Import)
- Method: POST
- URL: `<BASE_URL>/suite/deployment-management/v2/deployments`
- Headers: `appian-api-key`, `Action-Type: import`, `Accept: application/json`, `Content-Type: multipart/form-data`
- Body (multipart):
  - Part `json`: `{ "name": "<name>", "description": "<desc>", "packageFileName": "<file.zip>", [optional] ... }`
  - File `packageFileName`: binary ZIP
  - Optional file `customizationFileName`: `.properties`
  - Optional file `adminConsoleSettingsFileName`: ZIP
  - Optional file `pluginsFileName`: ZIP
- Response: `{ "uuid": "<dep_uuid>", "url": "<status_url>", ... }`
- Code refs: `.github/actions/appian-promote/import_cli.py:24`, `:42-48`

Example (curl)
```
curl -X POST \
  -H "appian-api-key: <API_KEY_QA>" \
  -H "Action-Type: import" \
  -H "Accept: application/json" \
  -F 'json={"name":"Promote","description":"From Dev","packageFileName":"my_pkg.zip"};type=application/json' \
  -F 'packageFileName=@/path/to/my_pkg.zip;type=application/zip' \
  <BASE_URL_QA>/suite/deployment-management/v2/deployments
```

Transient error retry
- Retries on HTTP 500, network errors, and timeouts, up to `APPIAN_PROMOTE_IMPORT_RETRIES` with `APPIAN_PROMOTE_RETRY_DELAY` seconds between attempts. See `.github/actions/appian-promote/import_cli.py:49`.


## 4) Get Deployment Status
- Method: GET
- URL: `<BASE_URL>/suite/deployment-management/v2/deployments/{uuid}` (or `url` from create response)
- Headers: `appian-api-key`, `Accept: application/json`
- Response: `{ "status": "COMPLETED|FAILED|COMPLETED_WITH_*", "summary": { ... } }`
- Code refs: `.github/actions/appian-promote/import_cli.py:73`, `.github/actions/appian-export/appian_cli.py:82`

Example (curl)
```
curl -H "appian-api-key: <API_KEY_QA>" -H "Accept: application/json" \
  <BASE_URL_QA>/suite/deployment-management/v2/deployments/<UUID>
```


## 5) Get Deployment Log (Import)
- Method: GET
- URL: `<BASE_URL>/suite/deployment-management/v2/deployments/{uuid}/log`
- Headers: `appian-api-key`, `Accept: text/plain`
- Response: plain text (import log)
- Code refs: `.github/actions/appian-promote/import_cli.py:80`

Example (curl)
```
curl -H "appian-api-key: <API_KEY_QA>" -H "Accept: text/plain" \
  <BASE_URL_QA>/suite/deployment-management/v2/deployments/<UUID>/log
```


## 6) Create Deployment (Export)
- Method: POST
- URL: `<BASE_URL>/suite/deployment-management/v2/deployments`
- Headers: `appian-api-key`, `Action-Type: export`, `Accept: application/json`, `Content-Type: multipart/form-data`
- Body (multipart):
  - Part `json`: `{ "exportType": "application|package", "uuids": ["<rid>"] }` plus optional `name`, `description`
- Response: `{ "uuid": "<dep_uuid>", "url": "<status_url>", ... }`
- Code refs: `.github/actions/appian-export/appian_cli.py:44`, `:66-70`

Example (curl)
```
curl -X POST \
  -H "appian-api-key: <API_KEY_DEV>" \
  -H "Action-Type: export" \
  -H "Accept: application/json" \
  -H "Content-Type: multipart/form-data; boundary=..." \
  --data-binary @<(printf "--B\r\nContent-Disposition: form-data; name=\"json\"\r\nContent-Type: application/json\r\n\r\n{\"exportType\":\"package\",\"uuids\":[\"<PACKAGE_UUID>\"]}\r\n--B--\r\n") \
  <BASE_URL_DEV>/suite/deployment-management/v2/deployments
```


## 7) Resolve Package by Name
- Method: GET
- URL: `<BASE_URL>/suite/deployment-management/v2/applications/{app_uuid}/packages`
- Headers: `appian-api-key`, `Accept: application/json`
- Response: `{ "packages": [ { "uuid": "...", "name": "..." }, ... ] }`
- Code refs: `.github/actions/appian-resolve-package/appian_cli.py:23`

Example (curl)
```
curl -H "appian-api-key: <API_KEY_DEV>" -H "Accept: application/json" \
  <BASE_URL_DEV>/suite/deployment-management/v2/applications/<APP_UUID>/packages
```


## 8) Package Download (Export)
- Method: GET
- URL: Prefer `results.packageZip` from export result. Fallback candidates:
  - `<status_url>/package-zip`
  - `<status_url>/package`
  - `<status_url>/download`
  - `<status_url>?download=true`
  - `<BASE_URL>/suite/deployment-management/v2/deployments/{uuid}/package-zip|package|download`
- Headers: `appian-api-key`, `Accept: application/zip`
- Response: binary ZIP
- Code refs: `.github/actions/appian-export/appian_cli.py:119`, `:141-143`


## Error Surfaces and Semantics
- HTTP errors: raised as `RuntimeError("HTTP <code> on <url>: <body>")` in the Core. See `.github/actions/appian-promote/utils.py:24`.
- Network errors: raised as `RuntimeError("Network error on <url>:")`. See `.github/actions/appian-promote/utils.py:26`.
- Special handling: 404 and `APNX-1-4552-005` on inspection GET are retried.

Placeholders
- Always redact: `<API_KEY_DEV>`, `<API_KEY_QA>`, `<API_KEY_PROD>`, `<BASE_URL_DEV|QA|PROD>`, `<APP_UUID>`, `<PACKAGE_UUID>`.

