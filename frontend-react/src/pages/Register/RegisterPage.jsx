/**
 * Registration Page - Multi-step registration wizard
 */

import React, { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { 
  ArrowLeft, 
  ArrowRight, 
  Check, 
  Loader2,
  User,
  Mail,
  Building2,
  Phone,
  Lock,
  Eye,
  EyeOff,
  CheckCircle
} from 'lucide-react';
import registrationService from '../../services/registration';

const STEPS = [
  { id: 'info', title: 'Your Information', icon: User },
  { id: 'account', title: 'Create Account', icon: Lock },
  { id: 'complete', title: 'Complete', icon: CheckCircle },
];

const RegisterPage = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  
  const [currentStep, setCurrentStep] = useState('info');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [plans, setPlans] = useState([]);
  const [showPassword, setShowPassword] = useState(false);
  
  // Form data
  const [formData, setFormData] = useState({
    email: '',
    fullName: '',
    companyName: '',
    phone: '',
    selectedPlan: searchParams.get('plan') || 'free_trial',
    billingPeriod: searchParams.get('billing') || 'monthly',
    username: '',
    password: '',
    confirmPassword: '',
  });
  
  // Session data
  const [sessionData, setSessionData] = useState(null);
  const [completionData, setCompletionData] = useState(null);

  useEffect(() => {
    checkExistingSession();
  }, []);

  const checkExistingSession = async () => {
    try {
      const session = await registrationService.getSessionStatus();
      if (session?.session) {
        setSessionData(session.session);
        setFormData(prev => ({
          ...prev,
          email: session.session.email || '',
          fullName: session.session.full_name || '',
          companyName: session.session.company_name || '',
        }));
        // Resume at current step
        if (session.session.current_step) {
          setCurrentStep(session.session.current_step);
        }
      }
    } catch (err) {
      // No existing session, start fresh
    }
  };

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
    setError(null);
  };

  const validateStep = () => {
    switch (currentStep) {
      case 'info':
        if (!formData.email || !formData.fullName) {
          setError('Email and full name are required');
          return false;
        }
        if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
          setError('Please enter a valid email address');
          return false;
        }
        return true;
      
      case 'account':
        if (!formData.username || formData.username.length < 3) {
          setError('Username must be at least 3 characters');
          return false;
        }
        if (!/^[a-zA-Z0-9_]+$/.test(formData.username)) {
          setError('Username can only contain letters, numbers, and underscores');
          return false;
        }
        if (!formData.password || formData.password.length < 8) {
          setError('Password must be at least 8 characters');
          return false;
        }
        if (formData.password !== formData.confirmPassword) {
          setError('Passwords do not match');
          return false;
        }
        return true;
      
      default:
        return true;
    }
  };

  const handleNext = async () => {
    if (!validateStep()) return;
    
    setLoading(true);
    setError(null);
    
    try {
      switch (currentStep) {
        case 'info':
          // Start registration and proceed to account
          const startResult = await registrationService.startRegistration({
            email: formData.email,
            fullName: formData.fullName,
            companyName: formData.companyName,
            phone: formData.phone,
          });
          setSessionData(startResult.data);
          setCurrentStep('account');
          break;
        
        case 'account':
          // Create account
          const accountResult = await registrationService.createAccount(
            formData.username,
            formData.password
          );
          setCompletionData(accountResult.data);
          setCurrentStep('complete');
          break;
        
        default:
          break;
      }
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  const handleBack = () => {
    const stepIndex = STEPS.findIndex(s => s.id === currentStep);
    if (stepIndex > 0) {
      setCurrentStep(STEPS[stepIndex - 1].id);
      setError(null);
    }
  };

  const renderStepIndicator = () => (
    <div className="flex items-center justify-center mb-8">
      {STEPS.map((step, index) => {
        const StepIcon = step.icon;
        const isActive = step.id === currentStep;
        const isCompleted = STEPS.findIndex(s => s.id === currentStep) > index;
        
        return (
          <React.Fragment key={step.id}>
            <div className={`flex items-center ${isActive ? 'text-blue-400' : isCompleted ? 'text-green-400' : 'text-gray-500'}`}>
              <div className={`w-10 h-10 rounded-full flex items-center justify-center border-2 ${
                isActive ? 'border-blue-400 bg-blue-400/20' : 
                isCompleted ? 'border-green-400 bg-green-400/20' : 
                'border-gray-600'
              }`}>
                {isCompleted ? (
                  <Check className="w-5 h-5" />
                ) : (
                  <StepIcon className="w-5 h-5" />
                )}
              </div>
              <span className="ml-2 text-sm font-medium hidden sm:inline">{step.title}</span>
            </div>
            {index < STEPS.length - 1 && (
              <div className={`w-12 h-0.5 mx-2 ${isCompleted ? 'bg-green-400' : 'bg-gray-600'}`} />
            )}
          </React.Fragment>
        );
      })}
    </div>
  );

  const renderInfoStep = () => (
    <div className="space-y-6">
      <div>
        <label className="block text-sm font-medium text-gray-300 mb-2">
          <Mail className="w-4 h-4 inline mr-2" />
          Email Address *
        </label>
        <input
          type="email"
          name="email"
          value={formData.email}
          onChange={handleInputChange}
          className="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg text-white focus:outline-none focus:border-blue-500"
          placeholder="you@company.com"
          required
        />
      </div>
      
      <div>
        <label className="block text-sm font-medium text-gray-300 mb-2">
          <User className="w-4 h-4 inline mr-2" />
          Full Name *
        </label>
        <input
          type="text"
          name="fullName"
          value={formData.fullName}
          onChange={handleInputChange}
          className="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg text-white focus:outline-none focus:border-blue-500"
          placeholder="John Doe"
          required
        />
      </div>
      
      <div>
        <label className="block text-sm font-medium text-gray-300 mb-2">
          <Building2 className="w-4 h-4 inline mr-2" />
          Company Name (Optional)
        </label>
        <input
          type="text"
          name="companyName"
          value={formData.companyName}
          onChange={handleInputChange}
          className="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg text-white focus:outline-none focus:border-blue-500"
          placeholder="Acme Inc."
        />
      </div>
      
      <div>
        <label className="block text-sm font-medium text-gray-300 mb-2">
          <Phone className="w-4 h-4 inline mr-2" />
          Phone (Optional)
        </label>
        <input
          type="tel"
          name="phone"
          value={formData.phone}
          onChange={handleInputChange}
          className="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg text-white focus:outline-none focus:border-blue-500"
          placeholder="+1 (555) 123-4567"
        />
      </div>
    </div>
  );

  const renderAccountStep = () => (
    <div className="space-y-6">
      <div>
        <label className="block text-sm font-medium text-gray-300 mb-2">
          <User className="w-4 h-4 inline mr-2" />
          Username *
        </label>
        <input
          type="text"
          name="username"
          value={formData.username}
          onChange={handleInputChange}
          className="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg text-white focus:outline-none focus:border-blue-500"
          placeholder="johndoe"
          required
        />
        <p className="text-xs text-gray-500 mt-1">Letters, numbers, and underscores only</p>
      </div>
      
      <div>
        <label className="block text-sm font-medium text-gray-300 mb-2">
          <Lock className="w-4 h-4 inline mr-2" />
          Password *
        </label>
        <div className="relative">
          <input
            type={showPassword ? 'text' : 'password'}
            name="password"
            value={formData.password}
            onChange={handleInputChange}
            className="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg text-white focus:outline-none focus:border-blue-500 pr-12"
            placeholder="••••••••"
            required
          />
          <button
            type="button"
            onClick={() => setShowPassword(!showPassword)}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-white"
          >
            {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
          </button>
        </div>
        <p className="text-xs text-gray-500 mt-1">Minimum 8 characters</p>
      </div>
      
      <div>
        <label className="block text-sm font-medium text-gray-300 mb-2">
          <Lock className="w-4 h-4 inline mr-2" />
          Confirm Password *
        </label>
        <input
          type={showPassword ? 'text' : 'password'}
          name="confirmPassword"
          value={formData.confirmPassword}
          onChange={handleInputChange}
          className="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg text-white focus:outline-none focus:border-blue-500"
          placeholder="••••••••"
          required
        />
      </div>
    </div>
  );

  const renderCompleteStep = () => (
    <div className="text-center py-8">
      <div className="w-20 h-20 bg-green-500/20 rounded-full flex items-center justify-center mx-auto mb-6">
        <CheckCircle className="w-10 h-10 text-green-400" />
      </div>
      
      <h2 className="text-2xl font-bold text-white mb-4">
        Account Created Successfully!
      </h2>
      
      <p className="text-gray-400 mb-6">
        Welcome to MCP Forensics, {completionData?.username || formData.username}!
      </p>
      
      {completionData?.is_trial && (
        <div className="bg-blue-500/10 border border-blue-500 rounded-lg p-4 mb-6 max-w-md mx-auto">
          <p className="text-blue-400">
            <strong>🎉 Your {completionData?.trial_days || 15}-day free trial has started!</strong>
          </p>
          <p className="text-sm text-blue-300 mt-2">
            Trial ends: {completionData?.trial_ends ? new Date(completionData.trial_ends).toLocaleDateString() : 'N/A'}
          </p>
        </div>
      )}
      
      <button
        onClick={() => navigate('/login')}
        className="bg-blue-600 hover:bg-blue-700 text-white px-8 py-3 rounded-lg font-medium"
      >
        Go to Login
      </button>
    </div>
  );

  const renderCurrentStep = () => {
    switch (currentStep) {
      case 'info':
        return renderInfoStep();
      case 'account':
        return renderAccountStep();
      case 'complete':
        return renderCompleteStep();
      default:
        return null;
    }
  };

  return (
    <div className="min-h-screen bg-gray-900 py-12 px-4">
      <div className="max-w-lg mx-auto">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-white">Create Your Account</h1>
          <p className="text-gray-400 mt-2">
            Get started with MCP Forensics in minutes
          </p>
        </div>

        {/* Step Indicator */}
        {currentStep !== 'complete' && renderStepIndicator()}

        {/* Form Card */}
        <div className="bg-gray-800 rounded-xl p-6 shadow-xl">
          {/* Error */}
          {error && (
            <div className="bg-red-500/10 border border-red-500 text-red-400 px-4 py-3 rounded-lg mb-6">
              {error}
            </div>
          )}

          {/* Step Content */}
          {renderCurrentStep()}

          {/* Navigation Buttons */}
          {currentStep !== 'complete' && (
            <div className="flex justify-between mt-8">
              <button
                type="button"
                onClick={handleBack}
                disabled={currentStep === 'info'}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg ${
                  currentStep === 'info'
                    ? 'text-gray-600 cursor-not-allowed'
                    : 'text-gray-400 hover:text-white'
                }`}
              >
                <ArrowLeft className="w-4 h-4" />
                Back
              </button>
              
              <button
                type="button"
                onClick={handleNext}
                disabled={loading}
                className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-6 py-2 rounded-lg font-medium disabled:opacity-50"
              >
                {loading ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <>
                    {currentStep === 'account' ? 'Create Account' : 'Continue'}
                    <ArrowRight className="w-4 h-4" />
                  </>
                )}
              </button>
            </div>
          )}
        </div>

        {/* Login Link */}
        {currentStep !== 'complete' && (
          <p className="text-center text-gray-400 mt-6">
            Already have an account?{' '}
            <a href="/login" className="text-blue-400 hover:underline">
              Sign in
            </a>
          </p>
        )}
      </div>
    </div>
  );
};

export default RegisterPage;
