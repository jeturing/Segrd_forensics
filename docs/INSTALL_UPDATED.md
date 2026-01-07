# Instalación y correcciones automáticas (Actualizado)

Este documento resume las mejoras del instalador automátizado y los pasos que realiza `./scripts/install.sh` ahora.

Qué hace ahora el instalador:

- Crea la estructura de directorios necesaria (`tools`, `logs`, `evidence`, `forensics-evidence`).
- Clona las herramientas forenses configuradas (si están disponibles).
- Crea y configura un `venv` local en `./venv`.
- Asegura permisos en `venv` y `logs` (corrige situaciones donde `venv` o `logs` fueron creados por `root`).
- Instala `requirements.txt` y, adicionalmente, instala `pydantic[email]`, `flask` y `requests` para cubrir casos de runtime (validación de emails y proxy simple).
- Intenta instalar Node.js LTS vía `nvm` si `npm` no está presente. Si `nvm` no puede instalarse, el script mostrará una advertencia y te pedirá instalar Node manualmente.

Comandos importantes (manuales que pueden necesitar sudo en macOS):

- Forzar propiedad de venv/logs (si ves errores de permisos):

```bash
sudo chown -R "$(whoami)":"$(id -gn)" /path/to/project/venv /path/to/project/logs /path/to/project/.env
```

- Ejecutar instalador:

```bash
./install.sh
# o
./scripts/install.sh
```

- Si `npm` no se instaló automáticamente, instala Node (ejemplo con Homebrew):

```bash
brew install node
```

Notas de resolución de problemas:

- Si ves errores de `email-validator` o `ModuleNotFoundError: No module named 'flask'`, ejecuta dentro del `venv`:

```bash
source venv/bin/activate
pip install "pydantic[email]" flask requests
```

- Si el backend falla por variables de entorno faltantes, revisa `./.env` y añade las claves necesarias (por ejemplo `JETURING_CORE_API_KEY`).

- Para exponer rápidamente algo en `:3000` cuando el frontend no está disponible, el repo incluye `scripts/proxy3000.py` que reenvía tráfico al backend (`:9000`) — instala `flask` y ejecuta:

```bash
python scripts/proxy3000.py
```

Si quieres, puedo integrar pasos adicionales (por ejemplo, detección e instalación de Homebrew, o opciones para instalar Node por defecto).