import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Helmet } from 'react-helmet-async';
import { Send, CheckCircle, Loader, Mail, Clock, Building } from 'lucide-react';
import { Navbar, Footer } from '../../components/landing';
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || import.meta.env.VITE_API_BASE_URL || '/api';

const ContactPage = () => {
  const { t } = useTranslation('common');
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    company: '',
    phone: '',
    message: '',
    interest: 'demo'
  });
  const [submitted, setSubmitted] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    
    try {
      const response = await axios.post(`${API_BASE_URL}/contact/submit`, {
        ...formData,
        submitted_at: new Date().toISOString()
      });

      if (response.data.success) {
        setSubmitted(true);
      } else {
        setError('Error al enviar el formulario. Por favor intenta nuevamente.');
      }
    } catch (err) {
      console.error('Error submitting contact form:', err);
      setError(err.response?.data?.detail || 'Error al enviar. Contacta directamente a sales@jeturing.com');
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (e) => {
    setFormData(prev => ({
      ...prev,
      [e.target.name]: e.target.value
    }));
  };

  if (submitted) {
    return (
      <>
        <Helmet>
          <title>Mensaje Enviado - SEGRD</title>
        </Helmet>
        <div className="min-h-screen bg-gray-900">
          <Navbar />
          <div className="max-w-2xl mx-auto px-4 py-32 text-center">
            <CheckCircle className="w-20 h-20 text-green-500 mx-auto mb-6" />
            <h1 className="text-3xl font-bold text-white mb-4">¡Mensaje Enviado!</h1>
            <p className="text-gray-400 text-lg mb-8">
              Gracias por contactarnos. Un miembro de nuestro equipo se pondrá en contacto contigo en las próximas 24 horas.
            </p>
            <a
              href="/"
              className="inline-flex items-center gap-2 bg-gradient-to-r from-cyan-500 to-blue-600 text-white px-6 py-3 rounded-lg font-medium hover:shadow-lg hover:shadow-cyan-500/25 transition-all"
            >
              Volver al Inicio
            </a>
          </div>
          <Footer />
        </div>
      </>
    );
  }

  return (
    <>
      <Helmet>
        <title>Contacto - SEGRD</title>
        <meta name="description" content="Contacta al equipo de SEGRD para solicitar una demo o información sobre nuestros servicios de seguridad y forense digital." />
      </Helmet>

      <div className="min-h-screen bg-gray-900">
        <Navbar />
        
        <div className="max-w-6xl mx-auto px-4 py-32">
          <div className="text-center mb-16">
            <h1 className="text-4xl md:text-5xl font-bold text-white mb-4">Contacto</h1>
            <p className="text-gray-400 text-lg max-w-2xl mx-auto">
              ¿Tienes preguntas? ¿Necesitas una demo personalizada? Estamos aquí para ayudarte.
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-12">
            {/* Contact Info */}
            <div className="space-y-8">
              <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-6">
                <Mail className="w-8 h-8 text-cyan-400 mb-4" />
                <h3 className="text-lg font-semibold text-white mb-2">Email</h3>
                <a href="mailto:sales@jeturing.com" className="text-cyan-400 hover:text-cyan-300 transition">
                  sales@jeturing.com
                </a>
              </div>

              <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-6">
                <Clock className="w-8 h-8 text-cyan-400 mb-4" />
                <h3 className="text-lg font-semibold text-white mb-2">Horario</h3>
                <p className="text-gray-400">
                  Lunes a Viernes<br />
                  9:00 AM - 6:00 PM (EST)
                </p>
              </div>

              <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-6">
                <Building className="w-8 h-8 text-cyan-400 mb-4" />
                <h3 className="text-lg font-semibold text-white mb-2">Empresa</h3>
                <p className="text-gray-400">
                  Jeturing Inc.<br />
                  Made in USA 🇺🇸
                </p>
              </div>

              <div className="bg-gradient-to-br from-cyan-500/10 to-blue-600/10 border border-cyan-500/20 rounded-xl p-6">
                <h3 className="text-lg font-semibold text-white mb-2">¿Necesitas una autoevaluación?</h3>
                <p className="text-gray-400 text-sm mb-4">
                  Completa nuestro checklist de seguridad y recibe una recomendación personalizada.
                </p>
                <a
                  href="/security-checklist"
                  className="inline-flex items-center gap-2 text-cyan-400 hover:text-cyan-300 font-medium transition"
                >
                  Ir a Autoevaluación →
                </a>
              </div>
            </div>

            {/* Contact Form */}
            <div className="md:col-span-2">
              <form onSubmit={handleSubmit} className="bg-gray-800/50 border border-gray-700 rounded-xl p-8 space-y-6">
                <h2 className="text-2xl font-bold text-white mb-6">Solicitar Demo</h2>

                {error && (
                  <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4 text-red-400">
                    {error}
                  </div>
                )}

                <div className="grid md:grid-cols-2 gap-6">
                  <div>
                    <label className="block text-white font-medium mb-2">Nombre *</label>
                    <input
                      type="text"
                      name="name"
                      required
                      value={formData.name}
                      onChange={handleChange}
                      className="w-full bg-gray-900 border border-gray-700 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-cyan-500 transition"
                      placeholder="Tu nombre"
                    />
                  </div>

                  <div>
                    <label className="block text-white font-medium mb-2">Email *</label>
                    <input
                      type="email"
                      name="email"
                      required
                      value={formData.email}
                      onChange={handleChange}
                      className="w-full bg-gray-900 border border-gray-700 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-cyan-500 transition"
                      placeholder="tu@empresa.com"
                    />
                  </div>
                </div>

                <div className="grid md:grid-cols-2 gap-6">
                  <div>
                    <label className="block text-white font-medium mb-2">Empresa</label>
                    <input
                      type="text"
                      name="company"
                      value={formData.company}
                      onChange={handleChange}
                      className="w-full bg-gray-900 border border-gray-700 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-cyan-500 transition"
                      placeholder="Nombre de tu empresa"
                    />
                  </div>

                  <div>
                    <label className="block text-white font-medium mb-2">Teléfono</label>
                    <input
                      type="tel"
                      name="phone"
                      value={formData.phone}
                      onChange={handleChange}
                      className="w-full bg-gray-900 border border-gray-700 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-cyan-500 transition"
                      placeholder="+1 (555) 123-4567"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-white font-medium mb-2">¿En qué estás interesado?</label>
                  <select
                    name="interest"
                    value={formData.interest}
                    onChange={handleChange}
                    className="w-full bg-gray-900 border border-gray-700 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-cyan-500 transition"
                  >
                    <option value="demo">Solicitar Demo</option>
                    <option value="pricing">Información de Precios</option>
                    <option value="foren">Módulo FOREN (Forense)</option>
                    <option value="axion">Módulo AXION (Respuesta a Incidentes)</option>
                    <option value="vigil">Módulo VIGIL (Monitoreo)</option>
                    <option value="orbia">Módulo ORBIA (Automatización)</option>
                    <option value="enterprise">Plan Enterprise</option>
                    <option value="partnership">Partnership</option>
                    <option value="other">Otro</option>
                  </select>
                </div>

                <div>
                  <label className="block text-white font-medium mb-2">Mensaje *</label>
                  <textarea
                    name="message"
                    required
                    rows="5"
                    value={formData.message}
                    onChange={handleChange}
                    className="w-full bg-gray-900 border border-gray-700 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-cyan-500 transition resize-none"
                    placeholder="Cuéntanos sobre tus necesidades de seguridad..."
                  />
                </div>

                <button
                  type="submit"
                  disabled={loading}
                  className="w-full bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-600 hover:to-blue-700 disabled:from-gray-600 disabled:to-gray-600 text-white font-semibold py-4 rounded-lg transition-all flex items-center justify-center gap-2"
                >
                  {loading ? (
                    <>
                      <Loader className="w-5 h-5 animate-spin" />
                      Enviando...
                    </>
                  ) : (
                    <>
                      <Send className="w-5 h-5" />
                      Enviar Mensaje
                    </>
                  )}
                </button>

                <p className="text-gray-500 text-sm text-center">
                  Al enviar este formulario, aceptas nuestra{' '}
                  <a href="/privacy" className="text-cyan-400 hover:underline">Política de Privacidad</a>.
                </p>
              </form>
            </div>
          </div>
        </div>

        <Footer />
      </div>
    </>
  );
};

export default ContactPage;
