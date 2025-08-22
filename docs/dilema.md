# Arquitectura CI/CD para Appian — Opciones y Trade-offs

## Objetivo
Elegir una arquitectura CI/CD que permita:
- Desplegar apps Appian (app completa o package) a QA/Prod.
- Mantener seguridad y auditoría por ambiente.
- Escalar sin duplicar pipelines.
- Minimizar costo de mantenimiento.

---

## Opciones

### A) Core reusable + repos por app (Propuesta)
**Descripción:** Un repo `appian-cicd-core` con workflows reutilizables (`export.yml`, `promote.yml`). Cada repo de app define `deploy.yml` que llama al core y mantiene sus Environments (dev/qa/prod), Variables y Secrets.

**Pros**
- No duplicamos YAML; mejoras en un lugar.
- Secrets y approvals por app/ambiente (aislamiento).
- Soporta app completa y package por inputs (`export_scope`, `package_name`).
- Tags del core (`v1`, `v1.0.x`) → reproducibilidad y control.
- Fácil sumar apps: solo conectar al core.

**Contras**
- Requiere coordinar tags/refs del core.
- Debug a veces cruza repos (caller/core).
- Equipo debe conocer `workflow_call`.

---

### B) Repo template por app
**Descripción:** Un template de repo con pipelines completos copiados en cada app.

**Pros**
- Arranque simple; sin dependencias de otro repo.
- Autonomía total por app.

**Contras**
- Drift inevitable; arreglar bugs = N PRs.
- Inconsistencias de seguridad y calidad.
- Alto costo de mantenimiento a mediano plazo.

---

### C) Monorepo
**Descripción:** Todas las apps y pipelines en un solo repo.

**Pros**
- Cambios CI/CD impactan a todas inmediatamente.
- Trazabilidad centralizada.

**Contras**
- Blast radius alto; permisos/gobernanza complicados.
- Cadencias de release acopladas.
- Escala regular con muchas apps/equipos.

---

## Requerimientos no funcionales y comparación

| NFR                   | A) Core reusable | B) Template por app | C) Monorepo |
|-----------------------|------------------|---------------------|-------------|
| **Seguridad**         | **Alta** (aislamiento por app) | Media (depende de cada repo) | Media-Alta (compleja) |
| **Mantenibilidad**    | **Alta** (cambios 1→N) | **Baja** (drift) | Media-Alta (coupling) |
| **Escalabilidad**     | **Alta** | Media | Media |
| **Trazabilidad**      | **Alta** (auditoría por app + versión del core) | Variable | Alta central |
| **Reproducibilidad**  | **Alta** (tags) | Media | Alta |
| **Confiabilidad**     | Alta (blast radius acotado a tag) | Media-Baja | **Baja** (blast radius alto) |
| **DX**                | Media-Alta | Alta al inicio, baja después | Mixta |
| **Tiempo de cambio**  | **Alto impacto** (una mejora → N apps) | Bajo (N PRs) | Alto (una PR afecta a todas) |
| **Costo operativo**   | **Bajo/Medio** (gestión de tags) | **Alto** | Bajo en cambios, alto en gobernanza |
| **Gobernanza**        | **Alta** (estándares en core) | Baja/Media | Alta (pero burocrática) |

---

## Recomendación
**Adoptar A) Core reusable + repos por app.**  
Razones:
- Maximiza seguridad y gobernanza sin frenar a los equipos.
- Escala mejor (nuevas apps se conectan al core).
- Reduce drásticamente mantenimiento y drift respecto a templates.
- Mantiene blast radius acotado con tags.

---

## Lineamientos concretos (si elegimos A)
- **Core**: workflows reutilizables (`export.yml`, `promote.yml`), versionados por tags `v1.0.x` + alias `v1`.
- **Repos de app**: `deploy.yml` (wrapper) + `config/appian.json` + Environments `dev/qa/prod` con:
  - Variables: `APPIAN_URL`, `APP_PROPS_PUBLIC_JSON`
  - Secrets: `APPIAN_API_KEY`, `APP_PROPS_SENSITIVE_JSON`
- **Flujo**: `Deploy` hace Export (dev) → Promote (qa/prod) según input (`targets`).
- **Seguridad**: approvals por Environment de cada app; secrets nunca en git.
- **Evolución**: mejoras en core; apps actualizan `@v1` o pinnean `@v1.0.x`.

---

## Decisión pendiente
- Política de versiones (**¿alias `v1` mutable + `v1.0.x` inmutables?**).
- Frecuencia de releases del core (quincenal/mensual) y changelog.
- Métricas de adopción: número de apps integradas, tiempo promedio de despliegue, tasa de fallos por pipeline.