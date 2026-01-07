# 🚀 MCP Forensics React Frontend

Frontend moderno con React 18 + Vite para la plataforma MCP Kali Forensics & IR.

## ✨ Características

- ✅ **Interfaz Moderna**: Diseño tipo Microsoft Sentinel
- ✅ **Menú Funcional**: Sidebar con navegación fluida
- ✅ **Estado Global**: Redux Toolkit para gestión de estado
- ✅ **TypeScript Ready**: Preparado para migración a TS
- ✅ **Responsive**: Mobile-first, funciona en todos los dispositivos
- ✅ **Dark Mode**: Tema oscuro profesional por defecto
- ✅ **Real-time**: Socket.io ready para actualizaciones en vivo

## 📋 Requisitos

- Node.js >= 18.0.0
- npm >= 9.0.0

## 🔧 Instalación

### 1. Clonar/Navegar al directorio

```bash
cd /home/hack/mcp-kali-forensics/frontend-react
```

### 2. Instalar dependencias

```bash
npm install
```

### 3. Configurar variables de entorno

```bash
cp .env.example .env
```

Editar `.env` si es necesario:
```
VITE_API_URL=http://localhost:9000/api
VITE_WS_URL=ws://localhost:9000/ws
VITE_APP_NAME=MCP Kali Forensics & IR
VITE_ENVIRONMENT=development
VITE_DEBUG=true
```

### 4. Iniciar servidor de desarrollo

```bash
npm run dev
```

Abre http://localhost:3000 en el navegador.

## 📦 Estructura

```
src/
├── components/        # Componentes React
│   ├── Layout/       # Sidebar, Topbar, Layout
│   ├── Dashboard/    # Dashboard principal
│   ├── Common/       # Componentes reutilizables (Button, Card, Alert, etc)
│   └── Investigations/  # (En construcción)
├── services/         # APIs y servicios
│   └── cases.js     # Servicio de casos
├── store/            # Redux store
│   └── reducers/     # Slices de Redux
├── hooks/            # Custom Hooks
├── styles/           # Estilos globales
└── App.jsx          # Componente principal
```

## 🎯 Menú Funcional

El menú lateral incluye:

**Principal**
- 🏠 Dashboard
- 🔍 Investigaciones
- 📊 Grafo de Ataque

**Análisis**
- ☁️ Microsoft 365
- 🔌 Agentes Remotos
- 🔑 Credenciales

**Amenazas**
- 🎯 Threat Hunting
- ⚡ Inteligencia IOC
- ⏱️ Timeline Forense

**Reportes**
- 📋 Reportes
- 🏢 Gestión Tenants

## 🚀 Comandos

```bash
# Desarrollo
npm run dev

# Build para producción
npm run build

# Preview del build
npm run preview

# Linting
npm run lint
npm run lint:fix

# Formateo de código
npm run format

# Tests
npm run test
npm run test:ui
```

## 🔌 Integración Backend

El frontend se conecta al backend FastAPI en `http://localhost:9000`:

```javascript
// Proxy automático en development
/api/* → http://localhost:9000/api/*
/ws/* → ws://localhost:9000/ws/*
```

## 📱 Componentes Disponibles

### Common Components

```jsx
import { Button, Card, Alert, Loading } from '@/components/Common';

<Button variant="primary" onClick={handleClick}>
  Hacer algo
</Button>

<Card title="Mi Tarjeta" icon={SomeIcon}>
  Contenido aquí
</Card>

<Alert type="warning" message="Advertencia" />

<Loading message="Cargando..." />
```

### Services

```jsx
import { caseService } from '@/services/cases';

const cases = await caseService.getCases(1, 10);
const newCase = await caseService.createCase(data);
```

### Redux

```jsx
import { useDispatch, useSelector } from 'react-redux';
import { fetchCases, selectCase } from '@/store/reducers/caseReducer';

const dispatch = useDispatch();
const { items, loading } = useSelector(state => state.cases);

dispatch(fetchCases({ page: 1, limit: 10 }));
```

## 🎨 Tailwind CSS

El proyecto usa Tailwind CSS v3 para estilos. Clases personalizadas disponibles:

```jsx
// Utilidades
<button className="btn btn-primary">Primario</button>
<button className="btn btn-secondary btn-sm">Secundario</button>

<div className="card">Tarjeta</div>
<input className="input-base" />

<span className="badge badge-danger">Crítico</span>

<div className="alert alert-warning">Alerta</div>
```

## 📚 Documentación Adicional

- [React Router v6](https://reactrouter.com/)
- [Redux Toolkit](https://redux-toolkit.js.org/)
- [Tailwind CSS](https://tailwindcss.com/)
- [Vite](https://vitejs.dev/)

## 🐛 Troubleshooting

### Puerto 3000 en uso
```bash
# Cambiar puerto en vite.config.js
server: {
  port: 3001
}
```

### CORS errors
Asegúrate de que el backend en `http://localhost:9000` está ejecutando.

### Módulos no encontrados
```bash
rm -rf node_modules package-lock.json
npm install
```

## 📄 Licencia

Mismo que el proyecto principal (MCP Kali Forensics)

---

**Estado**: 🟢 Funcional - Menú y componentes base listos. Páginas en construcción.
