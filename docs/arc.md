# Arquitectura CI/CD para Apps Appian

> **Resumen:** Orquestamos despliegues de múltiples aplicaciones Appian desde GitHub.  
> Cada aplicación tiene su **repo propio** (basado en **template**), que invoca **workflows core** alojados en un **Repo Core**.  
> En **Fase 1** operamos solo con GitHub (sin AWS). En **Fase 2** integramos **AWS Secrets Manager** (vía OIDC) para credenciales seguras.

---

## 0) Imagen de Arquitectura

![Arquitectura CI/CD](../out/arc/arc.png)

### Explicación del Diagrama

El diagrama ilustra la interacción entre los principales componentes de la arquitectura:

- **GitHub:** Plataforma central que aloja tanto los repositorios de las aplicaciones como el repositorio Core, el cual contiene los workflows compartidos.
- **Repo Core:** Almacena y gestiona los workflows centrales que orquestan los despliegues y procesos CI/CD de las aplicaciones Appian, garantizando consistencia y reutilización.
- **AWS:** Incorporado en la Fase 2, integra AWS Secrets Manager mediante OIDC para almacenar y recuperar de forma segura las credenciales (API keys) en una bóveda centralizada.
- **Appian Cloud:** Entornos de origen y destino (Dev, QA, Prod) donde se exportan, inspeccionan y despliegan las aplicaciones Appian.

---

## 1) Descripción de la Arquitectura

La arquitectura está diseñada para facilitar la gestión y despliegue de múltiples aplicaciones Appian de forma centralizada y segura. Cada aplicación posee su propio repositorio basado en un template estándar que contiene las configuraciones específicas y los objetos versionados.

Estos repositorios de aplicaciones invocan workflows definidos en un repositorio Core, que centraliza la lógica de CI/CD. Esto permite reutilizar procesos y mantener consistencia en los despliegues.

En la Fase 1, toda la orquestación se realiza únicamente con GitHub Actions, sin integración con servicios externos. En la Fase 2, se añade la integración con AWS Secrets Manager para manejar credenciales sensibles de forma segura, evitando exponerlas en los repositorios.

---

## 2) Fases de Implementación

- **Fase 1:**  
  Más que nada consiste en un refactor estructural para darle soporte centralizado al sistema, partiendo de la base de la arquitectura anterior ya desarrollada. La operación es exclusiva con GitHub Actions: los workflows se ejecutan dentro de GitHub, utilizando archivos de configuración y variables de entorno para manejar credenciales y parámetros. No se utiliza AWS ni otros servicios externos para gestión de secretos en esta etapa.

- **Fase 2:**  
  Se integra AWS Secrets Manager mediante OIDC para la autenticación segura desde GitHub Actions. Esto permite almacenar y recuperar credenciales sensibles de forma centralizada y segura, mejorando la seguridad y facilitando la gestión de secretos en los despliegues.

---

## 3) Repositorios de Aplicaciones

Cada aplicación Appian cuenta con un repositorio propio, basado en un template común que estandariza la estructura y configuración.  
En estos repositorios **no se almacena código fuente tradicional**, sino:

- Archivos `.zip` que contienen los objetos Appian exportados.
- Archivos de configuración específicos de la aplicación.
- Referencias para invocar los workflows del Repo Core.
- Template del archivo `.properties` para parametrización (sin incluir valores reales ni secretos).

Bajo el concepto de **release**, cada despliegue exitoso encapsula los datos y objetos exportados en un artefacto versionado, garantizando trazabilidad de qué se desplegó y cuándo, sin exponer información sensible.  
Este modelo permite un desarrollo independiente para cada aplicación y facilita la integración continua y despliegue automatizado mediante los workflows centralizados en el Repo Core.

---

## 4) Manejo de archivos `.properties`

En la nueva arquitectura, los `.properties` se tratan como **archivos desechables y dinámicos**, asegurando que no dejen trazabilidad persistente en repositorios ni en históricos.  
Su objetivo es parametrizar el despliegue en tiempo de ejecución, usando únicamente **GitHub Secrets** y **Variables de Environment** como fuente de datos.

**Flujo de trabajo:**

1. **Export (Dev)** → El Core obtiene el template del export (app o package) y detecta las llaves requeridas.
2. **Sync/Validate (target env)** → El Core lee, en el *Environment* correspondiente del repo de la app:
   - **Variables:** `APP_PROPS_PUBLIC_JSON`
   - **Secrets:** `APP_PROPS_SENSITIVE_JSON`  
   Luego compara ambas contra las llaves requeridas.
3. **Si faltan llaves**:
   - El job publica un resumen (Job Summary) con la lista y crea un *Issue* con checklist.
   - El job queda bloqueado esperando el **approval del Environment** (QA/Prod).
   - Antes de aprobar, el usuario edita en GitHub los valores de `APP_PROPS_PUBLIC_JSON` y/o `APP_PROPS_SENSITIVE_JSON` para completar lo faltante.
   - Una vez guardado, se aprueba el Environment y el job continúa.
4. **Build** → El Core construye `app.properties` en **runtime** (merge de PUBLIC_JSON + SENSITIVE_JSON + overrides) y continúa con la importación.

**Ventajas del enfoque:**
- No se almacena ningún `.properties` sensible en el repo ni en histórico.
- Los valores se solicitan solo cuando son necesarios y se eliminan al final del proceso.
- El pipeline no falla por llaves faltantes: queda en espera controlada hasta completar la información.
---

## 5) Estimación de Esfuerzo y Refactor

Para adoptar esta arquitectura se requiere un refactor significativo dividido en dos fases:

### Estimación de Esfuerzo (horas de desarrollo y pruebas)

#### **Fase 1 – Refactor estructural y centralización en Repo Core**
- Análisis y levantamiento de arquitectura actual: **6 h**  
- Diseño y ajuste de template de repos de aplicaciones: **8 h**  
- Refactor de workflows y modularización (export/promote): **18 h**  
- Ajuste de manejo de `.properties` desechables y validaciones: **10 h**  
- Pruebas de integración end‐to‐end (Dev → QA → Prod): **12 h**  
- Documentación y capacitación interna: **6 h**  

**Subtotal Fase 1:** **60 h**

#### **Fase 2 – Integración AWS + Middleware**
- Configuración de AWS Secrets Manager, roles y políticas IAM con OIDC: **4 h**  
- Desarrollo de Lambda broker de secretos + proxy Appian Deployment API v2: **10 h**  
- Configuración de API Gateway para invocar Lambda de forma segura: **4 h**  
- Integración con GitHub Actions (OIDC + API Gateway): **6 h**  
- Pruebas unitarias e integración end-to-end: **6 h**  
- Documentación y entrenamiento: **3 h**  

**Subtotal Fase 2:** **33 h**

**Total estimado:** **93 h**

Este esfuerzo permitirá mejorar la escalabilidad, seguridad y mantenibilidad de los procesos CI/CD para las aplicaciones Appian, además de habilitar un manejo seguro y dinámico de credenciales en la segunda fase.