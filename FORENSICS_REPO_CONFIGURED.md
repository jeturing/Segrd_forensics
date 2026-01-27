╔════════════════════════════════════════════════════════════════╗
║       REPOSITORIO FORENSICS CONFIGURADO Y SINCRONIZADO         ║
╚════════════════════════════════════════════════════════════════╝

✅ CONFIGURACIÓN COMPLETADA

📦 Repositorio Forensics:
  • Ubicación Local: /opt/forensics/mcp-kali-forensics.backup (LXC 154)
  • GitHub: git@github.com:jeturing/Segrd_forensics.git
  • Branch: main
  • Estado: ✓ Sincronizado y actualizado

🔐 Autenticación SSH:
  • Llave: /root/.ssh/id_ed25519 (soc@jeturing.com)
  • Passphrase: Configurada con expect
  • Wrapper: /usr/local/bin/git-push-auto
  • Config SSH: /root/.ssh/config

🤖 Automatización CI/CD:
  • Watcher: Monitoreando cambios cada 30s
  • Build: Compilación en Docker (LXC 154)
  • Push: Automático a GitHub con expect
  • Servicio: watch-and-build.service (activo)

📁 Estructura del Pipeline:

  1. Detecta cambios en /opt/forensics/mcp-kali-forensics.backup
  2. Ejecuta build en Docker (LXC 154)
  3. Si exitoso → Commit dentro del LXC
  4. Push automático usando expect (passphrase: 321Abcd.)
  5. GitHub actualizado sin intervención manual

🚀 Comandos Útiles:

  # Ver estado general
  pipeline status

  # Build manual forensics
  pipeline build forensics

  # Ver logs en tiempo real
  pipeline follow

  # Ver estado del repo en LXC
  pct exec 154 -- bash -c "cd /opt/forensics/mcp-kali-forensics.backup && git status"

  # Push manual desde LXC
  pct exec 154 -- bash -c "cd /opt/forensics/mcp-kali-forensics.backup && /usr/local/bin/git-push-auto origin main"

📊 Repositorios Activos:

  ✓ /opt/wl → github.com:jeturing/JEturing_WL_BACK.git
  ✓ /opt/forensics (LXC 154) → github.com:jeturing/Segrd_forensics.git

🔒 Seguridad:
  • VPN Only: Desarrollo no expuesto a internet
  • SSH Keys: Autenticación con Ed25519
  • Passphrase: Manejada automáticamente con expect
  • LXC Isolation: Procesos aislados en contenedor

═══════════════════════════════════════════════════════════════════
Configurado: $(date)
Estado: ✅ OPERACIONAL
═══════════════════════════════════════════════════════════════════
