# appian-cicd-core
Repositorio central de CI/CD para Appian. Contiene los workflows reutilizables, librerías de automatización y scripts base para orquestar la exportación, inspección e importación de aplicaciones Appian entre entornos (Dev → QA → Prod), integrados con GitHub Actions y APIs de Appian.

**MVP del Core**
- Workflows reutilizables (`workflow_call`):
  - `.github/workflows/export.yml`: exporta app o package desde un entorno Appian y publica ZIP + artefactos auxiliares (scripts SQL, customization file/template, plugins) cuando están disponibles.
  - `.github/workflows/promote.yml`: importa/promueve un paquete hacia un entorno objetivo.
- CoreLib reutilizable:
  - Composite actions:
    - `.github/actions/appian-export`: wrapper de export (simulado en MVP).
    - `.github/actions/appian-promote`: wrapper de import/promote (simulado en MVP).
  - Shell scripts:
    - `scripts/appian_export.sh` y `scripts/appian_promote.sh` (placeholders para futura integración real con API de Appian).

Este MVP no llama APIs reales; genera artefactos simulados para validar la integración entre repos y el paso de `secrets` organizacionales.

## Requisitos
- Secrets de organización disponibles para el runner:
  - `APPIAN_DEV_API_KEY`, `APPIAN_QA_API_KEY`, `APPIAN_PROD_API_KEY`, `APPIAN_DEMO_API_KEY` (opcional si se usa).
- Repos sandbox “wrapper” que invocan a estos workflows con `secrets: inherit`.

## Cómo usar desde un repo Sandbox
Ejemplo de wrapper `deploy.yml` que permite elegir despliegue por `app` o `package`, resolver el paquete por nombre, y elegir el plan de promoción (Dev→QA, Dev→Prod o Dev→QA→Prod). El Sandbox puede leer `vars.APP_UUID` y pasarlo como `app_uuid`.

```yaml
name: Deploy (wrapper)
on:
  workflow_dispatch:
    inputs:
      deploy_kind:
        description: Tipo de despliegue
        type: choice
        options: [package, app]
        default: package
      app_uuid:
        description: UUID de la aplicación
        required: true
      package_name:
        description: Nombre del package (si deploy_kind=package y no hay UUID)
        required: false
      plan:
        description: Plan de promoción
        type: choice
        options: [dev-to-qa, dev-to-prod, dev-qa-prod]
        default: dev-to-qa
      dry_run:
        type: boolean
        required: false
        default: false

jobs:
  export:
    uses: <org>/<repo-core>/.github/workflows/export.yml@develop
    secrets: inherit
    with:
      env: dev
      deploy_kind: ${{ inputs.deploy_kind }}
      app_uuid: ${{ inputs.app_uuid }} # o usa vars.APP_UUID
      package_name: ${{ inputs.package_name }}
      dry_run: ${{ inputs.dry_run }}

  promote_qa:
    if: ${{ inputs.plan != 'dev-to-prod' }}
    needs: export
    uses: <org>/<repo-core>/.github/workflows/promote.yml@develop
    secrets: inherit
    with:
      source_env: dev
      target_env: qa
      artifact_name: ${{ needs.export.outputs.artifact_name }}
      dry_run: ${{ inputs.dry_run }}

  promote_prod_direct:
    if: ${{ inputs.plan == 'dev-to-prod' }}
    needs: export
    uses: <org>/<repo-core>/.github/workflows/promote.yml@develop
    secrets: inherit
    with:
      source_env: dev
      target_env: prod
      artifact_name: ${{ needs.export.outputs.artifact_name }}
      dry_run: ${{ inputs.dry_run }}

  promote_prod_after_qa:
    if: ${{ inputs.plan == 'dev-qa-prod' }}
    needs: promote_qa
    uses: <org>/<repo-core>/.github/workflows/promote.yml@develop
    secrets: inherit
    with:
      source_env: dev
      target_env: prod
      artifact_name: ${{ needs.export.outputs.artifact_name }}
      dry_run: ${{ inputs.dry_run }}
```

Notas:
- Los workflows del Core resuelven la API key correcta según `env` usando los secrets de organización. No se indexan dinámicamente `secrets.*`; se seleccionan de forma explícita por entorno.
- `export.yml` sube el ZIP como artifact y, si existen, publica artifacts adicionales para scripts SQL, customization file/template y plugins. Expone `artifact_name`, `artifact_path`, `artifact_dir`, `manifest_path`, `raw_response_path`, `deployment_uuid` y `deployment_status`. `promote.yml` descarga por `artifact_name`.
- Para pruebas iniciales, `dry_run=true` evita llamadas reales y crea/usa un archivo simulado.

### Variables/URLs de entornos
- Define variables (org o repo) con las URLs base de Appian, por ejemplo:
  - `APPIAN_DEV_BASE_URL`, `APPIAN_QA_BASE_URL`, `APPIAN_PROD_BASE_URL` (y `APPIAN_DEMO_BASE_URL` si aplica).
- El Core las resuelve a `APPIAN_BASE_URL` en tiempo de ejecución según el `env`/`target_env` seleccionado.

## Aprobaciones por entorno
- Define en el repo Sandbox los environments `qa` y `prod` con reviewers requeridos.
- El workflow `promote.yml` del Core marca `environment: <target_env>`, por lo que el gating/approval se aplica en el Sandbox al promover a `qa` o `prod`.
- `export.yml` no define environment (sin approvals de exportación).

## Roadmap de la integración real (siguiente iteración)
- Implementar llamadas a Appian Deployment API en los scripts (auth, export, inspect, import).
- Manejo de artefactos: subir `artifact_path` a Artifacts de Actions o a un bucket externo.
- Validaciones y gating: inspección en QA, approvals manuales para PROD.
- Trazabilidad: IDs de deployment, logs estructurados y auditoría.
- Versionamiento de acciones (tags semánticos) para uso estable desde sandboxes.
