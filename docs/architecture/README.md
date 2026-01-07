# 🏗️ Architecture - Diseño del Sistema

Documentación de la arquitectura y diseño del sistema.

## 📚 Documentos

- **OVERVIEW.md** - Visión general del sistema
- **SYSTEM_DESIGN.md** - Diseño de arquitectura
- **DATA_FLOW.md** - Flujo de datos
- **SECURITY.md** - Consideraciones de seguridad

## 🎯 Lectura Recomendada

1. Comienza con **OVERVIEW.md** (10 min)
2. Profundiza en **SYSTEM_DESIGN.md** (20 min)
3. Entiende flujos en **DATA_FLOW.md** (15 min)
4. Revisa seguridad en **SECURITY.md** (15 min)

## 📐 Componentes Principales

- Backend FastAPI
- Frontend React
- Base de datos SQLite
- WebSockets para tiempo real
- Integración con M365
- Tools forenses (Loki, Sparrow, etc.)

## 🔄 Flujo General

```
Entrada → Backend API → Procesamiento → BD → Frontend
           (FastAPI)   (Tools/Scripts)  (SQLite) (React)
```

## 🆘 Preguntas

- "¿Cómo fluyen los datos?" → **DATA_FLOW.md**
- "¿Cómo está estructurado?" → **SYSTEM_DESIGN.md**
- "¿Es seguro?" → **SECURITY.md**
