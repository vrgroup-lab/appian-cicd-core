# appian-cicd-core
Repositorio central de CI/CD para Appian. Provee composite actions reutilizables y
utilidades que orquestan la exportación, inspección e importación de aplicaciones Appian
entre entornos (Dev → QA → Prod), integrados con GitHub Actions y las Deployment APIs de Appian.

**MVP del Core**
- Composite actions:
  - `.github/actions/appian-export`: wrapper de export Appian que descarga artefactos y expone metadata.
  - `.github/actions/appian-promote`: wrapper de import/promote Appian con inspección opcional.
  - `.github/actions/appian-build-icf`: genera ICF efímeros con overrides seguros.
  - `.github/actions/appian-prepare-db-scripts`: descarga scripts SQL y produce metadata.
  - `.github/actions/appian-resolve-package`: resuelve UUID de package por nombre dentro de una app.
- CLIs Python internos ejecutan las llamadas reales a Appian (ver carpeta de cada acción).

## Requisitos
- Secrets de organización disponibles para el runner:
  - `APPIAN_DEV_API_KEY`, `APPIAN_QA_API_KEY`, `APPIAN_PROD_API_KEY`, `APPIAN_DEMO_API_KEY` (opcional si se usa).
- Repos sandbox “wrapper” que invocan a estas acciones y proveen las keys vía `env`.

### Formato de `ICF_JSON_OVERRIDES`
- `appian-build-icf` espera que los secretos `ICF_JSON_OVERRIDES_*` contengan texto plano con pares `clave=valor`.
- Cada línea puede estar vacía o comenzar con `#` (comentario); sólo las líneas con `=` son válidas y se normalizan a `\n`.
- El primer `=` separa la clave del valor; el resto se mantiene literal para permitir contraseñas con dicho caracter.
- Aún se acepta JSON plano que empiece con `{`, pero se considera *deprecated* y se emite un `::notice::`.

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

jobs:
  export:
    runs-on: ubuntu-latest
    env:
      APPIAN_DEV_API_KEY: ${{ secrets.APPIAN_DEV_API_KEY }}
      APPIAN_QA_API_KEY: ${{ secrets.APPIAN_QA_API_KEY }}
      APPIAN_PROD_API_KEY: ${{ secrets.APPIAN_PROD_API_KEY }}
      APPIAN_DEMO_API_KEY: ${{ secrets.APPIAN_DEMO_API_KEY }}
    steps:
      - uses: actions/checkout@v4
      - uses: <org>/<repo-core>/.github/actions/appian-export@main
        id: export
        with:
          env: dev
          deploy_kind: ${{ inputs.deploy_kind }}
          app_uuid: ${{ inputs.app_uuid }}
          package_name: ${{ inputs.package_name }}

  promote_qa:
    if: ${{ inputs.plan != 'dev-to-prod' }}
    needs: export
    runs-on: ubuntu-latest
    env:
      APPIAN_DEV_API_KEY: ${{ secrets.APPIAN_DEV_API_KEY }}
      APPIAN_QA_API_KEY: ${{ secrets.APPIAN_QA_API_KEY }}
      APPIAN_PROD_API_KEY: ${{ secrets.APPIAN_PROD_API_KEY }}
      APPIAN_DEMO_API_KEY: ${{ secrets.APPIAN_DEMO_API_KEY }}
    steps:
      - uses: actions/download-artifact@v4
        with:
          name: ${{ needs.export.outputs.artifact_name }}
          path: downloaded
      - name: Resolver ZIP
        id: package
        run: |
          set -euo pipefail
          path=$(find downloaded -type f -name '*.zip' -print -quit)
          echo "path=$path" >> "$GITHUB_OUTPUT"
      - uses: <org>/<repo-core>/.github/actions/appian-prepare-db-scripts@main
        id: prepare
        with:
          artifact-name: ${{ needs.export.outputs.artifact_name }}
      - uses: <org>/<repo-core>/.github/actions/appian-promote@main
        with:
          source_env: dev
          target_env: qa
          package_path: ${{ steps.package.outputs.path }}
          db_scripts_path: ${{ steps.prepare.outputs.db_scripts_path }}
          data_source: ${{ steps.prepare.outputs.data_source }}

  promote_prod_direct:
    if: ${{ inputs.plan == 'dev-to-prod' }}
    needs: export
    # Reutilizar los steps de promote_qa con target_env=prod

  promote_prod_after_qa:
    if: ${{ inputs.plan == 'dev-qa-prod' }}
    needs: promote_qa
    # Reutilizar los steps de promote_qa para promover a prod
```

Notas:
- Las acciones resuelven la API key correcta a partir de `APPIAN_<ENV>_API_KEY`, por lo que el caller debe exportar esas variables (con `secrets.*` o `vars.*`).
- `appian-export` sube el ZIP original más artifacts adicionales (scripts SQL, customization, plugins) y expone `artifact_name`, `artifact_path`, `artifact_dir`, `manifest_path`, `raw_response_path`, `deployment_uuid` y `deployment_status`.
### Variables/URLs de entornos
- Define variables (org o repo) con las URLs base de Appian, por ejemplo:
  - `APPIAN_DEV_BASE_URL`, `APPIAN_QA_BASE_URL`, `APPIAN_PROD_BASE_URL` (y `APPIAN_DEMO_BASE_URL` si aplica).
- El Core las resuelve a `APPIAN_BASE_URL` en tiempo de ejecución según el `env`/`target_env` seleccionado.

## Roadmap de la integración real (siguiente iteración)
- Implementar llamadas a Appian Deployment API en los scripts (auth, export, inspect, import).
- Manejo de artefactos: subir `artifact_path` a Artifacts de Actions o a un bucket externo.
- Validaciones y gating: inspección en QA, approvals manuales para PROD.
- Trazabilidad: IDs de deployment, logs estructurados y auditoría.
- Versionamiento de acciones (tags semánticos) para uso estable desde sandboxes.
