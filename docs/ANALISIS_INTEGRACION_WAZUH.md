# Análisis de Integración: Wazuh como Agente de Endpoint

## 1. Evaluación de la Propuesta
Integrar Wazuh como agente de endpoint es una **excelente opción** para potenciar las capacidades de detección y respuesta del MCP Kali Forensics.

### ✅ Ventajas (Pros)
*   **Detección en Tiempo Real**: Wazuh ofrece FIM (File Integrity Monitoring), detección de rootkits y análisis de logs en tiempo real.
*   **Respuesta Activa**: Permite ejecutar scripts de respuesta (bloqueo de IP, aislamiento) automáticamente, lo cual se alinea con el módulo SOAR del MCP.
*   **Multi-plataforma**: Agentes ligeros para Windows, Linux, macOS.
*   **Compliance**: Ayuda con PCI-DSS, HIPAA, GDPR (valor añadido para SaaS).
*   **Open Source**: Sin costes de licencia, compatible con la filosofía del proyecto.

### ❌ Desafíos (Cons)
*   **Complejidad de Gestión**: Requiere mantener un Wazuh Manager (server) y Indexer (Elasticsearch/OpenSearch), lo que aumenta la carga de recursos.
*   **Despliegue**: El agente requiere instalación y configuración de claves.

## 2. Arquitectura Propuesta

### A. Despliegue del Wazuh Manager
Recomendamos desplegar el **Wazuh Manager** como un contenedor adicional en el stack del MCP (`docker-compose.yml` o Helm chart).
*   **Imagen**: `wazuh/wazuh-manager:latest`
*   **Puertos**: 1514 (Agentes), 55000 (API).

### B. Integración con MCP (Backend)
El MCP actuará como orquestador y consumidor de inteligencia:
1.  **Ingesta de Alertas**: Configurar Wazuh para enviar alertas críticas al MCP vía Webhook o Syslog (`logging-worker`).
2.  **Automatización (SOAR)**:
    *   Alerta Wazuh -> MCP Webhook -> Trigger Playbook.
    *   Ejemplo: "Wazuh detecta Mimikatz" -> MCP ejecuta playbook "Aislamiento de Host" -> MCP ordena a Wazuh Agent bloquear red.
3.  **Gestión de Agentes**:
    *   El MCP puede usar la API de Wazuh para listar agentes, ver estado y extraer logs.

### C. Despliegue de Agentes (Frontend)
En el Dashboard del MCP:
1.  Crear sección "Agentes / Sensores".
2.  Generar comandos de instalación automática (PowerShell/Bash) que apunten al Wazuh Manager del MCP.
3.  Visualizar estado de salud de los agentes.

## 3. Plan de Acción
1.  Añadir `wazuh-manager` al `docker-compose.yml`.
2.  Crear servicio `api/services/wazuh_integration.py` para consumir la API de Wazuh.
3.  Crear rutas `api/routes/wazuh.py` para exponer datos al frontend.
4.  Actualizar frontend para mostrar alertas y estado de agentes.

## Conclusión
La integración es **altamente recomendada** y factible. Transformará el MCP de una herramienta de respuesta reactiva a una plataforma de monitoreo continuo y respuesta activa (XDR).
