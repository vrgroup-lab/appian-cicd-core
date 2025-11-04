# appian-build-icf (v1)

Genera un Import Customization File (ICF) efímero combinando overrides no sensibles (YAML)
y sensibles (JSON inyectado vía `ICF_JSON_OVERRIDES`).

## Inputs
- `template_path` (string, required): Ruta al template `.properties` dentro del repo caller.
- `map_path` (string, optional): YAML con overrides no sensibles. Puede contener nodos por entorno.
- `env` (string, required): Entorno de destino (`dev`, `qa`, `prod`).
- `out_path` (string, required): Ruta donde se escribe el `.properties` generado.

## Outputs
- `icf_path`: Ruta absoluta al ICF generado en el runner.

## Variables de entorno
- `ICF_JSON_OVERRIDES` (string, opcional): JSON con overrides sensibles. La action no acepta secretos por `with:`.

## Ejemplo
```yaml
- name: Construir ICF efímero
  uses: vrgroup-lab/appian-cicd-core/.github/actions/appian-build-icf@v1
  env:
    ICF_JSON_OVERRIDES: ${{ secrets.ICF_JSON_OVERRIDES }}
  with:
    template_path: provisioning/icf-template.properties
    map_path: provisioning/env/dev.yml
    env: dev
    out_path: ${{ runner.temp }}/icf-dev.properties
```
