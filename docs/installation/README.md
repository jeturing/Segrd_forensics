# 📦 Installation - Guías Detalladas de Instalación

Instrucciones paso a paso para instalar MCP Kali Forensics.

## 📚 Documentos

- **REQUIREMENTS.md** - Requisitos del sistema
- **NATIVE_INSTALLATION.md** - Instalación nativa (Kali/WSL) ⭐ **Recomendado**
- **DOCKER_INSTALLATION.md** - Instalación con Docker
- **TROUBLESHOOTING.md** - Solucionar errores de instalación

## 🎯 Elige tu Método

### Opción 1: Instalación Nativa (Recomendado)
→ **NATIVE_INSTALLATION.md**
- Directamente en Kali Linux
- O en WSL2 en Windows
- Mejor rendimiento
- Más control

### Opción 2: Instalación con Docker
→ **DOCKER_INSTALLATION.md**
- Más aislada
- Más portátil
- Requisitos mínimos

## ⚠️ Requisitos Previos

Revisa **REQUIREMENTS.md** antes de empezar:
- RAM, disco duro, puertos
- Dependencias del sistema
- Acceso a internet
- Credenciales de M365 (opcional)

## 🛠️ Problemas

Si algo falla durante la instalación:
→ **TROUBLESHOOTING.md**

## ✅ Verificación

Después de instalar, verifica que todo funciona:
```bash
# Comprobar backend
curl http://localhost:8888/health

# Comprobar frontend
curl http://localhost:3000
```
