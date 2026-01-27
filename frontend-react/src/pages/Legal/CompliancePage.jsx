import { Helmet } from 'react-helmet-async';
import { Shield, FileCheck, Globe, Database, Users, Lock, CheckCircle } from 'lucide-react';
import { Navbar, Footer } from '../../components/landing';

const CompliancePage = () => {
  const frameworks = [
    {
      name: 'GDPR',
      region: 'Unión Europea',
      status: 'Compliant',
      icon: Globe,
      description: 'Cumplimiento total con el Reglamento General de Protección de Datos.',
      features: [
        'Derecho al olvido implementado',
        'Exportación de datos en formato portable',
        'Consentimiento explícito para cookies',
        'DPO designado'
      ]
    },
    {
      name: 'HIPAA',
      region: 'Estados Unidos',
      status: 'BAA Disponible',
      icon: Database,
      description: 'Controles para datos de salud con Business Associate Agreement disponible.',
      features: [
        'Encriptación de PHI',
        'Audit logs de acceso',
        'Backup y recuperación',
        'BAA bajo solicitud'
      ]
    },
    {
      name: 'SOC 2 Type II',
      region: 'Global',
      status: 'En Proceso',
      icon: Shield,
      description: 'Auditoría de seguridad, disponibilidad, integridad de procesamiento.',
      features: [
        'Controles de seguridad documentados',
        'Monitoreo continuo',
        'Gestión de incidentes',
        'Esperado Q2 2026'
      ]
    },
    {
      name: 'ISO 27001',
      region: 'Global',
      status: 'Planificado',
      icon: FileCheck,
      description: 'Sistema de Gestión de Seguridad de la Información.',
      features: [
        'SGSI en implementación',
        'Políticas de seguridad formalizadas',
        'Gestión de riesgos',
        'Esperado Q4 2026'
      ]
    }
  ];

  const getStatusColor = (status) => {
    if (status.includes('Compliant') || status.includes('Disponible')) {
      return 'bg-green-500/10 text-green-400 border-green-500/30';
    } else if (status.includes('Proceso')) {
      return 'bg-yellow-500/10 text-yellow-400 border-yellow-500/30';
    }
    return 'bg-gray-500/10 text-gray-400 border-gray-500/30';
  };

  return (
    <>
      <Helmet>
        <title>Compliance - SEGRD</title>
        <meta name="description" content="Cumplimiento normativo de SEGRD. GDPR, HIPAA, SOC 2, ISO 27001 y más." />
      </Helmet>

      <div className="min-h-screen bg-gray-900">
        <Navbar />
        
        {/* Hero */}
        <section className="pt-32 pb-16 px-4">
          <div className="max-w-4xl mx-auto text-center">
            <div className="w-20 h-20 bg-cyan-500/10 rounded-2xl flex items-center justify-center mx-auto mb-8">
              <FileCheck className="w-10 h-10 text-cyan-400" />
            </div>
            <h1 className="text-4xl md:text-5xl font-bold text-white mb-6">
              Compliance
            </h1>
            <p className="text-xl text-gray-400 max-w-3xl mx-auto">
              SEGRD está diseñado para cumplir con los marcos regulatorios más exigentes, 
              permitiéndote operar con confianza en industrias reguladas.
            </p>
          </div>
        </section>

        {/* Frameworks */}
        <section className="py-16 px-4">
          <div className="max-w-6xl mx-auto">
            <div className="grid md:grid-cols-2 gap-8">
              {frameworks.map((framework) => {
                const Icon = framework.icon;
                return (
                  <div key={framework.name} className="bg-gray-800/50 border border-gray-700 rounded-xl p-8">
                    <div className="flex items-start justify-between mb-4">
                      <div className="flex items-center gap-4">
                        <div className="w-12 h-12 bg-cyan-500/10 rounded-xl flex items-center justify-center">
                          <Icon className="w-6 h-6 text-cyan-400" />
                        </div>
                        <div>
                          <h3 className="text-xl font-bold text-white">{framework.name}</h3>
                          <p className="text-gray-500 text-sm">{framework.region}</p>
                        </div>
                      </div>
                      <span className={`px-3 py-1 rounded-full text-xs font-medium border ${getStatusColor(framework.status)}`}>
                        {framework.status}
                      </span>
                    </div>
                    
                    <p className="text-gray-400 mb-6">{framework.description}</p>
                    
                    <ul className="space-y-2">
                      {framework.features.map((feature, idx) => (
                        <li key={idx} className="flex items-center gap-2 text-gray-300 text-sm">
                          <CheckCircle className="w-4 h-4 text-cyan-400 flex-shrink-0" />
                          {feature}
                        </li>
                      ))}
                    </ul>
                  </div>
                );
              })}
            </div>
          </div>
        </section>

        {/* Data Residency */}
        <section className="py-16 px-4 bg-gray-800/30">
          <div className="max-w-4xl mx-auto">
            <h2 className="text-2xl font-bold text-white mb-8 text-center">
              Residencia de Datos
            </h2>
            <div className="grid md:grid-cols-3 gap-6">
              <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-6 text-center">
                <div className="text-3xl mb-3">🇺🇸</div>
                <h3 className="text-lg font-semibold text-white mb-2">US East</h3>
                <p className="text-gray-400 text-sm">Virginia (us-east-1)</p>
                <span className="inline-block mt-3 px-3 py-1 bg-green-500/10 text-green-400 rounded-full text-xs">Disponible</span>
              </div>
              
              <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-6 text-center">
                <div className="text-3xl mb-3">🇪🇺</div>
                <h3 className="text-lg font-semibold text-white mb-2">EU West</h3>
                <p className="text-gray-400 text-sm">Frankfurt (eu-central-1)</p>
                <span className="inline-block mt-3 px-3 py-1 bg-yellow-500/10 text-yellow-400 rounded-full text-xs">Q2 2026</span>
              </div>
              
              <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-6 text-center">
                <div className="text-3xl mb-3">🏢</div>
                <h3 className="text-lg font-semibold text-white mb-2">On-Premise</h3>
                <p className="text-gray-400 text-sm">Tu infraestructura</p>
                <span className="inline-block mt-3 px-3 py-1 bg-green-500/10 text-green-400 rounded-full text-xs">Enterprise</span>
              </div>
            </div>
          </div>
        </section>

        {/* CTA */}
        <section className="py-16 px-4">
          <div className="max-w-3xl mx-auto text-center">
            <h2 className="text-2xl font-bold text-white mb-4">¿Necesitas más información?</h2>
            <p className="text-gray-400 mb-8">
              Contáctanos para obtener documentación detallada de compliance, 
              cuestionarios de seguridad completados, o para discutir requisitos específicos.
            </p>
            <div className="flex flex-wrap justify-center gap-4">
              <a
                href="/contact"
                className="inline-flex items-center gap-2 bg-gradient-to-r from-cyan-500 to-blue-600 text-white px-6 py-3 rounded-lg font-medium hover:shadow-lg hover:shadow-cyan-500/25 transition-all"
              >
                Contactar al Equipo
              </a>
              <a
                href="/security"
                className="inline-flex items-center gap-2 border border-gray-600 text-white px-6 py-3 rounded-lg font-medium hover:bg-gray-800 transition"
              >
                Ver Seguridad
              </a>
            </div>
          </div>
        </section>

        <Footer />
      </div>
    </>
  );
};

export default CompliancePage;
