# Onboarding Flow Documentation

## Overview

The automated onboarding system provides a seamless 6-step process to convert new users into paying customers with full platform access.

## Onboarding Steps

```
┌─────────────────┐
│  1. Start       │  Email, name, company → Generate session_id & tenant_id
└────────┬────────┘
         ↓
┌─────────────────┐
│  2. Customer    │  Create Stripe customer record
└────────┬────────┘
         ↓
┌─────────────────┐
│  3. Payment     │  Collect payment method via Stripe Elements
└────────┬────────┘
         ↓
┌─────────────────┐
│  4. Plan        │  Select billing plan + optional discount code
└────────┬────────┘
         ↓
┌─────────────────┐
│  5. Subscribe   │  Create Stripe subscription with trial period
└────────┬────────┘
         ↓
┌─────────────────┐
│  6. Complete    │  Provision tenant & grant platform access
└─────────────────┘
```

## Frontend Integration

### 1. Initiate Onboarding

```javascript
// Step 1: Start onboarding
const response = await fetch('https://api.example.com/api/v1/onboarding/start', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-API-Key': 'your-api-key'
  },
  body: JSON.stringify({
    email: 'customer@example.com',
    name: 'John Doe',
    company_name: 'ACME Corp',
    phone: '+1234567890'
  })
});

const { data } = await response.json();
const { session_id, tenant_id } = data;

// Store session_id for subsequent steps
sessionStorage.setItem('onboarding_session', session_id);
```

### 2. Create Customer

```javascript
// Step 2: Create Stripe customer
const response = await fetch('https://api.example.com/api/v1/onboarding/step/create-customer', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-API-Key': 'your-api-key'
  },
  body: JSON.stringify({
    session_id: sessionStorage.getItem('onboarding_session')
  })
});

const { data } = await response.json();
// data.customer_id is now created in Stripe
```

### 3. Collect Payment Method

```javascript
// Step 3: Get SetupIntent client secret
const response = await fetch('https://api.example.com/api/v1/onboarding/step/setup-payment', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-API-Key': 'your-api-key'
  },
  body: JSON.stringify({
    session_id: sessionStorage.getItem('onboarding_session'),
    return_url: window.location.origin + '/onboarding/complete'
  })
});

const { data } = await response.json();
const { client_secret } = data;

// Initialize Stripe.js
const stripe = Stripe('pk_test_your_publishable_key');

// Mount Stripe Elements
const elements = stripe.elements({ clientSecret: client_secret });
const paymentElement = elements.create('payment');
paymentElement.mount('#payment-element');

// Handle form submission
const form = document.getElementById('payment-form');
form.addEventListener('submit', async (event) => {
  event.preventDefault();
  
  const { error } = await stripe.confirmSetup({
    elements,
    confirmParams: {
      return_url: window.location.origin + '/onboarding/complete',
    },
  });
  
  if (error) {
    // Show error to customer
    console.error(error.message);
  } else {
    // Payment method saved, continue to next step
    window.location.href = '/onboarding/select-plan';
  }
});
```

### 4. Select Plan

```javascript
// Step 4: Select billing plan
const response = await fetch('https://api.example.com/api/v1/onboarding/step/select-plan', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-API-Key': 'your-api-key'
  },
  body: JSON.stringify({
    session_id: sessionStorage.getItem('onboarding_session'),
    plan_id: 'enterprise',
    price_id: 'price_1ABC123...',
    discount_code: 'LAUNCH50' // Optional
  })
});
```

### 5. Create Subscription

```javascript
// Step 5: Create subscription
const response = await fetch('https://api.example.com/api/v1/onboarding/step/create-subscription', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-API-Key': 'your-api-key'
  },
  body: JSON.stringify({
    session_id: sessionStorage.getItem('onboarding_session')
  })
});

const { data } = await response.json();
// data.subscription_id is now active
// data.trial_end shows when trial period ends
```

### 6. Complete Onboarding

```javascript
// Step 6: Finalize onboarding
const response = await fetch('https://api.example.com/api/v1/onboarding/complete', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-API-Key': 'your-api-key'
  },
  body: JSON.stringify({
    session_id: sessionStorage.getItem('onboarding_session')
  })
});

const { data } = await response.json();
// Tenant is now provisioned and ready
// Redirect to platform dashboard
window.location.href = '/dashboard';
```

## React Example Component

```jsx
import React, { useState } from 'react';
import { loadStripe } from '@stripe/stripe-js';
import {
  Elements,
  PaymentElement,
  useStripe,
  useElements,
} from '@stripe/react-stripe-js';

const stripePromise = loadStripe('pk_test_your_publishable_key');

function OnboardingWizard() {
  const [step, setStep] = useState(1);
  const [sessionId, setSessionId] = useState(null);
  const [clientSecret, setClientSecret] = useState(null);

  // Step 1: Start
  const handleStart = async (formData) => {
    const response = await fetch('/api/v1/onboarding/start', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': process.env.REACT_APP_API_KEY,
      },
      body: JSON.stringify(formData),
    });
    const { data } = await response.json();
    setSessionId(data.session_id);
    setStep(2);
  };

  // Step 2: Create customer
  const handleCreateCustomer = async () => {
    await fetch('/api/v1/onboarding/step/create-customer', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': process.env.REACT_APP_API_KEY,
      },
      body: JSON.stringify({ session_id: sessionId }),
    });
    setStep(3);
  };

  // Step 3: Setup payment
  const handleSetupPayment = async () => {
    const response = await fetch('/api/v1/onboarding/step/setup-payment', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': process.env.REACT_APP_API_KEY,
      },
      body: JSON.stringify({
        session_id: sessionId,
        return_url: window.location.origin + '/onboarding/complete',
      }),
    });
    const { data } = await response.json();
    setClientSecret(data.client_secret);
  };

  return (
    <div className="onboarding-wizard">
      {step === 1 && <StartForm onSubmit={handleStart} />}
      {step === 2 && <CreateCustomerStep onNext={handleCreateCustomer} />}
      {step === 3 && clientSecret && (
        <Elements stripe={stripePromise} options={{ clientSecret }}>
          <PaymentForm sessionId={sessionId} onNext={() => setStep(4)} />
        </Elements>
      )}
      {step === 4 && <PlanSelection sessionId={sessionId} onNext={() => setStep(5)} />}
      {step === 5 && <CreateSubscription sessionId={sessionId} onNext={() => setStep(6)} />}
      {step === 6 && <CompleteOnboarding sessionId={sessionId} />}
    </div>
  );
}

// Payment form component
function PaymentForm({ sessionId, onNext }) {
  const stripe = useStripe();
  const elements = useElements();
  const [error, setError] = useState(null);
  const [processing, setProcessing] = useState(false);

  const handleSubmit = async (event) => {
    event.preventDefault();
    
    if (!stripe || !elements) return;

    setProcessing(true);

    const { error } = await stripe.confirmSetup({
      elements,
      confirmParams: {
        return_url: window.location.origin + '/onboarding/complete',
      },
      redirect: 'if_required',
    });

    if (error) {
      setError(error.message);
      setProcessing(false);
    } else {
      // Success, move to next step
      onNext();
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <PaymentElement />
      {error && <div className="error">{error}</div>}
      <button type="submit" disabled={!stripe || processing}>
        {processing ? 'Processing...' : 'Continue'}
      </button>
    </form>
  );
}

export default OnboardingWizard;
```

## State Management

### Session Status

Track onboarding status:

```javascript
const response = await fetch(`/api/v1/onboarding/status/${session_id}`, {
  headers: {
    'X-API-Key': 'your-api-key'
  }
});

const { data } = await response.json();

// data.status values:
// - "started" - Initial state
// - "customer_created" - Stripe customer created
// - "payment_setup" - Payment method configured
// - "plan_selected" - Plan chosen
// - "subscription_created" - Subscription active
// - "completed" - Onboarding complete
// - "failed" - Error occurred
// - "expired" - Session timed out (24 hours)
```

### Error Handling

```javascript
try {
  const response = await fetch('/api/v1/onboarding/step/...', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-API-Key': 'your-api-key'
    },
    body: JSON.stringify({ ... })
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail);
  }

  const { data } = await response.json();
  // Continue to next step
} catch (error) {
  // Show error to user
  console.error('Onboarding error:', error.message);
  // Optionally rollback or retry
}
```

## Session Expiration

Onboarding sessions expire after 24 hours. Check expiration:

```javascript
const { data } = await fetch(`/api/v1/onboarding/status/${session_id}`).then(r => r.json());

if (data.status === 'expired') {
  // Session expired, start new onboarding
  alert('Your session has expired. Please start over.');
  window.location.href = '/onboarding/start';
}
```

## Available Plans

Fetch available plans for display:

```javascript
const response = await fetch('/api/v1/onboarding/plans');
const { data } = await response.json();

data.plans.forEach(plan => {
  console.log(plan.name); // "Enterprise", "Professional", "Basic"
  console.log(plan.price_monthly); // Price in cents
  console.log(plan.features); // Array of features
  console.log(plan.stripe_price_id_monthly); // Stripe price ID
});
```

## Best Practices

### Progress Indicator

Show users their progress:

```jsx
<div className="progress-bar">
  <div className={step >= 1 ? 'active' : ''}>1. Info</div>
  <div className={step >= 2 ? 'active' : ''}>2. Account</div>
  <div className={step >= 3 ? 'active' : ''}>3. Payment</div>
  <div className={step >= 4 ? 'active' : ''}>4. Plan</div>
  <div className={step >= 5 ? 'active' : ''}>5. Subscribe</div>
  <div className={step >= 6 ? 'active' : ''}>6. Complete</div>
</div>
```

### Session Persistence

Save session ID to prevent loss on page refresh:

```javascript
// Save on start
sessionStorage.setItem('onboarding_session', session_id);
sessionStorage.setItem('onboarding_step', step);

// Restore on page load
const savedSession = sessionStorage.getItem('onboarding_session');
const savedStep = parseInt(sessionStorage.getItem('onboarding_step') || '1');

if (savedSession) {
  setSessionId(savedSession);
  setStep(savedStep);
  // Verify session is still valid
  checkSessionStatus(savedSession);
}
```

### Validation

Validate each step before proceeding:

```javascript
const validateStep = async (step, data) => {
  switch(step) {
    case 1:
      // Validate email format
      if (!/\S+@\S+\.\S+/.test(data.email)) {
        throw new Error('Invalid email');
      }
      break;
    case 4:
      // Validate plan selection
      if (!data.price_id) {
        throw new Error('Please select a plan');
      }
      break;
  }
};
```

## Troubleshooting

### Payment Method Not Saving

- Ensure SetupIntent is confirmed before moving to next step
- Check Stripe Dashboard for error details
- Verify publishable key matches secret key environment

### Session Not Found

- Check session_id is being passed correctly
- Verify session hasn't expired (24 hours)
- Ensure API key is valid

### Subscription Creation Fails

- Verify customer has valid payment method
- Check price_id exists in your Stripe account
- Review Stripe error message in response

## Testing

### Test Flow

```bash
# 1. Start onboarding
curl -X POST http://localhost:8080/api/v1/onboarding/start \
  -H "Content-Type: application/json" \
  -H "X-API-Key: test-key" \
  -d '{"email":"test@example.com","name":"Test User"}'

# 2. Complete subsequent steps with returned session_id
# ... (see full examples above)
```

### Test Cards

Use these in development:
- Success: `4242 4242 4242 4242`
- Requires auth: `4000 0025 0000 3155`
- Decline: `4000 0000 0000 0002`

Expiry: Any future date  
CVC: Any 3 digits
