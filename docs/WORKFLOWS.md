# Reusable Actions

Este repositorio ahora expone únicamente composite actions. Los pipelines wrapper deben
referenciar directamente estas acciones (sin workflows intermedios).

Principales composites
- `.github/actions/appian-export`: exporta aplicaciones o packages, descarga artefactos
  asociados (ZIP, scripts SQL, customization, plug-ins) y expone rutas via outputs.
- `.github/actions/appian-promote`: realiza inspección opcional e importación del paquete
  en el entorno destino.
- `.github/actions/appian-build-icf`: genera ICF efímeros tomando overrides YAML + JSON.
- `.github/actions/appian-prepare-db-scripts`: descarga y procesa scripts de base de datos
  junto con su metadata.
- `.github/actions/appian-resolve-package`: resuelve el UUID de un package por nombre.

Scripts internos
- Export CLI: `.github/actions/appian-export/appian_cli.py`
- Resolve helper: `.github/actions/appian-export/scripts/resource_resolver.py`
- Promote CLI: `.github/actions/appian-promote/appian_cli.py`
- Inspect CLI: `.github/actions/appian-promote/inspect_cli.py`
- Import CLI: `.github/actions/appian-promote/import_cli.py`

Uso típico en repos wrapper
- Exportar:
  ```yaml
  - uses: vrgroup-lab/appian-cicd-core/.github/actions/appian-export@<tag>
    with:
      env: dev
      deploy_kind: app
      app_uuid: ${{ vars.APPIAN_APP_UUID }}
      app_name: MyApp
    env:
      APPIAN_DEV_API_KEY: ${{ secrets.APPIAN_DEV_API_KEY }}
      APPIAN_QA_API_KEY: ${{ secrets.APPIAN_QA_API_KEY }}
      APPIAN_PROD_API_KEY: ${{ secrets.APPIAN_PROD_API_KEY }}
      APPIAN_DEMO_API_KEY: ${{ secrets.APPIAN_DEMO_API_KEY }}
  ```
- Preparar scripts + promover:
  ```yaml
  - uses: vrgroup-lab/appian-cicd-core/.github/actions/appian-prepare-db-scripts@<tag>
    with:
      artifact-name: ${{ needs.export.outputs.artifact_name }}

  - uses: vrgroup-lab/appian-cicd-core/.github/actions/appian-promote@<tag>
    with:
      source_env: dev
      target_env: qa
      package_path: ${{ steps.package.outputs.path }}
      db_scripts_path: ${{ steps.prepare.outputs.db_scripts_path }}
      data_source: ${{ steps.prepare.outputs.data_source }}
    env:
      APPIAN_DEV_API_KEY: ${{ secrets.APPIAN_DEV_API_KEY }}
      APPIAN_QA_API_KEY: ${{ secrets.APPIAN_QA_API_KEY }}
      APPIAN_PROD_API_KEY: ${{ secrets.APPIAN_PROD_API_KEY }}
      APPIAN_DEMO_API_KEY: ${{ secrets.APPIAN_DEMO_API_KEY }}
  ```

Resolución de configuración
- Las URLs base provienen de `.github/actions/_config/appian_base_urls.env`.
- Las API keys se resuelven a partir de variables de entorno `APPIAN_<ENV>_API_KEY`
  que el repositorio llamador debe inyectar (normalmente `secrets.*`).
