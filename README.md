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
      base-url: https://example.appiancloud.com
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
      base-url: https://example.appiancloud.com
      package-path: path/al/paquete.zip
    secrets:
      APPIAN_API_KEY: ${{ secrets.APPIAN_API_KEY }}
```

Parámetros opcionales: `poll-timeout-sec`, `poll-interval-sec`.
