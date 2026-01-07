# Guía de Instalación Nativa - MCP Kali Forensics

## 🎯 Instalación en Kali Linux / WSL

Esta guía te ayudará a instalar el MCP directamente en tu sistema Kali Linux o WSL2 **sin usar Docker**.

### Requisitos Previos

- **Sistema**: Kali Linux 2023+ o WSL2 con Kali
- **Python**: 3.9 o superior
- **Privilegios**: sudo para instalación de herramientas
- **Espacio**: ~5GB para herramientas forenses
- **Red**: Conexión a internet para descargar dependencias

### ⚡ Instalación Rápida (Automatizada)

```bash
# 1. Navegar al directorio del proyecto
cd /home/hack/mcp-kali-forensics

# 2. Ejecutar instalador nativo
chmod +x scripts/setup_native.sh
./scripts/setup_native.sh
```

El script realizará automáticamente:
1. ✅ Actualización del sistema
2. ✅ Instalación de Python 3.11+
3. ✅ Creación de directorios (`/opt/forensics-tools`, `~/forensics-evidence`)
4. ✅ Instalación de herramientas forenses:
   - PowerShell Core
   - YARA
   - OSQuery
   - Volatility 3
   - Loki Scanner
   - Sparrow 365
   - Hawk
   - YARA Rules
   - O365 Extractor
5. ✅ Creación de entorno virtual Python
6. ✅ Instalación de dependencias Python
7. ✅ Generación de `.env` con API key aleatoria
8. ✅ Configuración de permisos

### 🔧 Instalación Manual (Paso a Paso)

Si prefieres controlar cada paso:

#### 1. Instalar dependencias del sistema

```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv python3-dev
sudo apt install -y build-essential libssl-dev libffi-dev
sudo apt install -y yara osquery git wget
```

#### 2. Instalar PowerShell Core

```bash
wget -q https://packages.microsoft.com/config/debian/11/packages-microsoft-prod.deb -O /tmp/packages-microsoft-prod.deb
sudo dpkg -i /tmp/packages-microsoft-prod.deb
sudo apt update
sudo apt install -y powershell
rm /tmp/packages-microsoft-prod.deb
```

#### 3. Crear directorios

```bash
sudo mkdir -p /opt/forensics-tools
mkdir -p ~/forensics-evidence
mkdir -p logs
```

#### 4. Instalar herramientas forenses

```bash
cd /opt/forensics-tools

# Loki Scanner
sudo git clone https://github.com/Neo23x0/Loki.git
cd Loki && sudo pip3 install -r requirements.txt && cd ..

# Sparrow 365
sudo git clone https://github.com/cisagov/Sparrow.git

# Hawk
sudo git clone https://github.com/T0pCyber/hawk.git Hawk

# YARA Rules
sudo git clone https://github.com/Yara-Rules/rules.git yara-rules

# O365 Extractor
sudo git clone https://github.com/PwC-IR/Office-365-Extractor.git
cd Office-365-Extractor && sudo pip3 install -r requirements.txt && cd ..

# Volatility 3
sudo apt install -y volatility3 || sudo git clone https://github.com/volatilityfoundation/volatility3.git
```

#### 5. Configurar proyecto Python

```bash
cd /home/hack/mcp-kali-forensics

# Crear entorno virtual
python3 -m venv venv

# Activar entorno virtual
source venv/bin/activate

# Instalar dependencias
pip install --upgrade pip
pip install -r requirements.txt
```

#### 6. Configurar variables de entorno

```bash
# Copiar plantilla
cp .env.example .env

# Generar API key
API_KEY=$(openssl rand -hex 32)
echo "API_KEY=$API_KEY" >> .env

# Editar configuración
nano .env
```

### 🔐 Configuración de Credenciales

Edita `.env` con tus credenciales:

```env
# ========================================
# MCP Kali Forensics - Configuración
# ========================================

# API Key (generada automáticamente)
API_KEY=tu-api-key-generada-aqui

# Microsoft 365 (REQUERIDO para análisis M365)
M365_TENANT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
M365_CLIENT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
M365_CLIENT_SECRET=tu-client-secret

# Have I Been Pwned API (OPCIONAL)
HIBP_ENABLED=true
HIBP_API_KEY=tu-hibp-api-key

# Dehashed API (OPCIONAL)
DEHASHED_ENABLED=false
DEHASHED_API_KEY=

# Jeturing CORE (OPCIONAL)
JETURING_CORE_ENABLED=false
JETURING_CORE_URL=https://core.jeturing.local
JETURING_CORE_API_KEY=

# Tailscale (OPCIONAL - para acceso remoto)
TAILSCALE_ENABLED=false
TAILSCALE_AUTH_KEY=

# Debug
DEBUG=false
```

### 🚀 Iniciar el Servicio

#### Modo Desarrollo (Manual)

```bash
# Activar entorno virtual
cd /home/hack/mcp-kali-forensics
source venv/bin/activate

# Iniciar con recarga automática
uvicorn api.main:app --host 0.0.0.0 --port 8080 --reload

# Acceder a Swagger UI
xdg-open http://localhost:8080/docs
```

#### Modo Producción (Systemd Service)

```bash
# 1. Copiar archivo de servicio
sudo cp scripts/mcp-forensics.service /etc/systemd/system/

# 2. Recargar systemd
sudo systemctl daemon-reload

# 3. Habilitar inicio automático
sudo systemctl enable mcp-forensics

# 4. Iniciar servicio
sudo systemctl start mcp-forensics

# 5. Verificar estado
sudo systemctl status mcp-forensics

# 6. Ver logs en tiempo real
sudo journalctl -u mcp-forensics -f
```

### ✅ Verificar Instalación

```bash
# Verificar herramientas instaladas
cd /home/hack/mcp-kali-forensics
./scripts/check_tools.sh

# Debería mostrar:
# ✓ Python 3.x
# ✓ PowerShell Core
# ✓ YARA
# ✓ OSQuery
# ✓ Volatility 3
# ✓ Loki Scanner
# ✓ Sparrow 365
# ✓ Hawk
# ✓ O365 Extractor

# Verificar API
curl http://localhost:8080/health

# Respuesta esperada:
# {"status":"healthy","version":"1.0.0"}
```

### 🔧 Ajustes de Permisos

```bash
# Dar permisos de lectura a herramientas
sudo chmod -R a+rX /opt/forensics-tools

# Asegurar permisos de escritura en evidencia
chmod -R u+rwX ~/forensics-evidence

# Verificar que el usuario puede ejecutar herramientas
python3 /opt/forensics-tools/Loki/loki.py --version
yara --version
osqueryi --version
pwsh --version
```

### 📂 Estructura de Directorios

```
/opt/forensics-tools/           # Herramientas forenses (sudo)
├── Loki/                       # IOC Scanner
├── Sparrow/                    # M365 analyzer
├── Hawk/                       # Email forensics
├── yara-rules/                 # Reglas YARA
├── Office-365-Extractor/       # O365 logs
└── volatility3/                # Memory forensics

/home/hack/mcp-kali-forensics/  # Proyecto MCP
├── api/                        # Backend FastAPI
├── venv/                       # Entorno virtual Python
├── logs/                       # Logs de aplicación
├── .env                        # Configuración
└── forensics.db                # Base de datos SQLite

/home/hack/forensics-evidence/  # Evidencia de casos
└── IR-2024-001/               # Caso ejemplo
    ├── sparrow/               # Resultados Sparrow
    ├── hawk/                  # Resultados Hawk
    ├── loki/                  # Resultados Loki
    └── yara/                  # Detecciones YARA
```

### 🐛 Troubleshooting

#### Error: "Permission denied" al ejecutar herramientas

```bash
sudo chmod -R a+rX /opt/forensics-tools
```

#### Error: "Module not found" al iniciar API

```bash
# Asegúrate de activar el entorno virtual
source venv/bin/activate

# Reinstalar dependencias
pip install -r requirements.txt
```

#### Error: PowerShell no encontrado

```bash
# Verificar instalación
which pwsh

# Si no está instalado, reinstalar:
wget https://packages.microsoft.com/config/debian/11/packages-microsoft-prod.deb
sudo dpkg -i packages-microsoft-prod.deb
sudo apt update
sudo apt install -y powershell
```

#### Error: OSQuery no funciona en WSL

OSQuery puede tener limitaciones en WSL. Para análisis completo, usa un endpoint Linux nativo.

#### Logs de errores

```bash
# Logs de aplicación
tail -f logs/mcp-forensics.log

# Logs de systemd (si usas servicio)
sudo journalctl -u mcp-forensics -n 50

# Logs de herramientas específicas
ls ~/forensics-evidence/IR-*/*/
```

### 🔄 Actualizar MCP

```bash
cd /home/hack/mcp-kali-forensics

# Detener servicio (si está corriendo)
sudo systemctl stop mcp-forensics

# Actualizar código
git pull

# Activar entorno virtual
source venv/bin/activate

# Actualizar dependencias
pip install -r requirements.txt --upgrade

# Reiniciar servicio
sudo systemctl start mcp-forensics
```

### 📖 Siguiente Paso

Lee [USAGE.md](USAGE.md) para aprender a usar el MCP y ejecutar análisis forenses.
