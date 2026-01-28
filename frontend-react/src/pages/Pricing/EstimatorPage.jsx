/**
 * Pricing Estimator Page
 * Full-page wizard for customers to estimate their pricing
 */

import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Helmet } from 'react-helmet-async';
import { useNavigate } from 'react-router-dom';
import PricingCalculator from '@/components/pricing/PricingCalculator';
import { ArrowLeft, CheckCircle } from 'lucide-react';

const PricingEstimatorPage = () => {
  const { t } = useTranslation(['common', 'pricing']);
  const navigate = useNavigate();

  return (
    <>
      <Helmet>
        <title>{t('pricing:pricing_model.title')} | Segrd Forensics</title>
        <meta 
          name="description" 
          content={t('pricing:pricing_model.calculator_description')}
        />
      </Helmet>

      <div className="min-h-screen bg-black">
        {/* Navigation Bar */}
        <div className="bg-gray-900/50 border-b border-gray-800 sticky top-0 z-40">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex items-center justify-between">
            <button
              onClick={() => navigate('/pricing')}
              className="flex items-center gap-2 text-gray-400 hover:text-white transition-colors"
            >
              <ArrowLeft className="w-5 h-5" />
              Volver a Precios
            </button>
            <h1 className="text-xl font-bold text-white">Estimador Personalizado</h1>
            <div className="w-20"></div>
          </div>
        </div>

        {/* Main Content */}
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
          {/* Header Section */}
          <div className="text-center mb-12">
            <h2 className="text-4xl font-bold text-white mb-4">
              Calcula tu Presupuesto Personalizado
            </h2>
            <p className="text-lg text-gray-400 max-w-2xl mx-auto">
              Nuestro modelo de precios es 100% transparente y se ajusta automáticamente según:
            </p>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-8">
              <div className="flex items-center justify-center gap-3 bg-gray-900/50 rounded-lg p-4 border border-gray-800">
                <CheckCircle className="w-5 h-5 text-blue-400 flex-shrink-0" />
                <span className="text-gray-300">Cantidad de dispositivos</span>
              </div>
              <div className="flex items-center justify-center gap-3 bg-gray-900/50 rounded-lg p-4 border border-gray-800">
                <CheckCircle className="w-5 h-5 text-amber-400 flex-shrink-0" />
                <span className="text-gray-300">Retención de logs</span>
              </div>
              <div className="flex items-center justify-center gap-3 bg-gray-900/50 rounded-lg p-4 border border-gray-800">
                <CheckCircle className="w-5 h-5 text-purple-400 flex-shrink-0" />
                <span className="text-gray-300">Liderazgo de seguridad</span>
              </div>
            </div>
          </div>

          {/* Calculator */}
          <div className="mb-12">
            <PricingCalculator />
          </div>

          {/* FAQ Section */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mt-16">
            <div>
              <h3 className="text-2xl font-bold text-white mb-6">Preguntas Frecuentes</h3>
              <div className="space-y-6">
                <div className="bg-gray-900/50 rounded-lg p-6 border border-gray-800">
                  <h4 className="text-lg font-semibold text-white mb-2">¿Cómo se calcula el precio?</h4>
                  <p className="text-gray-400 text-sm">
                    El precio se compone de: (dispositivos × tarifa tier) + retención + v-CISO + add-ons. 
                    Cada tier tiene una tarifa por dispositivo que disminuye según volumen.
                  </p>
                </div>

                <div className="bg-gray-900/50 rounded-lg p-6 border border-gray-800">
                  <h4 className="text-lg font-semibold text-white mb-2">¿Qué incluye la retención de logs?</h4>
                  <p className="text-gray-400 text-sm">
                    La base es 30 días. Aumentar a 90, 180 o 365 días agrega un costo fijo mensual 
                    para cobertura histórica completa en investigaciones forenses.
                  </p>
                </div>

                <div className="bg-gray-900/50 rounded-lg p-6 border border-gray-800">
                  <h4 className="text-lg font-semibold text-white mb-2">¿El v-CISO es obligatorio?</h4>
                  <p className="text-gray-400 text-sm">
                    No, es opcional. Sin v-CISO tienes acceso a todas las herramientas. 
                    Con v-CISO Lite o Estándar obtienes asesoría y liderazgo ejecutivo.
                  </p>
                </div>
              </div>
            </div>

            <div>
              <h3 className="text-2xl font-bold text-white mb-6">Ejemplos de Presupuesto</h3>
              <div className="space-y-4">
                <div className="bg-gradient-to-r from-blue-900/30 to-blue-800/30 rounded-lg p-6 border border-blue-500/30">
                  <h4 className="text-white font-semibold mb-2">Pequeña Empresa (25 dispositivos)</h4>
                  <p className="text-gray-300 text-sm mb-3">
                    • 25 dispositivos × $0.50 = $12.50<br/>
                    • Retención 90 días = $150<br/>
                    • v-CISO Lite = $1,500
                  </p>
                  <div className="text-lg font-bold text-blue-400">Total: $1,662.50/mes</div>
                </div>

                <div className="bg-gradient-to-r from-purple-900/30 to-purple-800/30 rounded-lg p-6 border border-purple-500/30">
                  <h4 className="text-white font-semibold mb-2">Empresa Mediana (150 dispositivos)</h4>
                  <p className="text-gray-300 text-sm mb-3">
                    • 150 dispositivos × $1.50 = $225<br/>
                    • Retención 90 días = $150<br/>
                    • v-CISO Estándar = $3,500<br/>
                    • MDR 24x7 + SIEM = $1,250
                  </p>
                  <div className="text-lg font-bold text-purple-400">Total: $5,125/mes</div>
                </div>

                <div className="bg-gradient-to-r from-amber-900/30 to-amber-800/30 rounded-lg p-6 border border-amber-500/30">
                  <h4 className="text-white font-semibold mb-2">Empresa Grande (300+ dispositivos)</h4>
                  <p className="text-gray-300 text-sm mb-3">
                    • 300 dispositivos × $3.00 = $900<br/>
                    • Retención 365 días = $500<br/>
                    • v-CISO Estándar = $3,500<br/>
                    • Todos los add-ons = $3,700
                  </p>
                  <div className="text-lg font-bold text-amber-400">Total: $8,600/mes</div>
                </div>
              </div>
            </div>
          </div>

          {/* CTA Section */}
          <div className="mt-16 bg-gradient-to-r from-blue-600 to-purple-600 rounded-lg p-8 text-center">
            <h3 className="text-2xl font-bold text-white mb-3">¿Necesitas ayuda?</h3>
            <p className="text-blue-100 mb-6">
              Nuestro equipo de ventas puede ayudarte con negociaciones especiales, 
              descuentos por volumen o planes personalizados.
            </p>
            <button className="bg-white text-blue-600 font-semibold px-8 py-3 rounded-lg hover:bg-gray-100 transition-colors">
              Contactar Equipo de Ventas
            </button>
          </div>
        </div>
      </div>
    </>
  );
};

export default PricingEstimatorPage;
