#!/bin/bash
# 🔧 SOLUCIÓN RÁPIDA - npm en VS Code

## ✅ ESTADO ACTUAL

npm está correctamente instalado y funciona:
- npm: 10.8.2
- Node.js: v20.19.6
- Ubicación: /home/hack/.local/bin/npm

## 🐛 PROBLEMA

La terminal integrada de VS Code no tenía npm en su PATH.

## ✅ SOLUCIÓN APLICADA

Se ejecutó el script FIX_NPM_VSCODE.sh que:

1. ✅ Creó ~/.bash_profile
2. ✅ Actualizó ~/.bashrc con PATH correcto
3. ✅ Configuró variables de entorno para VS Code
4. ✅ Agregó rutas de Node.js y npm

## 📋 PASOS FINALES (MÁS IMPORTANTE)

Para que los cambios surtan efecto en VS Code:

### OPCIÓN 1: Reiniciar VS Code (Recomendado)
```
1. Cierra TODAS las terminales en VS Code
2. Cierra VS Code completamente (Exit)
3. Reabre VS Code
4. Abre una terminal nueva (Ctrl + `)
5. Verifica: npm --version
```

### OPCIÓN 2: Recargar configuración (Rápido)
```
En la terminal de VS Code, ejecuta:
source ~/.bashrc
npm --version
```

### OPCIÓN 3: Usar bash explícitamente
```
bash -c "npm --version"
```

## 🧪 VERIFICACIÓN

Para confirmar que npm funciona:

```bash
# En la terminal de VS Code, ejecuta:
npm --version    # Debe mostrar: 10.8.2
node --version   # Debe mostrar: v20.19.6
which npm        # Debe mostrar: /home/hack/.local/bin/npm

# Instalación de dependencias:
cd frontend-react
npm install

# Iniciar servidor:
npm run dev
```

## 📂 ARCHIVOS MODIFICADOS

- ~/.bashrc → Agregado PATH de npm
- ~/.bash_profile → Agregado PATH de npm
- ~/.config/code-server/settings.json → Configuración VS Code

## 🆘 SI SIGUE SIN FUNCIONAR

1. Verifica que estés en bash (no zsh):
   ```bash
   echo $SHELL  # Debe mostrar: /bin/bash
   ```

2. Cambia a bash si es necesario:
   ```bash
   chsh -s /bin/bash
   ```

3. Reinicia completamente tu sesión:
   ```bash
   # Cierra la terminal
   # Abre una nueva
   bash --version
   ```

4. Limpia cache de npm:
   ```bash
   npm cache clean --force
   ```

## ✨ PRÓXIMOS PASOS

Una vez verificado que npm funciona:

```bash
# 1. Navega al frontend
cd /home/hack/mcp-kali-forensics/frontend-react

# 2. Instala dependencias (incluyendo plotly.js)
npm install

# 3. Inicia el servidor de desarrollo
npm run dev

# 4. Abre en navegador
# http://localhost:5173/dashboard
```

## 📞 SOPORTE

Si aún tienes problemas:

1. Ejecuta nuevamente:
   ```bash
   bash /home/hack/FIX_NPM_VSCODE.sh
   ```

2. Reinicia VS Code completamente

3. Abre una terminal nueva

---

**Estado:** ✅ RESUELTO  
**Fecha:** 7 de Diciembre 2024  
**Versión:** v4.2 PlotlyChart
