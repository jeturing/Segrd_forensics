import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';

const PricingCalculator = () => {
  const { t } = useTranslation('pricing');

  const [deviceCount, setDeviceCount] = useState(50);
  const [retention, setRetention] = useState(30);
  const [tier, setTier] = useState('essential');

  const devicePricing = {
    essential: 0.5,
    professional: 1.5,
    critical: 3.0,
  };

  const retentionPricing = {
    30: 0,
    90: 150,
    180: 300,
    365: 500,
  };

  const calculatePrice = () => {
    const deviceCost = deviceCount * devicePricing[tier];
    const retentionCost = retentionPricing[retention];
    return deviceCost + retentionCost;
  };

  return (
    <div className="bg-gray-800 p-6 rounded-lg shadow-md">
      <h2 className="text-2xl font-bold text-white mb-4">{t('pricing_model.title')}</h2>
      <p className="text-gray-400 mb-6">{t('pricing_model.description')}</p>

      <div className="mb-4">
        <label className="block text-sm font-medium text-gray-300 mb-2">
          {t('pricing_model.device_pricing.title')}
        </label>
        <input
          type="number"
          min="1"
          max="10000"
          value={deviceCount}
          onChange={(e) => setDeviceCount(Number(e.target.value))}
          className="w-full px-4 py-2 bg-gray-700 text-white rounded-lg"
        />
      </div>

      <div className="mb-4">
        <label className="block text-sm font-medium text-gray-300 mb-2">
          {t('pricing_model.retention_tiers.title')}
        </label>
        <select
          value={retention}
          onChange={(e) => setRetention(Number(e.target.value))}
          className="w-full px-4 py-2 bg-gray-700 text-white rounded-lg"
        >
          {Object.entries(retentionPricing).map(([key, value]) => (
            <option key={key} value={key}>
              {t(`pricing_model.retention_tiers.${key}.label`)}
            </option>
          ))}
        </select>
      </div>

      <div className="mb-4">
        <label className="block text-sm font-medium text-gray-300 mb-2">
          {t('pricing_model.device_pricing.title')}
        </label>
        <select
          value={tier}
          onChange={(e) => setTier(e.target.value)}
          className="w-full px-4 py-2 bg-gray-700 text-white rounded-lg"
        >
          {Object.entries(devicePricing).map(([key, value]) => (
            <option key={key} value={key}>
              {t(`pricing_model.device_pricing.${key}.label`)}
            </option>
          ))}
        </select>
      </div>

      <div className="mt-6">
        <h3 className="text-xl font-bold text-white">
          {t('pricing_model.calculator_description')}
        </h3>
        <p className="text-2xl font-bold text-blue-400 mt-2">
          ${calculatePrice().toFixed(2)} / {t('billing_monthly')}
        </p>
      </div>
    </div>
  );
};

export default PricingCalculator;