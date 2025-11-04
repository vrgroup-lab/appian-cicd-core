# appian-promote (v1)

Composite action que inspecciona e importa paquetes Appian en entornos gestionados por el Core.

## Inputs
- `source_env` (string, required): Entorno origen, solo para logging.
- `target_env` (string, required): Entorno destino.
- `package_path` (string, required): Ruta al ZIP a importar.
- `icf_path` (string, optional): Ruta al Import Customization File (ICF) generado previamente.
- `dry_run` (string/bool, optional): Si es `true` solo simula la llamada.

## Outputs
- `deployment_status`: Estado final reportado por Appian (por ejemplo `COMPLETED`).
- `deployment_uuid`: Identificador del deployment generado por Appian.

## Ejemplo
```yaml
- name: Promover a QA
  uses: vrgroup-lab/appian-cicd-core/.github/actions/appian-promote@v1
  env:
    APPIAN_API_KEY_TARGET: ${{ secrets.APPIAN_QA_API_KEY }}
  with:
    source_env: dev
    target_env: qa
    package_path: artifacts/my-app.zip
    icf_path: ${{ steps.build_icf.outputs.icf_path }}
```
