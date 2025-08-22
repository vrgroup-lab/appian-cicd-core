# appian-cicd-core

Repositorio con scripts Bash y workflows reutilizables de GitHub Actions para automatizar la exportación y promoción de artefactos en Appian.

## Requisitos
- [jq](https://stedolan.github.io/jq/)
- [curl](https://curl.se/)

## Estructura
- `docs/`: documentación y diagramas del proyecto.
- `.github/`: workflows y acciones compuestas de GitHub.
- `scripts/`: scripts de shell para exportar y promover paquetes.

## Workflows

### export.yml
Workflow reutilizable para exportar aplicaciones o paquetes desde Appian.

```yaml
jobs:
  export:
    uses: OWNER/appian-cicd-core/.github/workflows/export.yml@main
    with:
      source-env: dev
      export-type: application # o package
      uuid: 00000000-0000-0000-0000-000000000000
    secrets:
      APPIAN_API_KEY: ${{ secrets.APPIAN_API_KEY }}
```

Parámetros opcionales: `name`, `description`, `poll-timeout-sec`, `poll-interval-sec`, `download-out`.

### promote.yml
Workflow reutilizable para promover un paquete a otro entorno de Appian.

```yaml
jobs:
  promote:
    uses: OWNER/appian-cicd-core/.github/workflows/promote.yml@main
    with:
      target-env: prod
      package-path: path/al/paquete.zip
    secrets:
      APPIAN_API_KEY: ${{ secrets.APPIAN_API_KEY }}
```

Parámetros opcionales: `poll-timeout-sec`, `poll-interval-sec`.

## Configuración de entornos

Las URLs base de cada entorno se definen como variables de entorno en este
repositorio con el formato `APPIAN_<ENTORNO>_URL` (por ejemplo,
`APPIAN_DEV_URL`, `APPIAN_PROD_URL`).

Los workflows reciben el nombre del entorno (`source-env` o `target-env`) y
resuelven internamente la URL correspondiente usando estas variables.
