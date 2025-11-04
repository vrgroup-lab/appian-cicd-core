# Architecture

This Core repo provides a centralized integration to Appian Deployment Management v2. It supports a two‑repository model where application code lives in app‑specific repos, while promotion mechanics and API logic live here.

Two‑repo model
- App repo: owns the application, packaging logic, and invokes reusable workflows from the Core via `workflow_call`.
- Core repo (this): exposes reusable workflows, composite actions, and CLIs that encapsulate Appian API calls, polling, retries, and error handling.

Boundaries and configuration
- Base URLs: `.github/actions/_config/appian_base_urls.env`.
- Action behavior: `.github/actions/_config/appian_promote.env`.
- Secrets: injected by the caller repo’s environment via GitHub Secrets (`APPIAN_*_API_KEY`).
- API clients: pure Python in `.github/actions/appian-promote/*.py` and `.github/actions/appian-export/appian_cli.py`.


## Flow: Dev → QA → Prod
```mermaid
sequenceDiagram
  autonumber
  participant AppRepo as App Repo (Wrapper)
  participant CoreWF as Core Workflows
  participant Appian as Appian API v2

  AppRepo->>CoreWF: Call export.yml (env=dev)
  CoreWF->>Appian: POST /deployments (Action-Type: export)
  CoreWF-->>Appian: Poll GET /deployments/{uuid}
  Appian-->>CoreWF: status=COMPLETED, packageZip
  CoreWF->>AppRepo: Upload artifact ZIP

  AppRepo->>CoreWF: Call promote.yml (target=qa)
  CoreWF->>Appian: (optional) POST /inspections
  CoreWF-->>Appian: Poll GET /inspections/{uuid}
  Appian-->>CoreWF: status=COMPLETED
  CoreWF->>Appian: POST /deployments (Action-Type: import)
  CoreWF-->>Appian: Poll GET /deployments/{uuid}
  Appian-->>CoreWF: status=COMPLETED

  AppRepo->>CoreWF: Call promote.yml (target=prod)
  CoreWF->>Appian: (optional) inspect, then import
```


## Flow: Inspection + Polling (Retries/Backoff)
```mermaid
sequenceDiagram
  autonumber
  participant Core as Core (inspect_cli.py)
  participant Appian as Appian v2

  Core->>Appian: POST /inspections (multipart)
  Appian-->>Core: { uuid, url }
  loop until COMPLETED/FAILED or timeout
    Core->>Appian: GET /inspections/{uuid}
    alt 404 just-registered
      Core-->>Core: wait interval, retry
    else 500 APNX-1-4552-005
      Core-->>Core: retry up to N times
    else transient network/timeout
      Core-->>Core: retry up to N times
    end
  end
  Core-->>Core: evaluate summary.problems (errors/warnings)
```

Implementation references
- Inspect POST: `.github/actions/appian-promote/inspect_cli.py:19`
- Inspect GET: `.github/actions/appian-promote/inspect_cli.py:41`
- Retry handling and status evaluation: `.github/actions/appian-promote/inspect_cli.py:72`


## Flow: Import (Options)
```mermaid
sequenceDiagram
  autonumber
  participant Core as Core (import_cli.py)
  participant Appian as Appian v2

  Core->>Appian: POST /deployments (Action-Type: import)
  Note over Core: multipart includes json, packageFileName,<br/>optional customization/adminSettings/plugins
  Appian-->>Core: { uuid, url }
  loop until terminal status
    Core->>Appian: GET /deployments/{uuid}
  end
  Core->>Appian: GET /deployments/{uuid}/log (tail)
  Core-->>Core: fail on FAILED or COMPLETED_WITH_*_ERRORS
```

Notes
- Common import options like deleteMissing are not sent by the current Core. They can be added via the JSON portion of the multipart if required by your governance; diagram shows options as a future extension.

Implementation references
- Import POST: `.github/actions/appian-promote/import_cli.py:24`
- Deployment GET: `.github/actions/appian-promote/import_cli.py:73`
- Log GET: `.github/actions/appian-promote/import_cli.py:80`
- Status handling: `.github/actions/appian-promote/import_cli.py:133`

