import { Helmet } from 'react-helmet-async';
import { Navbar, Footer } from '../../components/landing';

const TermsPage = () => {
  const lastUpdated = '15 de Enero, 2026';

  return (
    <>
      <Helmet>
        <title>Términos de Servicio - SEGRD</title>
        <meta name="description" content="Términos y condiciones de uso de la plataforma SEGRD." />
      </Helmet>

      <div className="min-h-screen bg-gray-900">
        <Navbar />
        
        <div className="max-w-4xl mx-auto px-4 py-32">
          <h1 className="text-4xl font-bold text-white mb-4">Términos de Servicio</h1>
          <p className="text-gray-400 mb-12">Última actualización: {lastUpdated}</p>

          <div className="prose prose-invert prose-lg max-w-none space-y-8">
            <section>
              <h2 className="text-2xl font-bold text-white mb-4">1. Aceptación de Términos</h2>
              <p className="text-gray-300">
                Al acceder o usar los servicios de SEGRD (operados por Jeturing Inc.), 
                aceptas estar sujeto a estos Términos de Servicio. Si no estás de acuerdo 
                con alguna parte de los términos, no debes usar el servicio.
              </p>
            </section>

            <section>
              <h2 className="text-2xl font-bold text-white mb-4">2. Descripción del Servicio</h2>
              <p className="text-gray-300">
                SEGRD es una plataforma de seguridad y forense digital que proporciona:
              </p>
              <ul className="list-disc pl-6 text-gray-300 space-y-2">
                <li>Análisis forense digital (Módulo FOREN)</li>
                <li>Respuesta a incidentes automatizada (Módulo AXION)</li>
                <li>Monitoreo de seguridad continuo (Módulo VIGIL)</li>
                <li>Automatización de seguridad (Módulo ORBIA)</li>
              </ul>
            </section>

            <section>
              <h2 className="text-2xl font-bold text-white mb-4">3. Cuentas de Usuario</h2>
              <p className="text-gray-300">
                Para usar ciertos aspectos del servicio, debes crear una cuenta. Eres responsable de:
              </p>
              <ul className="list-disc pl-6 text-gray-300 space-y-2">
                <li>Mantener la confidencialidad de tu contraseña</li>
                <li>Todas las actividades bajo tu cuenta</li>
                <li>Notificar inmediatamente cualquier uso no autorizado</li>
                <li>Proporcionar información precisa y actualizada</li>
              </ul>
            </section>

            <section>
              <h2 className="text-2xl font-bold text-white mb-4">4. Uso Aceptable</h2>
              <p className="text-gray-300">Te comprometes a NO usar el servicio para:</p>
              <ul className="list-disc pl-6 text-gray-300 space-y-2">
                <li>Actividades ilegales o no autorizadas</li>
                <li>Violar derechos de propiedad intelectual</li>
                <li>Transmitir malware o código malicioso</li>
                <li>Interferir con la operación del servicio</li>
                <li>Acceder a datos de otros usuarios sin autorización</li>
                <li>Investigaciones forenses sin autorización legal apropiada</li>
              </ul>
            </section>

            <section>
              <h2 className="text-2xl font-bold text-white mb-4">5. Suscripción y Pagos</h2>
              <p className="text-gray-300">
                Ciertos servicios requieren suscripción de pago:
              </p>
              <ul className="list-disc pl-6 text-gray-300 space-y-2">
                <li>Los precios están sujetos a cambios con 30 días de aviso</li>
                <li>Las suscripciones se renuevan automáticamente</li>
                <li>Puedes cancelar en cualquier momento desde tu panel</li>
                <li>No hay reembolsos por períodos parciales</li>
              </ul>
            </section>

            <section>
              <h2 className="text-2xl font-bold text-white mb-4">6. Propiedad Intelectual</h2>
              <p className="text-gray-300">
                SEGRD y todo su contenido, características y funcionalidad son propiedad exclusiva 
                de Jeturing Inc. y están protegidos por leyes de propiedad intelectual. 
                Los datos que procesas a través del servicio permanecen siendo de tu propiedad.
              </p>
            </section>

            <section>
              <h2 className="text-2xl font-bold text-white mb-4">7. Limitación de Responsabilidad</h2>
              <p className="text-gray-300">
                En la máxima medida permitida por ley, Jeturing Inc. no será responsable por 
                daños indirectos, incidentales, especiales, consecuentes o punitivos, incluyendo 
                pérdida de beneficios, datos o uso del servicio.
              </p>
            </section>

            <section>
              <h2 className="text-2xl font-bold text-white mb-4">8. Indemnización</h2>
              <p className="text-gray-300">
                Aceptas indemnizar y mantener indemne a Jeturing Inc. contra cualquier reclamación 
                o demanda derivada de tu uso del servicio o violación de estos términos.
              </p>
            </section>

            <section>
              <h2 className="text-2xl font-bold text-white mb-4">9. Terminación</h2>
              <p className="text-gray-300">
                Podemos terminar o suspender tu acceso inmediatamente, sin aviso previo, 
                por cualquier motivo, incluyendo violación de estos Términos. 
                Tras la terminación, tu derecho de uso cesará inmediatamente.
              </p>
            </section>

            <section>
              <h2 className="text-2xl font-bold text-white mb-4">10. Ley Aplicable</h2>
              <p className="text-gray-300">
                Estos términos se rigen por las leyes del Estado de Delaware, Estados Unidos, 
                sin tener en cuenta conflictos de disposiciones legales.
              </p>
            </section>

            <section>
              <h2 className="text-2xl font-bold text-white mb-4">11. Contacto</h2>
              <p className="text-gray-300">
                Para preguntas sobre estos términos:
              </p>
              <p className="text-gray-300 mt-4">
                <strong>Jeturing Inc.</strong><br />
                Email: <a href="mailto:legal@jeturing.com" className="text-cyan-400 hover:underline">legal@jeturing.com</a><br />
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

export default TermsPage;
