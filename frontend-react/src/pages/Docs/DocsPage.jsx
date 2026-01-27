import { Helmet } from 'react-helmet-async';
import { Link } from 'react-router-dom';
import { Book, FileText, Code, Zap, Shield, HelpCircle, ExternalLink } from 'lucide-react';
import { Navbar, Footer } from '../../components/landing';

const DocsPage = () => {
  const docSections = [
    {
      icon: Zap,
      title: 'Inicio Rápido',
      description: 'Comienza con SEGRD en menos de 5 minutos',
      links: [
        { label: 'Instalación', href: '#installation' },
        { label: 'Primeros Pasos', href: '#getting-started' },
        { label: 'Configuración Inicial', href: '#initial-config' }
      ]
    },
    {
      icon: Book,
      title: 'Guías',
      description: 'Tutoriales paso a paso para cada módulo',
      links: [
        { label: 'Guía FOREN (Forense)', href: '#foren-guide' },
        { label: 'Guía AXION (IR)', href: '#axion-guide' },
        { label: 'Guía VIGIL (Monitoreo)', href: '#vigil-guide' },
        { label: 'Guía ORBIA (Automatización)', href: '#orbia-guide' }
      ]
    },
    {
      icon: Code,
      title: 'API Reference',
      description: 'Documentación técnica de la API REST',
      links: [
        { label: 'Autenticación', href: '#api-auth' },
        { label: 'Endpoints', href: '#api-endpoints' },
        { label: 'Webhooks', href: '#api-webhooks' },
        { label: 'Rate Limits', href: '#api-rate-limits' }
      ]
    },
    {
      icon: Shield,
      title: 'Seguridad',
      description: 'Configuración de seguridad y compliance',
      links: [
        { label: 'BYO-LLM Setup', href: '#byollm-setup' },
        { label: 'Multi-Tenant', href: '#multi-tenant' },
        { label: 'RBAC', href: '#rbac' },
        { label: 'Audit Logs', href: '#audit-logs' }
      ]
    }
  ];

  return (
    <>
      <Helmet>
        <title>Documentación - SEGRD</title>
        <meta name="description" content="Documentación técnica de SEGRD. Guías, tutoriales y referencia de API para la plataforma de seguridad y forense." />
      </Helmet>

      <div className="min-h-screen bg-gray-900">
        <Navbar />
        
        {/* Hero */}
        <section className="pt-32 pb-16 px-4">
          <div className="max-w-7xl mx-auto text-center">
            <h1 className="text-4xl md:text-5xl font-bold text-white mb-6">
              Documentación
            </h1>
            <p className="text-xl text-gray-400 max-w-3xl mx-auto mb-8">
              Todo lo que necesitas para implementar y aprovechar al máximo SEGRD.
            </p>
            
            {/* Search */}
            <div className="max-w-2xl mx-auto">
              <div className="relative">
                <input
                  type="text"
                  placeholder="Buscar en la documentación..."
                  className="w-full bg-gray-800 border border-gray-700 rounded-xl px-6 py-4 pl-12 text-white focus:outline-none focus:border-cyan-500 transition"
                />
                <svg className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
              </div>
            </div>
          </div>
        </section>

        {/* Doc Sections */}
        <section className="py-16 px-4">
          <div className="max-w-7xl mx-auto">
            <div className="grid md:grid-cols-2 gap-8">
              {docSections.map((section) => {
                const Icon = section.icon;
                return (
                  <div key={section.title} className="bg-gray-800/50 border border-gray-700 rounded-xl p-8 hover:border-gray-600 transition">
                    <div className="flex items-center gap-4 mb-4">
                      <div className="w-12 h-12 bg-cyan-500/10 rounded-xl flex items-center justify-center">
                        <Icon className="w-6 h-6 text-cyan-400" />
                      </div>
                      <div>
                        <h2 className="text-xl font-bold text-white">{section.title}</h2>
                        <p className="text-gray-400 text-sm">{section.description}</p>
                      </div>
                    </div>
                    <ul className="space-y-2">
                      {section.links.map((link) => (
                        <li key={link.label}>
                          <a
                            href={link.href}
                            className="flex items-center gap-2 text-gray-300 hover:text-cyan-400 transition py-1"
                          >
                            <FileText className="w-4 h-4" />
                            {link.label}
                          </a>
                        </li>
                      ))}
                    </ul>
                  </div>
                );
              })}
            </div>
          </div>
        </section>

        {/* Quick Links */}
        <section className="py-16 px-4 bg-gray-800/30">
          <div className="max-w-7xl mx-auto">
            <h2 className="text-2xl font-bold text-white mb-8 text-center">Enlaces Rápidos</h2>
            <div className="grid md:grid-cols-3 gap-6">
              <a
                href="/changelog"
                className="flex items-center gap-4 bg-gray-800/50 border border-gray-700 rounded-xl p-6 hover:border-cyan-500/50 transition group"
              >
                <Zap className="w-8 h-8 text-cyan-400" />
                <div>
                  <h3 className="text-white font-semibold group-hover:text-cyan-400 transition">Changelog</h3>
                  <p className="text-gray-400 text-sm">Últimas actualizaciones</p>
                </div>
              </a>

              <a
                href="https://github.com/jeturing/segrd"
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-4 bg-gray-800/50 border border-gray-700 rounded-xl p-6 hover:border-cyan-500/50 transition group"
              >
                <Code className="w-8 h-8 text-cyan-400" />
                <div className="flex-1">
                  <h3 className="text-white font-semibold group-hover:text-cyan-400 transition flex items-center gap-2">
                    GitHub <ExternalLink className="w-4 h-4" />
                  </h3>
                  <p className="text-gray-400 text-sm">Código y ejemplos</p>
                </div>
              </a>

              <Link
                to="/contact"
                className="flex items-center gap-4 bg-gray-800/50 border border-gray-700 rounded-xl p-6 hover:border-cyan-500/50 transition group"
              >
                <HelpCircle className="w-8 h-8 text-cyan-400" />
                <div>
                  <h3 className="text-white font-semibold group-hover:text-cyan-400 transition">Soporte</h3>
                  <p className="text-gray-400 text-sm">¿Necesitas ayuda?</p>
                </div>
              </Link>
            </div>
          </div>
        </section>

        {/* Coming Soon Notice */}
        <section className="py-16 px-4">
          <div className="max-w-3xl mx-auto text-center">
            <div className="bg-gradient-to-br from-cyan-500/10 to-blue-600/10 border border-cyan-500/20 rounded-xl p-8">
              <h3 className="text-xl font-bold text-white mb-4">📚 Documentación en Desarrollo</h3>
              <p className="text-gray-400 mb-6">
                Estamos trabajando activamente en expandir nuestra documentación. 
                Mientras tanto, no dudes en contactarnos para cualquier consulta.
              </p>
              <Link
                to="/contact"
                className="inline-flex items-center gap-2 bg-gradient-to-r from-cyan-500 to-blue-600 text-white px-6 py-3 rounded-lg font-medium hover:shadow-lg hover:shadow-cyan-500/25 transition-all"
              >
                Contactar Soporte
              </Link>
            </div>
          </div>
        </section>

        <Footer />
      </div>
    </>
  );
};

export default DocsPage;
