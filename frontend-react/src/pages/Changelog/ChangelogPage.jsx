import { Helmet } from 'react-helmet-async';
import { Zap, Shield, Wrench, Bug, Star } from 'lucide-react';
import { Navbar, Footer } from '../../components/landing';

const ChangelogPage = () => {
  const releases = [
    {
      version: '4.6.0',
      date: '2026-01-15',
      type: 'major',
      highlights: [
        { icon: Star, text: 'Sistema de registro y pricing con Stripe' },
        { icon: Star, text: 'Landing page multilingüe (EN/ES)' },
        { icon: Star, text: 'Global Admin Dashboard' },
        { icon: Shield, text: 'Autenticación multi-tenant mejorada' }
      ],
      changes: [
        'Nuevo flujo de registro con selección de planes',
        'Página de pricing integrada',
        'Panel de administración global para gestión de usuarios y tenants',
        'Soporte completo para i18n (internacionalización)',
        'Mejoras en el sistema de roles RBAC'
      ]
    },
    {
      version: '4.5.0',
      date: '2025-12-01',
      type: 'major',
      highlights: [
        { icon: Star, text: 'Integración Monkey365 para M365 Cloud Security' },
        { icon: Shield, text: 'AuthContext con RBAC granular' },
        { icon: Zap, text: 'Security Checklist Form' }
      ],
      changes: [
        'Nuevo módulo M365 Cloud Security con Monkey365',
        'Sistema de autenticación refactorizado con Context API',
        'Formulario de autoevaluación de seguridad',
        'Mejoras en la gestión de sesiones',
        'Correcciones de seguridad críticas'
      ]
    },
    {
      version: '4.4.1',
      date: '2025-11-15',
      type: 'patch',
      highlights: [
        { icon: Bug, text: 'Correcciones de estabilidad' },
        { icon: Wrench, text: 'Optimizaciones de rendimiento' }
      ],
      changes: [
        'Fix: WebSocket reconnection issues',
        'Fix: Memory leak in graph visualization',
        'Optimización de queries en dashboard',
        'Mejoras en manejo de errores de API'
      ]
    },
    {
      version: '4.4.0',
      date: '2025-11-01',
      type: 'major',
      highlights: [
        { icon: Star, text: 'Case Context Provider' },
        { icon: Zap, text: 'Streaming logs en tiempo real' },
        { icon: Shield, text: 'Evidence management mejorado' }
      ],
      changes: [
        'Nuevo sistema de contexto para casos activos',
        'Logs en tiempo real via WebSocket',
        'Gestión de evidencia con cadena de custodia',
        'Timeline forense mejorado',
        'Nuevas integraciones de threat intelligence'
      ]
    },
    {
      version: '4.3.0',
      date: '2025-10-01',
      type: 'major',
      highlights: [
        { icon: Star, text: 'LLM Studio - BYO-LLM' },
        { icon: Zap, text: 'Threat Hunting interface' },
        { icon: Wrench, text: 'Maintenance Panel' }
      ],
      changes: [
        'LLM Studio para configurar proveedores de IA',
        'Soporte para OpenAI, Claude, Ollama, Azure OpenAI',
        'Nueva interfaz de Threat Hunting',
        'Panel de mantenimiento para administradores',
        'Generador de reportes mejorado'
      ]
    }
  ];

  const getTypeColor = (type) => {
    switch (type) {
      case 'major': return 'bg-cyan-500';
      case 'minor': return 'bg-blue-500';
      case 'patch': return 'bg-gray-500';
      default: return 'bg-gray-500';
    }
  };

  return (
    <>
      <Helmet>
        <title>Changelog - SEGRD</title>
        <meta name="description" content="Historial de cambios y actualizaciones de SEGRD. Nuevas funcionalidades, mejoras y correcciones." />
      </Helmet>

      <div className="min-h-screen bg-gray-900">
        <Navbar />
        
        {/* Hero */}
        <section className="pt-32 pb-16 px-4">
          <div className="max-w-4xl mx-auto text-center">
            <h1 className="text-4xl md:text-5xl font-bold text-white mb-6">
              Changelog
            </h1>
            <p className="text-xl text-gray-400">
              Historial de actualizaciones y nuevas funcionalidades
            </p>
          </div>
        </section>

        {/* Releases */}
        <section className="py-8 px-4">
          <div className="max-w-4xl mx-auto">
            <div className="relative">
              {/* Timeline line */}
              <div className="absolute left-8 top-0 bottom-0 w-0.5 bg-gray-700"></div>
              
              <div className="space-y-12">
                {releases.map((release, idx) => (
                  <div key={release.version} className="relative pl-20">
                    {/* Version badge */}
                    <div className="absolute left-0 w-16 h-16 bg-gray-800 border-4 border-gray-900 rounded-full flex items-center justify-center">
                      <span className={`w-3 h-3 rounded-full ${getTypeColor(release.type)}`}></span>
                    </div>

                    <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-6">
                      <div className="flex flex-wrap items-center gap-4 mb-4">
                        <h2 className="text-2xl font-bold text-white">v{release.version}</h2>
                        <span className={`px-3 py-1 rounded-full text-xs font-medium ${getTypeColor(release.type)} text-white`}>
                          {release.type}
                        </span>
                        <span className="text-gray-500 text-sm">{release.date}</span>
                      </div>

                      {/* Highlights */}
                      <div className="flex flex-wrap gap-3 mb-6">
                        {release.highlights.map((highlight, i) => {
                          const Icon = highlight.icon;
                          return (
                            <div key={i} className="flex items-center gap-2 bg-gray-900/50 px-3 py-1.5 rounded-lg">
                              <Icon className="w-4 h-4 text-cyan-400" />
                              <span className="text-gray-300 text-sm">{highlight.text}</span>
                            </div>
                          );
                        })}
                      </div>

                      {/* Changes */}
                      <ul className="space-y-2">
                        {release.changes.map((change, i) => (
                          <li key={i} className="flex items-start gap-2 text-gray-400">
                            <span className="w-1.5 h-1.5 bg-cyan-500 rounded-full mt-2 flex-shrink-0"></span>
                            {change}
                          </li>
                        ))}
                      </ul>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>

        <Footer />
      </div>
    </>
  );
};

export default ChangelogPage;
