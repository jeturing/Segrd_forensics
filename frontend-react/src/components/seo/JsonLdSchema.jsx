import { useTranslation } from "react-i18next";
import { Helmet } from "react-helmet-async";

const JsonLdSchema = () => {
  const { t, i18n } = useTranslation(["landing", "modules", "faq"]);
  const lang = i18n.language;

  // Organization Schema
  const organizationSchema = {
    "@context": "https://schema.org",
    "@type": "Organization",
    "name": "Jeturing Inc.",
    "alternateName": "SEGRD",
    "url": "https://segrd.com",
    "logo": "https://segrd.com/logo.png",
    "description": t("landing:hero.description"),
    "foundingDate": "2024",
    "foundingLocation": {
      "@type": "Place",
      "address": {
        "@type": "PostalAddress",
        "addressCountry": "US",
        "addressRegion": "Delaware"
      }
    },
    "sameAs": [
      "https://github.com/jeturing",
      "https://linkedin.com/company/jeturing",
      "https://twitter.com/jeturing"
    ],
    "contactPoint": {
      "@type": "ContactPoint",
      "contactType": "sales",
      "email": "sales@segrd.com",
      "availableLanguage": ["English", "Spanish"]
    }
  };

  // SoftwareApplication Schema
  const softwareSchema = {
    "@context": "https://schema.org",
    "@type": "SoftwareApplication",
    "name": "SEGRD",
    "applicationCategory": "SecurityApplication",
    "operatingSystem": "Web, Linux, Windows, macOS",
    "description": t("landing:hero.description"),
    "offers": {
      "@type": "Offer",
      "price": "0",
      "priceCurrency": "USD",
      "description": "14-day free trial"
    },
    "featureList": [
      "Digital Forensics Analysis",
      "Incident Response Automation",
      "Network Traffic Analysis",
      "OSINT Intelligence Gathering",
      "SOAR Orchestration",
      "Cloud Security Posture Management",
      "MCP Integration for AI Agents",
      "BYO-LLM Support"
    ],
    "screenshot": "https://segrd.com/screenshot.png",
    "softwareVersion": "1.0",
    "author": {
      "@type": "Organization",
      "name": "Jeturing Inc."
    }
  };

  // FAQ Schema from translations - CORRECTED
  const faqItemsData = t("faq:items", { returnObjects: true }) || [];
  const faqItems = Array.isArray(faqItemsData) ? faqItemsData.map(item => ({
    "@type": "Question",
    "name": item.question,
    "acceptedAnswer": {
      "@type": "Answer",
      "text": item.answer
    }
  })) : [];

  const faqSchema = {
    "@context": "https://schema.org",
    "@type": "FAQPage",
    "mainEntity": faqItems
  };

  // WebSite Schema with SearchAction
  const websiteSchema = {
    "@context": "https://schema.org",
    "@type": "WebSite",
    "name": "SEGRD",
    "url": "https://segrd.com",
    "inLanguage": lang === "es" ? "es-ES" : "en-US",
    "potentialAction": {
      "@type": "SearchAction",
      "target": "https://segrd.com/search?q={search_term_string}",
      "query-input": "required name=search_term_string"
    }
  };

  // Product Schema for each module - CORRECTED
  const modulesData = t("modules:items", { returnObjects: true }) || [];
  const productSchemas = Array.isArray(modulesData) ? modulesData.map((mod, index) => ({
    "@context": "https://schema.org",
    "@type": "Product",
    "name": `SEGRD ${mod.name}`,
    "description": mod.description,
    "category": "Security Software",
    "brand": {
      "@type": "Brand",
      "name": "SEGRD"
    },
    "offers": {
      "@type": "Offer",
      "availability": "https://schema.org/InStock",
      "priceCurrency": "USD"
    }
  })) : [];

  return (
    <Helmet>
      <html lang={lang} />
      <title>SEGRD - Security, Forensics & Incident Response Platform | Jeturing Inc.</title>
      <meta name="description" content={t("landing:hero.description")} />
      <meta name="keywords" content="digital forensics, incident response, DFIR, SOC, SIEM, SOAR, cybersecurity, MCP, AI security, threat intelligence, OSINT, cloud security" />
      
      {/* Open Graph */}
      <meta property="og:type" content="website" />
      <meta property="og:title" content="SEGRD - Security, Forensics & Incident Response" />
      <meta property="og:description" content={t("landing:hero.description")} />
      <meta property="og:url" content="https://segrd.com" />
      <meta property="og:image" content="https://segrd.com/og-image.png" />
      <meta property="og:locale" content={lang === "es" ? "es_ES" : "en_US"} />
      
      {/* Twitter Card */}
      <meta name="twitter:card" content="summary_large_image" />
      <meta name="twitter:site" content="@jeturing" />
      <meta name="twitter:title" content="SEGRD - Security, Forensics & Incident Response" />
      <meta name="twitter:description" content={t("landing:hero.description")} />
      
      {/* JSON-LD Schemas */}
      <script type="application/ld+json">
        {JSON.stringify(organizationSchema)}
      </script>
      <script type="application/ld+json">
        {JSON.stringify(softwareSchema)}
      </script>
      <script type="application/ld+json">
        {JSON.stringify(faqSchema)}
      </script>
      <script type="application/ld+json">
        {JSON.stringify(websiteSchema)}
      </script>
      {productSchemas.map((schema, index) => (
        <script key={index} type="application/ld+json">
          {JSON.stringify(schema)}
        </script>
      ))}
    </Helmet>
  );
};

export default JsonLdSchema;
