import { Helmet } from 'react-helmet-async';
import { Navbar, Footer } from '../../components/landing';

const TermsPage = () => {
  const lastUpdated = '1 de Enero, 2025';

  return (
    <>
      <Helmet>
        <title>Términos de Servicio - Jeturing | SEGRD™</title>
        <meta name="description" content="Términos y condiciones de los servicios de ciberseguridad gestionados de Jeturing." />
      </Helmet>

      <div className="min-h-screen bg-gray-900">
        <Navbar />
        
        <div className="max-w-4xl mx-auto px-4 py-32">
          <h1 className="text-4xl font-bold text-white mb-4">Términos de Servicio</h1>
          <p className="text-gray-400 mb-12">Última actualización: {lastUpdated}</p>

          <div className="prose prose-invert prose-lg max-w-none space-y-8">
            <section>
              <h2 className="text-2xl font-bold text-white mb-4">1. Alcance de Servicios</h2>
              <p className="text-gray-300">
                Jeturing Inc. provee servicios de ciberseguridad gestionados utilizando la plataforma SEGRD™. 
                Los servicios incluyen monitoreo de seguridad 24x7, respuesta a incidentes, análisis forense digital, 
                y consultoría estratégica (v-CISO) según el Bundle contratado.
              </p>
              <p className="text-gray-300 mt-4">
                El cliente reconoce que estos servicios son <strong>servicios gestionados</strong> (MSP) donde 
                Jeturing opera herramientas en nombre del cliente, no una licencia de software.
              </p>
            </section>

            <section>
              <h2 className="text-2xl font-bold text-white mb-4">2. Facturación y Condiciones de Pago</h2>
              <p className="text-gray-300">
                Los servicios se facturan mensualmente por adelantado:
              </p>
              <ul className="list-disc pl-6 text-gray-300 space-y-2 mt-4">
                <li><strong>Bundle I - Protección Esencial:</strong> USD $2,500/mes</li>
                <li><strong>Bundle II - Resiliencia Profesional:</strong> USD $4,500/mes</li>
                <li><strong>Bundle III - Blindaje Misión Crítica:</strong> USD $6,500/mes</li>
                <li><strong>v-CISO Lite:</strong> USD $1,500/mes (adicional)</li>
                <li><strong>v-CISO Estándar:</strong> USD $3,500/mes (adicional)</li>
              </ul>
              <p className="text-gray-300 mt-4">
                Términos de pago: <strong>Net 15</strong> desde la fecha de factura. 
                Métodos aceptados: Stripe (ACH/tarjeta) o transferencia bancaria. 
                Facturas vencidas generan interés del 1.5% mensual.
              </p>
            </section>

            <section>
              <h2 className="text-2xl font-bold text-white mb-4">3. Vigencia, Renovación y Terminación</h2>
              <p className="text-gray-300">
                <strong>Vigencia inicial:</strong> 12 meses desde la fecha de firma del SOW (Statement of Work).
              </p>
              <p className="text-gray-300 mt-4">
                <strong>Renovación automática:</strong> El contrato se renueva automáticamente por períodos de 12 meses, 
                salvo que cualquiera de las partes notifique por escrito su intención de no renovar con al menos 
                <strong> 30 días de anticipación</strong> antes del vencimiento.
              </p>
              <p className="text-gray-300 mt-4">
                <strong>Terminación anticipada:</strong> El cliente puede terminar el servicio antes del vencimiento, 
                pero no hay reembolsos pro-rata por los meses pagados por adelantado. 
                Jeturing puede suspender servicios por falta de pago después de 15 días de mora.
              </p>
            </section>

            <section>
              <h2 className="text-2xl font-bold text-white mb-4">4. SLA y Garantías de Disponibilidad</h2>
              <p className="text-gray-300">
                Jeturing garantiza los siguientes niveles de servicio según el bundle contratado:
              </p>
              <ul className="list-disc pl-6 text-gray-300 space-y-2 mt-4">
                <li><strong>Bundle I:</strong> Disponibilidad 99% (8x5 soporte)</li>
                <li><strong>Bundle II:</strong> Disponibilidad 99.5% (24x7 soporte)</li>
                <li><strong>Bundle III:</strong> Disponibilidad 99.9% (24x7 soporte premium)</li>
              </ul>
              <p className="text-gray-300 mt-4">
                Si no cumplimos el SLA en un mes, el cliente recibe un <strong>crédito del 10%</strong> sobre 
                la factura mensual (único remedio disponible). No aplica crédito por interrupciones causadas 
                por mantenimiento programado o factores fuera del control de Jeturing.
              </p>
            </section>

            <section>
              <h2 className="text-2xl font-bold text-white mb-4">5. Limitación de Responsabilidad</h2>
              <p className="text-gray-300">
                <strong>Límite de responsabilidad total:</strong> Jeturing Inc. NO será responsable por daños 
                indirectos, consecuentes, incidentales, especiales, punitivos o pérdida de beneficios, 
                incluso si fue advertida de su posibilidad.
              </p>
              <p className="text-gray-300 mt-4">
                La responsabilidad agregada máxima de Jeturing por cualquier reclamación bajo este contrato 
                está <strong>limitada al monto total pagado por el cliente a Jeturing en los últimos 12 meses</strong>.
              </p>
              <p className="text-gray-300 mt-4 font-semibold">
                Jeturing NO garantiza prevención absoluta de incidentes de seguridad, solo capacidad de 
                detección y respuesta según los SLA acordados.
              </p>
            </section>

            <section>
              <h2 className="text-2xl font-bold text-white mb-4">6. Propiedad Intelectual</h2>
              <p className="text-gray-300">
                <strong>Tecnología SEGRD™:</strong> La plataforma SEGRD™, sus módulos, código fuente, 
                metodologías y documentación son propiedad exclusiva de Jeturing Inc. El cliente NO adquiere 
                derechos de propiedad intelectual sobre la plataforma, solo un derecho de uso durante la vigencia del contrato.
              </p>
              <p className="text-gray-300 mt-4">
                <strong>Datos del Cliente:</strong> Todos los datos, logs, evidencia digital y reportes generados 
                para el cliente son propiedad del cliente. Jeturing puede retener copias por razones de auditoría 
                o cumplimiento normativo durante 7 años.
              </p>
              <p className="text-gray-300 mt-4">
                <strong>Código desarrollado a medida:</strong> Cualquier desarrollo custom para el cliente 
                (playbooks, integraciones, scripts) sigue siendo propiedad de Jeturing, pero el cliente recibe 
                una licencia perpetua de uso interno.
              </p>
            </section>

            <section>
              <h2 className="text-2xl font-bold text-white mb-4">7. Acuerdos de Asociación de Negocios (BAA/DPA)</h2>
              <p className="text-gray-300">
                Para clientes regulados bajo <strong>HIPAA</strong> (salud) o <strong>GDPR</strong> (Europa), 
                Jeturing firma un Business Associate Agreement (BAA) o Data Processing Agreement (DPA) sin costo adicional.
              </p>
              <p className="text-gray-300 mt-4">
                El cliente debe solicitar el BAA/DPA <strong>antes de la firma del contrato</strong>. 
                Jeturing NO procesa PHI (Protected Health Information) ni PII (Personally Identifiable Information) 
                sin un BAA/DPA firmado previamente.
              </p>
            </section>

            <section>
              <h2 className="text-2xl font-bold text-white mb-4">8. No Solicitación de Personal</h2>
              <p className="text-gray-300">
                Durante la vigencia del contrato y por <strong>12 meses después de su terminación</strong>, 
                el cliente se compromete a NO contratar, reclutar ni solicitar (directa o indirectamente) a 
                empleados, consultores o contratistas de Jeturing que hayan trabajado en la cuenta del cliente.
              </p>
              <p className="text-gray-300 mt-4">
                Violación de esta cláusula resulta en una penalidad equivalente al <strong>100% del salario anual</strong> 
                del empleado contratado.
              </p>
            </section>

            <section>
              <h2 className="text-2xl font-bold text-white mb-4">9. Confidencialidad</h2>
              <p className="text-gray-300">
                Ambas partes acuerdan mantener confidencial toda información técnica, comercial y estratégica 
                intercambiada durante la relación contractual. La obligación de confidencialidad sobrevive 
                <strong> 5 años después de la terminación del contrato</strong>.
              </p>
              <p className="text-gray-300 mt-4">
                Jeturing puede usar información agregada y anonimizada del cliente para mejoras del servicio, 
                benchmarking e investigación, siempre que no identifique al cliente específicamente.
              </p>
            </section>

            <section>
              <h2 className="text-2xl font-bold text-white mb-4">10. Ley Aplicable y Jurisdicción</h2>
              <p className="text-gray-300">
                Este contrato se rige por las leyes del <strong>Estado de Delaware, Estados Unidos</strong>, 
                sin considerar conflictos de leyes. Cualquier disputa se resolverá en tribunales estatales 
                o federales ubicados en Delaware.
              </p>
              <p className="text-gray-300 mt-4">
                Las partes aceptan someterse a la jurisdicción exclusiva de dichos tribunales y renuncian 
                a cualquier objeción por inconveniencia del foro.
              </p>
            </section>

            <section>
              <h2 className="text-2xl font-bold text-white mb-4">11. Modificaciones a estos Términos</h2>
              <p className="text-gray-300">
                Jeturing se reserva el derecho de modificar estos términos con <strong>30 días de aviso previo</strong> 
                por escrito. El uso continuado del servicio después de la fecha efectiva constituye aceptación 
                de los nuevos términos.
              </p>
              <p className="text-gray-300 mt-4">
                Si el cliente no está de acuerdo con los cambios, puede terminar el servicio antes de la 
                fecha efectiva sin penalidad.
              </p>
            </section>

            <section>
              <h2 className="text-2xl font-bold text-white mb-4">12. Contacto Legal</h2>
              <p className="text-gray-300">
                Para cuestiones legales, contractuales o de cumplimiento:
              </p>
              <p className="text-gray-300 mt-4">
                <strong>Jeturing Inc.</strong><br />
                Atención: Departamento Legal<br />
                Email: <a href="mailto:legal@jeturing.com" className="text-cyan-400 hover:underline">legal@jeturing.com</a><br />
                Teléfono: +1 (302) 555-0190<br />
                Dirección postal: 16192 Coastal Highway, Lewes, DE 19958, USA
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
