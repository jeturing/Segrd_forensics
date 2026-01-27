import { Helmet } from 'react-helmet-async';
import { Navbar, Footer } from '../../components/landing';

const PrivacyPage = () => {
  const lastUpdated = '15 de Enero, 2026';

  return (
    <>
      <Helmet>
        <title>Política de Privacidad - SEGRD</title>
        <meta name="description" content="Política de privacidad de SEGRD. Información sobre cómo recopilamos, usamos y protegemos tus datos." />
      </Helmet>

      <div className="min-h-screen bg-gray-900">
        <Navbar />
        
        <div className="max-w-4xl mx-auto px-4 py-32">
          <h1 className="text-4xl font-bold text-white mb-4">Política de Privacidad</h1>
          <p className="text-gray-400 mb-12">Última actualización: {lastUpdated}</p>

          <div className="prose prose-invert prose-lg max-w-none space-y-8">
            <section>
              <h2 className="text-2xl font-bold text-white mb-4">1. Información que Recopilamos</h2>
              <p className="text-gray-300">
                En SEGRD (operado por Jeturing Inc.), recopilamos información para proporcionar mejores servicios. 
                Los tipos de información que recopilamos incluyen:
              </p>
              <ul className="list-disc pl-6 text-gray-300 space-y-2">
                <li><strong>Información de cuenta:</strong> Nombre, email, empresa, cuando te registras.</li>
                <li><strong>Información de uso:</strong> Cómo usas nuestros servicios, incluyendo logs de actividad.</li>
                <li><strong>Información técnica:</strong> IP, navegador, sistema operativo para optimizar el servicio.</li>
                <li><strong>Datos de casos:</strong> Evidencia forense y datos de investigaciones que procesas.</li>
              </ul>
            </section>

            <section>
              <h2 className="text-2xl font-bold text-white mb-4">2. Cómo Usamos la Información</h2>
              <p className="text-gray-300">Utilizamos la información para:</p>
              <ul className="list-disc pl-6 text-gray-300 space-y-2">
                <li>Proporcionar, mantener y mejorar nuestros servicios</li>
                <li>Procesar transacciones y enviar comunicaciones relacionadas</li>
                <li>Detectar, investigar y prevenir fraudes o actividades ilícitas</li>
                <li>Cumplir con obligaciones legales</li>
                <li>Personalizar tu experiencia en la plataforma</li>
              </ul>
            </section>

            <section>
              <h2 className="text-2xl font-bold text-white mb-4">3. Seguridad de Datos</h2>
              <p className="text-gray-300">
                La seguridad es fundamental en SEGRD. Implementamos:
              </p>
              <ul className="list-disc pl-6 text-gray-300 space-y-2">
                <li>Encriptación en tránsito (TLS 1.3) y en reposo (AES-256)</li>
                <li>Aislamiento multi-tenant estricto</li>
                <li>Auditorías de seguridad regulares</li>
                <li>Controles de acceso basados en roles (RBAC)</li>
                <li>BYO-LLM: Tus datos nunca salen de tu infraestructura con esta opción</li>
              </ul>
            </section>

            <section>
              <h2 className="text-2xl font-bold text-white mb-4">4. Compartición de Datos</h2>
              <p className="text-gray-300">
                No vendemos ni compartimos datos personales con terceros para fines de marketing. 
                Solo compartimos información cuando:
              </p>
              <ul className="list-disc pl-6 text-gray-300 space-y-2">
                <li>Tienes tu consentimiento explícito</li>
                <li>Es necesario para proveedores de servicios bajo contrato (procesadores de pago, etc.)</li>
                <li>Es requerido por ley o proceso legal</li>
                <li>Es necesario para proteger derechos, propiedad o seguridad</li>
              </ul>
            </section>

            <section>
              <h2 className="text-2xl font-bold text-white mb-4">5. Tus Derechos</h2>
              <p className="text-gray-300">Tienes derecho a:</p>
              <ul className="list-disc pl-6 text-gray-300 space-y-2">
                <li>Acceder a tu información personal</li>
                <li>Corregir información inexacta</li>
                <li>Solicitar eliminación de datos (sujeto a obligaciones legales)</li>
                <li>Exportar tus datos en formato portable</li>
                <li>Oponerte al procesamiento de datos</li>
              </ul>
            </section>

            <section>
              <h2 className="text-2xl font-bold text-white mb-4">6. Retención de Datos</h2>
              <p className="text-gray-300">
                Retenemos datos personales mientras tu cuenta esté activa o según sea necesario para 
                proporcionar servicios. Los datos de casos forenses siguen las políticas de retención 
                configuradas por tu organización y requisitos legales aplicables.
              </p>
            </section>

            <section>
              <h2 className="text-2xl font-bold text-white mb-4">7. Cookies</h2>
              <p className="text-gray-300">
                Usamos cookies esenciales para la funcionalidad del servicio y cookies analíticas 
                para mejorar la experiencia. Puedes controlar las preferencias de cookies desde tu navegador.
              </p>
            </section>

            <section>
              <h2 className="text-2xl font-bold text-white mb-4">8. Contacto</h2>
              <p className="text-gray-300">
                Para preguntas sobre esta política o tus derechos de privacidad:
              </p>
              <p className="text-gray-300 mt-4">
                <strong>Jeturing Inc.</strong><br />
                Email: <a href="mailto:privacy@jeturing.com" className="text-cyan-400 hover:underline">privacy@jeturing.com</a><br />
                Web: <a href="/contact" className="text-cyan-400 hover:underline">segrd.com/contact</a>
              </p>
            </section>
          </div>
        </div>

        <Footer />
      </div>
    </>
  );
};

export default PrivacyPage;
