# Appian CI/CD Core

Repositorio central del sistema **CI/CD para Appian**, mantenido por el equipo de Automatización y DevOps de **VR Group / Bice Vida**.  
Implementa la lógica técnica que permite exportar, inspeccionar y promover aplicaciones **Appian** entre entornos (Dev → QA → Prod), integrándose con **GitHub Actions** y la **Appian Deployment REST API**.

---

## 🔧 Propósito

El **Core** concentra las acciones reutilizables que gestionan los procesos de despliegue Appian mediante llamadas autenticadas a las APIs oficiales de Appian.  
Su objetivo es estandarizar los flujos de integración y entrega continua, garantizando seguridad, trazabilidad y consistencia entre entornos.

---

## ⚙️ Funcionalidad principal

- **Exportación:** genera paquetes `.zip` desde aplicaciones Appian mediante la API `/applications/{uuid}/package`.  
- **Inspección:** ejecuta validaciones previas sobre dependencias, errores y objetos bloqueados usando `/packages/{uuid}/inspect`.  
- **Promoción:** importa y despliega artefactos a entornos objetivo con `/deployments`.  
- **Gestión de ICF:** genera archivos `customization.properties` efímeros en función de los secretos definidos en el repo *wrapper*.  
- **Preparación SQL:** detecta y normaliza scripts de base de datos incluidos en los paquetes exportados.

Todas las interacciones se realizan mediante solicitudes REST autenticadas con API Keys organizacionales.

---

## 🧩 Componentes incluidos

- `.github/actions/appian-export` — exporta artefactos Appian desde un entorno origen.  
- `.github/actions/appian-promote` — promueve paquetes entre entornos con validación y registro.  
- `.github/actions/appian-build-icf` — genera archivos `customization.properties` temporales con valores seguros.  
- `.github/actions/appian-prepare-db-scripts` — procesa scripts SQL asociados al despliegue.  
- `.github/actions/appian-resolve-package` — obtiene identificadores (UUID) de paquetes y aplicaciones.

Cada acción encapsula llamadas REST y devuelve *outputs* normalizados para ser consumidos por los repositorios wrapper.

---

## 🔒 Seguridad y autenticación

- Las **API Keys** (`APPIAN_DEV_API_KEY`, `APPIAN_QA_API_KEY`, `APPIAN_PROD_API_KEY`) se almacenan como **secrets de organización** en GitHub.  
- Las **URLs base** de los entornos están definidas dentro del Core, en `.github/actions/_config`, y no deben configurarse manualmente en los repos wrapper.  
- Los valores sensibles nunca se imprimen ni se exponen en logs.

---

## 🌐 Llamadas a la Appian Deployment REST API

El Core interactúa con los siguientes endpoints oficiales de Appian (versión 25.3):

| Acción | Endpoint | Método | Descripción |
|--------|-----------|--------|--------------|
| Exportar aplicación | `/suite/webapi/applications/{uuid}/package` | `POST` | Genera un archivo ZIP de la aplicación. |
| Inspeccionar paquete | `/suite/webapi/packages/{uuid}/inspect` | `POST` | Analiza dependencias y conflictos previos a la importación. |
| Desplegar paquete | `/suite/webapi/deployments` | `POST` | Importa un paquete a un entorno destino. |
| Consultar estado | `/suite/webapi/deployments/{id}` | `GET` | Consulta el estado de una importación. |

Cada acción del Core encapsula estos llamados, manejando cabeceras, autenticación, control de errores y trazabilidad de forma uniforme.

Referencia: [Appian Deployment REST API – versión 25.3](https://docs.appian.com/suite/help/25.3/Deployment_Rest_API.html)

---

## 🧾 Gestión de personalización (ICF)

El Core implementa la acción `appian-build-icf`, responsable de construir el archivo `customization.properties` utilizado durante los despliegues Appian.

Este archivo se genera de forma efímera en tiempo de ejecución, a partir de los secretos definidos en el **repositorio wrapper** (por ejemplo, `ICF_OVERRIDES_QA`, `ICF_OVERRIDES_PROD`).

Formato esperado del secreto (texto plano):

```
connectedSystem.<UUID>.baseUrl=https://example
connectedSystem.<UUID>.apiKeyValue=AAA
content.<UUID>.VALUE=10
```

**Importante:**
- Los secretos `ICF_OVERRIDES_*` se definen solo en el **repo wrapper**, no en el Core.  
- El Core únicamente los **consume** para generar el archivo temporal `customization.properties` antes del despliegue.  
- El archivo es efímero y nunca imprime valores sensibles en los logs.  
- Los formatos JSON legacy siguen siendo aceptados pero se consideran **obsoletos**.

---

## 🧱 Responsabilidad del Core

- Centralizar la lógica CI/CD de Appian en acciones reutilizables.  
- Abstraer la comunicación con las APIs de Appian.  
- Garantizar compatibilidad semántica entre versiones.  
- Ofrecer una interfaz estandarizada para los repos *wrapper*.  

---

## 🧭 Versionamiento y mantenimiento

- `main`: rama estable y auditada; solo recibe merges aprobados desde `develop` y representa el estado listo para despliegues productivos.  
- `develop`: rama estable de desarrollo; concentra la integración continua y sirve como base para QA.  
- Ramas de feature/hotfix: se crean desde `develop` (ej. `feature/<ticket>-descripcion`), se validan con PR y se eliminan tras el merge.  
- Las acciones del Core permanecen inmutables en los repos wrapper; cualquier ajuste debe realizarse mediante branches internos y PR hacia `develop`.

---

## 📞 Contacto y soporte

**Equipo CI/CD Appian – VR Group / Bice Vida**

- **Consultor / Developer:** Maximiliano Tombolini — `mtombolini@vr-group.cl`  
- **Lead Delivery Service:** Ángel Barroyeta — `abarroyeta@vrgroup.cl`  
- **Arquitecto Appian:** Ignacio Arriagada — `iarriagada@vrgroup.cl`

Para incidencias o solicitudes evolutivas, abrir un **Issue** en [`appian-cicd-core`](https://github.com/vrgroup/appian-cicd-core) o contactar al equipo anterior según corresponda.
