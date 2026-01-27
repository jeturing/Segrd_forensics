import { Helmet } from 'react-helmet-async';
import { Shield, Lock, Eye, Server, Key, FileCheck, AlertTriangle, CheckCircle } from 'lucide-react';
import { Navbar, Footer } from '../../components/landing';

const SecurityPage = () => {
  const securityFeatures = [
    {
      icon: Lock,
      title: 'Encriptación End-to-End',
      description: 'TLS 1.3 en tránsito, AES-256 en reposo. Todos los datos sensibles están encriptados.'
    },
    {
      icon: Server,
      title: 'Aislamiento Multi-Tenant',
      description: 'Separación completa entre organizaciones. Los datos de un tenant nunca son accesibles por otro.'
    },
    {
      icon: Key,
      title: 'BYO-LLM (Bring Your Own LLM)',
      description: 'Tus datos nunca salen de tu infraestructura. Usa tu propio proveedor de IA.'
    },
    {
      icon: Eye,
      title: 'Auditoría Completa',
      description: 'Logs de todas las acciones con timestamp, usuario y contexto. Chain of custody inmutable.'
    },
    {
      icon: FileCheck,
      title: 'RBAC Granular',
      description: 'Control de acceso basado en roles con permisos a nivel de recurso y acción.'
    },
    {
      icon: Shield,
      title: 'Pentesting Regular',
      description: 'Auditorías de seguridad internas y externas realizadas trimestralmente.'
    }
  ];

  const certifications = [
    { name: 'SOC 2 Type II', status: 'En Proceso', expected: 'Q2 2026' },
    { name: 'ISO 27001', status: 'Planificado', expected: 'Q4 2026' },
    { name: 'HIPAA', status: 'Disponible', expected: 'Con BAA' },
    { name: 'GDPR', status: 'Compliant', expected: 'Activo' }
  ];

  return (
    <>
      <Helmet>
        <title>Seguridad - SEGRD</title>
        <meta name="description" content="Prácticas de seguridad de SEGRD. Encriptación, aislamiento multi-tenant, BYO-LLM y certificaciones." />
      </Helmet>

      <div className="min-h-screen bg-gray-900">
        <Navbar />
        
        {/* Hero */}
        <section className="pt-32 pb-16 px-4">
          <div className="max-w-4xl mx-auto text-center">
            <div className="w-20 h-20 bg-cyan-500/10 rounded-2xl flex items-center justify-center mx-auto mb-8">
              <Shield className="w-10 h-10 text-cyan-400" />
            </div>
            <h1 className="text-4xl md:text-5xl font-bold text-white mb-6">
              Seguridad en SEGRD
            </h1>
            <p className="text-xl text-gray-400">
              La seguridad no es una característica — es la base de todo lo que hacemos.
            </p>
          </div>
        </section>

        {/* Security Features */}
        <section className="py-16 px-4">
          <div className="max-w-6xl mx-auto">
            <h2 className="text-2xl font-bold text-white mb-12 text-center">
              Características de Seguridad
            </h2>
            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
              {securityFeatures.map((feature) => {
                const Icon = feature.icon;
                return (
                  <div key={feature.title} className="bg-gray-800/50 border border-gray-700 rounded-xl p-6">
                    <div className="w-12 h-12 bg-cyan-500/10 rounded-xl flex items-center justify-center mb-4">
                      <Icon className="w-6 h-6 text-cyan-400" />
                    </div>
                    <h3 className="text-lg font-semibold text-white mb-2">{feature.title}</h3>
                    <p className="text-gray-400">{feature.description}</p>
                  </div>
                );
              })}
            </div>
          </div>
        </section>

        {/* Certifications */}
        <section className="py-16 px-4 bg-gray-800/30">
          <div className="max-w-4xl mx-auto">
            <h2 className="text-2xl font-bold text-white mb-8 text-center">
              Certificaciones & Compliance
            </h2>
            <div className="grid md:grid-cols-2 gap-6">
              {certifications.map((cert) => (
                <div key={cert.name} className="bg-gray-800/50 border border-gray-700 rounded-xl p-6 flex items-center gap-4">
                  {cert.status === 'Compliant' || cert.status === 'Disponible' ? (
                    <CheckCircle className="w-8 h-8 text-green-500 flex-shrink-0" />
                  ) : (
                    <AlertTriangle className="w-8 h-8 text-yellow-500 flex-shrink-0" />
                  )}
                  <div>
                    <h3 className="text-lg font-semibold text-white">{cert.name}</h3>
                    <p className="text-gray-400 text-sm">
                      {cert.status} — {cert.expected}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Responsible Disclosure */}
        <section className="py-16 px-4">
          <div className="max-w-3xl mx-auto">
            <div className="bg-gradient-to-br from-cyan-500/10 to-blue-600/10 border border-cyan-500/20 rounded-xl p-8">
              <h2 className="text-2xl font-bold text-white mb-4">
                🐛 Divulgación Responsable
              </h2>
              <p className="text-gray-300 mb-6">
                ¿Encontraste una vulnerabilidad? Valoramos la seguridad de nuestra comunidad. 
                Por favor repórtala de manera responsable.
              </p>
              <p className="text-gray-300 mb-4">
                <strong>Contacto:</strong>{' '}
                <a href="mailto:security@jeturing.com" className="text-cyan-400 hover:underline">
                  security@jeturing.com
                </a>
              </p>
              <p className="text-gray-400 text-sm">
                Usamos PGP para comunicaciones sensibles. Clave pública disponible bajo petición.
              </p>
            </div>
          </div>
        </section>

        <Footer />
      </div>
    </>
  );
};

export default SecurityPage;
