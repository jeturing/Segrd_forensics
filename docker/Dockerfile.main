FROM kalilinux/kali-rolling:latest

LABEL maintainer="jeturing-security@jeturing.local"
LABEL description="MCP Kali Forensics & IR Worker - Forensic analysis container"

# Evitar prompts interactivos
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# Actualizar sistema e instalar dependencias base
RUN apt-get update && apt-get upgrade -y && \
    apt-get install -y \
    python3 \
    python3-pip     python3-venv \
    git \
    curl \
    wget     jq \
    powershell \
    nodejs \
    npm \
    build-essential \
    libssl-dev \
    libffi-dev \
    libpq-dev \
    python3-dev \
    python3-pandas \
    python3-numpy \
    python3-sklearn python3-psycopg2 python3-asyncpg \
    yara \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Crear directorios de trabajo
RUN mkdir -p /opt/forensics-tools \
    /var/evidence \
    /var/log/mcp-forensics \
    /app/logs \
    /app

WORKDIR /app

# Copiar requirements y instalar dependencias Python
COPY requirements.txt .
RUN pip3 install --break-system-packages --ignore-installed --no-cache-dir -r requirements.txt && pip3 install --break-system-packages --no-cache-dir volatility3

# Instalar herramientas forenses
WORKDIR /opt/forensics-tools

# Sparrow 365
RUN git clone https://github.com/cisagov/Sparrow.git && \
    cd Sparrow && \
    echo "Sparrow installed"

# Hawk
RUN git clone https://github.com/OneMoreNicolas/hawk.git && \
    cd hawk && \
    pwsh -Command "Install-Module -Name ExchangeOnlineManagement -Force -AllowClobber" || true

# O365 Extractor
RUN git clone https://github.com/SecurityRiskAdvisors/sra-o365-extractor.git && \
    cd sra-o365-extractor && \
    pip3 install --break-system-packages -r requirements.txt || true

# Loki Scanner
RUN git clone https://github.com/Neo23x0/Loki.git && \
    cd Loki && \
    pip3 install --break-system-packages -r requirements.txt && \
    python3 loki-upgrader.py || true

# YARA Rules
RUN mkdir -p yara-rules && \
    cd yara-rules && \
    git clone https://github.com/Yara-Rules/rules.git community && \
    wget https://raw.githubusercontent.com/Neo23x0/signature-base/master/yara/gen_malware_set.yar || true

WORKDIR /app

# Copiar código de la aplicación
COPY api/ ./api/
COPY core/ ./core/
COPY scripts/ ./scripts/

# Crear usuario no-root para ejecución
RUN useradd -m -u 1000 forensics && \
    chown -R forensics:forensics /app && mkdir -p /app/logs && chown forensics:forensics /app/logs /var/evidence /var/log/mcp-forensics /opt/forensics-tools

USER forensics

# Exponer puerto de la API (9000 para alinear con proxy/frontend)
EXPOSE 9000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:9000/health || exit 1

# Comando de inicio
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "9000"]
