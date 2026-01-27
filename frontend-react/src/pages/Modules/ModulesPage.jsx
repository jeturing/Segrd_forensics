import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';
import { Search, Shield, Eye, Workflow, Check } from 'lucide-react';
import { Navbar, Footer } from '../../components/landing';

const ModulesPage = () => {
  const { t } = useTranslation(['modules', 'common']);

  const modules = [
    {
      id: 'foren',
      name: 'FOREN',
      icon: Search,
      color: 'from-blue-500 to-blue-700',
      title: 'Análisis Forense Digital',
      description: 'Recolección y análisis de evidencia de grado legal. Plataforma integral de forense digital para investigaciones, soporte en litigios y testimonios periciales.',
      tools: ['Sparrow', 'Hawk', 'YARA', 'Volatility', 'Loki'],
      features: [
        'Cadena de custodia certificada',
        'Reportes periciales automáticos',
        'M365 forensics completo',
        'Análisis de memoria RAM',
        'Recuperación de evidencia eliminada',
        'Timeline forense integrado'
      ],
      useCases: [
        'Investigaciones internas de fraude',
        'Soporte en litigios civiles y penales',
        'Auditoría forense post-incidente',
        'eDiscovery y preservación de evidencia'
      ]
    },
    {
      id: 'axion',
      name: 'AXION',
      icon: Shield,
      color: 'from-red-500 to-red-700',
      title: 'Respuesta a Incidentes',
      description: 'Contención y remediación rápida. Respuesta a incidentes de extremo a extremo desde detección hasta recuperación.',
      tools: ['OSQuery', 'Velociraptor', 'FastIR', 'TheHive'],
      features: [
        'Triaje automatizado de alertas',
        'Contención remota de endpoints',
        'Timeline analysis en tiempo real',
        'Playbooks de respuesta automáticos',
        'Integración con SIEM/SOAR',
        'Reporting ejecutivo instantáneo'
      ],
      useCases: [
        'Respuesta a ransomware',
        'Contención de brechas de datos',
        'Investigación de compromisos de red',
        'Remediación de malware avanzado'
      ]
    },
    {
      id: 'vigil',
      name: 'VIGIL',
      icon: Eye,
      color: 'from-green-500 to-green-700',
      title: 'Monitoreo de Amenazas',
      description: 'Visibilidad continua de tu entorno. Detección y monitoreo de amenazas 24/7 en endpoints, nube y red.',
      tools: ['Sigma', 'YARA', 'MISP', 'Shodan'],
      features: [
        'Threat Intelligence integrada',
        'IOC matching en tiempo real',
        'Alertas personalizables',
        'Correlación multi-fuente',
        'Dashboard de amenazas',
        'Integración con feeds externos'
      ],
      useCases: [
        'Monitoreo continuo de seguridad',
        'Threat hunting proactivo',
        'Detección de amenazas emergentes',
        'Vigilancia de superficie de ataque'
      ]
    },
    {
      id: 'orbia',
      name: 'ORBIA',
      icon: Workflow,
      color: 'from-purple-500 to-purple-700',
      title: 'Orquestación y Automatización',
      description: 'Orquestar, automatizar, responder. Conecta tus herramientas de seguridad y automatiza tareas repetitivas.',
      tools: ['MISP', 'TheHive', 'Cortex', 'Playbooks'],
      features: [
        'SOAR integrado',
        'Playbooks visuales drag-and-drop',
        'Integraciones API nativas',
        'Automatización de workflows',
        'Métricas y KPIs de operación',
        'Notificaciones multi-canal'
      ],
      useCases: [
        'Automatización de triaje de alertas',
        'Enriquecimiento automático de IOCs',
        'Respuesta automatizada a incidentes',
        'Integración de herramientas existentes'
      ]
    }
  ];

  return (
    <>
      <Helmet>
        <title>Módulos de Seguridad - SEGRD</title>
        <meta name="description" content="Explora los módulos de seguridad de SEGRD: FOREN (Forense), AXION (IR), VIGIL (Monitoreo), ORBIA (Automatización)" />
      </Helmet>

      <div className="min-h-screen bg-gray-900">
        <Navbar />
        
        {/* Hero */}
        <section className="pt-32 pb-16 px-4">
          <div className="max-w-7xl mx-auto text-center">
            <h1 className="text-4xl md:text-5xl font-bold text-white mb-6">
              Módulos de Seguridad
            </h1>
            <p className="text-xl text-gray-400 max-w-3xl mx-auto">
              Plataforma modular diseñada para adaptarse a tus necesidades. 
              Activa solo los módulos que necesitas, escala cuando crezcas.
            </p>
          </div>
        </section>

        {/* Modules Detail */}
        <section className="py-16 px-4">
          <div className="max-w-7xl mx-auto space-y-24">
            {modules.map((module, idx) => {
              const Icon = module.icon;
              const isEven = idx % 2 === 0;
              
              return (
                <div 
                  key={module.id}
                  id={module.id}
                  className={`grid md:grid-cols-2 gap-12 items-center ${isEven ? '' : 'md:flex-row-reverse'}`}
                >
                  <div className={isEven ? '' : 'md:order-2'}>
                    <div className="flex items-center gap-4 mb-6">
                      <div className={`w-16 h-16 bg-gradient-to-br ${module.color} rounded-2xl flex items-center justify-center`}>
                        <Icon className="w-8 h-8 text-white" />
                      </div>
                      <div>
                        <span className="text-sm font-bold text-gray-500 uppercase">{module.name}</span>
                        <h2 className="text-3xl font-bold text-white">{module.title}</h2>
                      </div>
                    </div>
                    
                    <p className="text-lg text-gray-400 mb-8">
                      {module.description}
                    </p>

                    {/* Tools */}
                    <div className="mb-8">
                      <h4 className="text-sm font-semibold text-gray-500 uppercase mb-3">Herramientas Incluidas</h4>
                      <div className="flex flex-wrap gap-2">
                        {module.tools.map((tool) => (
                          <span key={tool} className="px-3 py-1 bg-gray-800 text-gray-300 rounded-lg text-sm">
                            {tool}
                          </span>
                        ))}
                      </div>
                    </div>

                    <Link
                      to="/contact"
                      className="inline-flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-cyan-500 to-blue-600 text-white font-medium rounded-lg hover:shadow-lg hover:shadow-cyan-500/25 transition-all"
                    >
                      Solicitar Demo
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
                      </svg>
                    </Link>
                  </div>

                  <div className={`bg-gray-800/50 border border-gray-700 rounded-2xl p-8 ${isEven ? '' : 'md:order-1'}`}>
                    <h4 className="text-lg font-semibold text-white mb-6">Características</h4>
                    <ul className="space-y-3 mb-8">
                      {module.features.map((feature) => (
                        <li key={feature} className="flex items-start gap-3 text-gray-300">
                          <Check className="w-5 h-5 text-green-500 flex-shrink-0 mt-0.5" />
                          {feature}
                        </li>
                      ))}
                    </ul>

                    <h4 className="text-lg font-semibold text-white mb-4">Casos de Uso</h4>
                    <ul className="space-y-2">
                      {module.useCases.map((useCase) => (
                        <li key={useCase} className="flex items-center gap-2 text-gray-400 text-sm">
                          <span className="w-1.5 h-1.5 bg-cyan-500 rounded-full"></span>
                          {useCase}
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              );
            })}
          </div>
        </section>

        {/* CTA */}
        <section className="py-24 px-4 bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900">
          <div className="max-w-4xl mx-auto text-center">
            <h2 className="text-3xl font-bold text-white mb-6">
              ¿Listo para empezar?
            </h2>
            <p className="text-gray-400 mb-8">
              Prueba todos los módulos gratis por 14 días. Sin tarjeta de crédito.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <Link
                to="/register"
                className="px-8 py-4 bg-gradient-to-r from-cyan-500 to-blue-600 text-white font-semibold rounded-xl hover:shadow-lg hover:shadow-cyan-500/25 transition-all"
              >
                Iniciar Prueba Gratuita
              </Link>
              <Link
                to="/pricing"
                className="px-8 py-4 border-2 border-gray-600 text-white font-semibold rounded-xl hover:border-cyan-500 hover:bg-cyan-500/10 transition-all"
              >
                Ver Precios
              </Link>
            </div>
          </div>
        </section>

        <Footer />
      </div>
    </>
  );
};

export default ModulesPage;
