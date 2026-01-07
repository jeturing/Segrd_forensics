/**
 * Pricing Page - Display subscription plans
 */

import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Check, 
  X, 
  Loader2, 
  Shield, 
  Zap, 
  Building2,
  ArrowRight
} from 'lucide-react';
import registrationService from '../../services/registration';

const PricingPage = () => {
  const navigate = useNavigate();
  const [plans, setPlans] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [billingPeriod, setBillingPeriod] = useState('monthly');

  useEffect(() => {
    loadPlans();
  }, []);

  const loadPlans = async () => {
    try {
      setLoading(true);
      const plansData = await registrationService.getPlans();
      setPlans(plansData);
    } catch (err) {
      setError('Failed to load plans. Please try again.');
      console.error('Failed to load plans:', err);
    } finally {
      setLoading(false);
    }
  };

  const getPlanIcon = (planId) => {
    switch (planId) {
      case 'free_trial':
        return <Zap className="w-8 h-8 text-blue-400" />;
      case 'professional':
        return <Shield className="w-8 h-8 text-purple-400" />;
      case 'enterprise':
        return <Building2 className="w-8 h-8 text-amber-400" />;
      default:
        return <Shield className="w-8 h-8 text-gray-400" />;
    }
  };

  const getPlanColor = (planId) => {
    switch (planId) {
      case 'free_trial':
        return 'border-blue-500 bg-blue-500/10';
      case 'professional':
        return 'border-purple-500 bg-purple-500/10';
      case 'enterprise':
        return 'border-amber-500 bg-amber-500/10';
      default:
        return 'border-gray-500';
    }
  };

  const getPrice = (plan) => {
    if (plan.is_free) return 'Free';
    const price = billingPeriod === 'yearly' ? plan.price_yearly : plan.price_monthly;
    return `$${price}`;
  };

  const getPricePeriod = (plan) => {
    if (plan.is_free) return `${plan.trial_days} days`;
    return billingPeriod === 'yearly' ? '/year' : '/month';
  };

  const handleSelectPlan = (planId) => {
    // Navigate to registration with selected plan
    navigate(`/register?plan=${planId}&billing=${billingPeriod}`);
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <Loader2 className="w-12 h-12 animate-spin text-blue-500" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-900 py-12 px-4">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold text-white mb-4">
            Choose Your Plan
          </h1>
          <p className="text-gray-400 text-lg max-w-2xl mx-auto">
            Start with a free trial and upgrade when you're ready. 
            All plans include our core forensic and IR capabilities.
          </p>
        </div>

        {/* Billing Toggle */}
        <div className="flex justify-center mb-8">
          <div className="bg-gray-800 rounded-lg p-1 inline-flex">
            <button
              onClick={() => setBillingPeriod('monthly')}
              className={`px-6 py-2 rounded-md text-sm font-medium transition-colors ${
                billingPeriod === 'monthly'
                  ? 'bg-blue-600 text-white'
                  : 'text-gray-400 hover:text-white'
              }`}
            >
              Monthly
            </button>
            <button
              onClick={() => setBillingPeriod('yearly')}
              className={`px-6 py-2 rounded-md text-sm font-medium transition-colors ${
                billingPeriod === 'yearly'
                  ? 'bg-blue-600 text-white'
                  : 'text-gray-400 hover:text-white'
              }`}
            >
              Yearly
              <span className="ml-2 text-xs text-green-400">Save 17%</span>
            </button>
          </div>
        </div>

        {/* Error */}
        {error && (
          <div className="bg-red-500/10 border border-red-500 text-red-400 px-4 py-3 rounded-lg mb-8 text-center">
            {error}
          </div>
        )}

        {/* Plans Grid */}
        <div className="grid md:grid-cols-3 gap-8 max-w-5xl mx-auto">
          {plans.map((plan) => (
            <div
              key={plan.plan_id}
              className={`relative rounded-2xl border-2 p-6 transition-transform hover:scale-105 ${getPlanColor(plan.plan_id)}`}
            >
              {/* Popular Badge */}
              {plan.plan_id === 'professional' && (
                <div className="absolute -top-3 left-1/2 transform -translate-x-1/2">
                  <span className="bg-purple-500 text-white text-xs font-bold px-3 py-1 rounded-full">
                    MOST POPULAR
                  </span>
                </div>
              )}

              {/* Plan Header */}
              <div className="text-center mb-6">
                <div className="flex justify-center mb-4">
                  {getPlanIcon(plan.plan_id)}
                </div>
                <h3 className="text-xl font-bold text-white mb-2">{plan.name}</h3>
                <p className="text-gray-400 text-sm">{plan.description}</p>
              </div>

              {/* Price */}
              <div className="text-center mb-6">
                <span className="text-4xl font-bold text-white">{getPrice(plan)}</span>
                <span className="text-gray-400 ml-1">{getPricePeriod(plan)}</span>
              </div>

              {/* Limits */}
              <div className="space-y-3 mb-6">
                <div className="flex items-center text-gray-300">
                  <Check className="w-5 h-5 text-green-400 mr-2" />
                  <span>{plan.max_users} users</span>
                </div>
                <div className="flex items-center text-gray-300">
                  <Check className="w-5 h-5 text-green-400 mr-2" />
                  <span>{plan.max_cases === -1 ? 'Unlimited' : plan.max_cases} cases</span>
                </div>
                <div className="flex items-center text-gray-300">
                  <Check className="w-5 h-5 text-green-400 mr-2" />
                  <span>{plan.max_storage_gb} GB storage</span>
                </div>
                <div className="flex items-center text-gray-300">
                  <Check className="w-5 h-5 text-green-400 mr-2" />
                  <span>
                    {plan.max_analyses_per_month === -1 
                      ? 'Unlimited analyses' 
                      : `${plan.max_analyses_per_month} analyses/month`}
                  </span>
                </div>
              </div>

              {/* Features */}
              <div className="space-y-2 mb-6">
                {(plan.features || []).slice(0, 5).map((feature, idx) => (
                  <div key={idx} className="flex items-center text-gray-400 text-sm">
                    <Check className="w-4 h-4 text-green-400 mr-2 flex-shrink-0" />
                    <span>{feature}</span>
                  </div>
                ))}
              </div>

              {/* CTA Button */}
              <button
                onClick={() => handleSelectPlan(plan.plan_id)}
                className={`w-full py-3 px-4 rounded-lg font-medium flex items-center justify-center gap-2 transition-colors ${
                  plan.plan_id === 'professional'
                    ? 'bg-purple-600 hover:bg-purple-700 text-white'
                    : plan.plan_id === 'enterprise'
                    ? 'bg-amber-600 hover:bg-amber-700 text-white'
                    : 'bg-blue-600 hover:bg-blue-700 text-white'
                }`}
              >
                {plan.is_free ? 'Start Free Trial' : 'Get Started'}
                <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          ))}
        </div>

        {/* Footer */}
        <div className="text-center mt-12 text-gray-500">
          <p>All plans include 24/7 monitoring, automatic updates, and basic support.</p>
          <p className="mt-2">
            Questions? <a href="mailto:sales@jeturing.com" className="text-blue-400 hover:underline">Contact our sales team</a>
          </p>
        </div>

        {/* Login Link */}
        <div className="text-center mt-8">
          <p className="text-gray-400">
            Already have an account?{' '}
            <a href="/login" className="text-blue-400 hover:underline">
              Sign in
            </a>
          </p>
        </div>
      </div>
    </div>
  );
};

export default PricingPage;
