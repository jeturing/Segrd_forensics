# SEGRD Landing Page Implementation

**Versión:** 1.0.0  
**Fecha:** 2026-01-06  
**Autor:** Jeturing Web Team

---

## 📋 Resumen

Se implementó una landing page completa para SEGRD con:
- **i18n** (EN/ES) usando i18next
- **SEO** con JSON-LD schemas para AI discoverability
- **Diseño responsive** con Tailwind CSS
- **Componentes modulares** en React

---

## 🗂️ Estructura de Archivos

```
frontend-react/src/
├── i18n/
│   └── index.js                    # Configuración i18next
├── locales/
│   ├── en/
│   │   ├── common.json             # Nav, footer, CTAs
│   │   ├── landing.json            # Hero, value props, markets
│   │   ├── modules.json            # 7 módulos SEGRD
│   │   └── faq.json                # FAQ estructurado
│   └── es/
│       ├── common.json
│       ├── landing.json
│       ├── modules.json
│       └── faq.json
├── components/
│   ├── landing/
│   │   ├── index.js                # Exports centralizados
│   │   ├── Navbar.jsx              # Navegación con i18n
│   │   ├── HeroSection.jsx         # Hero con CTA
│   │   ├── ValueProps.jsx          # 4 propuestas de valor
│   │   ├── ModulesGrid.jsx         # Grid de 7 módulos
│   │   ├── TargetMarkets.jsx       # SOC, Legal, Banking
│   │   ├── BYOLLMSection.jsx       # BYO-LLM explicación
│   │   ├── FAQSection.jsx          # Acordeón FAQ
│   │   ├── CTASection.jsx          # Call to action final
│   │   ├── Footer.jsx              # Footer con links
│   │   └── LanguageSwitcher.jsx    # Selector EN/ES
│   └── seo/
│       └── JsonLdSchema.jsx        # Schemas estructurados
└── pages/
    └── Landing/
        └── LandingPage.jsx         # Página principal
```

---

## 🌐 Internacionalización (i18n)

### Configuración

```javascript
// src/i18n/index.js
import i18n from 'i18next';
import LanguageDetector from 'i18next-browser-languagedetector';
// ... configuración completa
```

### Uso en Componentes

```jsx
import { useTranslation } from 'react-i18next';

const Component = () => {
  const { t } = useTranslation('landing');
  return <h1>{t('hero.title')}</h1>;
};
```

### Cambiar Idioma

```jsx
import { useTranslation } from 'react-i18next';

const LanguageSwitcher = () => {
  const { i18n } = useTranslation();
  return (
    <button onClick={() => i18n.changeLanguage('es')}>ES</button>
  );
};
```

---

## 🔍 SEO & AI Discoverability

### JSON-LD Schemas Implementados

1. **Organization** - Jeturing Inc. como empresa
2. **SoftwareApplication** - SEGRD como producto
3. **FAQPage** - Preguntas frecuentes estructuradas
4. **WebSite** - Schema del sitio con SearchAction
5. **Product** - Cada módulo como producto

### Meta Tags Optimizados

- Open Graph (Facebook, LinkedIn)
- Twitter Cards
- Keywords para DFIR, SOC, forensics
- Robots meta para AI crawlers

---

## 🎨 Componentes Landing

### HeroSection
- Título animado con badge MCP-First
- Descripción dinámica por idioma
- CTAs primario/secundario
- Trust badges (SOC 2, GDPR, etc.)

### ValueProps
- 4 cards con iconos SVG
- Hover effects
- Contenido desde i18n

### ModulesGrid
- 7 módulos SEGRD
- Gradientes por módulo
- Preview de herramientas
- Links a páginas de módulo

### TargetMarkets
- 3 segmentos: SOC, Legal, Banking
- Features list por segmento
- Iconos personalizados

### BYOLLMSection
- Providers soportados
- 3 pasos visuales
- Timeline con gradiente

### FAQSection
- Acordeón colapsable
- Categorizado por tema
- Contenido SEO-friendly

### CTASection
- CTA final prominente
- Trust indicators
- Gradiente de fondo

---

## 📱 Responsive Design

El diseño usa breakpoints de Tailwind:
- `sm:` 640px+
- `md:` 768px+
- `lg:` 1024px+
- `xl:` 1280px+

Navbar incluye menú mobile hamburger.

---

## 🚀 Build & Deploy

```bash
# Build
cd frontend-react
npm run build

# Deploy a nginx
cp -r dist/* ../nginx/html/
docker restart mcp-forensics-nginx
```

---

## 📝 Pendientes

- [ ] Crear favicon.svg con logo SEGRD
- [ ] Crear og-image.png (1200x630px)
- [ ] Agregar más contenido a /modules/:id
- [ ] Implementar formulario de contacto
- [ ] Agregar página de pricing
- [ ] Analytics (Plausible/GA4)

---

## 🔗 URLs

- **Landing:** http://10.10.10.2/
- **Login:** http://10.10.10.2/login
- **Dashboard:** http://10.10.10.2/dashboard

---

**Fin del documento**
