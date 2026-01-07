# 🚀 Plan Completo de Onboarding con Stripe - MCP Kali Forensics v4.6
**Fecha**: 29 de Diciembre de 2025  
**Estado**: 📋 Planificación  
**Versión**: 1.0.0

---

## 📋 Índice

1. [Visión General](#visión-general)
2. [Arquitectura de Onboarding](#arquitectura-de-onboarding)
3. [Integración Stripe](#integración-stripe)
4. [Flujo de Registro](#flujo-de-registro)
5. [Implementación Backend](#implementación-backend)
6. [Implementación Frontend](#implementación-frontend)
7. [Webhooks y Eventos](#webhooks-y-eventos)
8. [Planes y Precios](#planes-y-precios)
9. [Testing](#testing)
10. [Deployment](#deployment)

---

## 🎯 Visión General

### Objetivo
Crear un sistema de onboarding automatizado que permita:
- ✅ Registro de nuevos clientes vía web
- ✅ Selección de plan (Free, Pro, Enterprise)
- ✅ Pago automático vía Stripe
- ✅ Creación automática de tenant y agentes LLM
- ✅ Provisión de recursos (contenedores, credenciales)
- ✅ Facturación recurrente automática
- ✅ Gestión de suscripciones (upgrade/downgrade/cancelación)

### Flujo de Usuario
```
1. Usuario visita /signup
2. Completa formulario de registro
3. Selecciona plan (Free/Pro/Enterprise)
4. Si plan pago → Stripe Checkout
5. Pago exitoso → Webhook activa provisión
6. Sistema crea:
   - Tenant en DB
   - Usuario admin
   - Agente(s) LLM dedicados
   - Credenciales M365 (si Enterprise)
7. Email de bienvenida con acceso
8. Usuario redirigido a dashboard
```

---

## 🏗️ Arquitectura de Onboarding

```
┌─────────────────────────────────────────────────────────┐
│                    Frontend React                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────────┐         │
│  │ /signup  │  │/pricing  │  │/dashboard    │         │
│  └────┬─────┘  └────┬─────┘  └──────────────┘         │
│       │             │                                    │
└───────┼─────────────┼────────────────────────────────────┘
        │             │
        │ POST        │ Stripe.js
        │ /register   │ Elements
        │             │
┌───────▼─────────────▼────────────────────────────────────┐
│                 FastAPI Backend                          │
│  ┌─────────────────────────────────────────────────┐    │
│  │ /api/onboarding/                                │    │
│  │  - POST /register      (Step 1: User data)     │    │
│  │  - POST /checkout      (Step 2: Payment)       │    │
│  │  - POST /webhook       (Step 3: Provision)     │    │
│  │  - GET  /status/{id}   (Check status)          │    │
│  └─────────────────────────────────────────────────┘    │
│                          │                               │
│  ┌─────────────────────────────────────────────────┐    │
│  │ OnboardingService                               │    │
│  │  - create_tenant()                              │    │
│  │  - provision_llm_agents()                       │    │
│  │  - setup_m365_integration()                     │    │
│  │  - send_welcome_email()                         │    │
│  └─────────────────────────────────────────────────┘    │
└────────────────────────┬─────────────────────────────────┘
                         │
┌────────────────────────▼─────────────────────────────────┐
│                   Stripe Platform                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │ Checkout     │  │ Subscriptions│  │ Webhooks     │  │
│  │ Sessions     │  │ Management   │  │ Events       │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
└──────────────────────────────────────────────────────────┘
                         │
┌────────────────────────▼─────────────────────────────────┐
│              Database (PostgreSQL)                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │ tenants      │  │ subscriptions│  │ invoices     │  │
│  │ users        │  │ llm_agents   │  │ usage_logs   │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
└──────────────────────────────────────────────────────────┘
```

---

## 💳 Integración Stripe

### 1. Configuración de Cuenta Stripe

**Requisitos**:
- Cuenta Stripe (https://stripe.com)
- API Keys (Test + Production)
- Webhook endpoint configurado

**Credenciales necesarias** (añadir a `.env`):
```bash
# Stripe Configuration
STRIPE_PUBLISHABLE_KEY=pk_test_xxxxx  # Para frontend
STRIPE_SECRET_KEY=sk_test_xxxxx        # Para backend
STRIPE_WEBHOOK_SECRET=whsec_xxxxx      # Para validar webhooks
STRIPE_SUCCESS_URL=http://localhost:3000/onboarding/success
STRIPE_CANCEL_URL=http://localhost:3000/pricing
```

### 2. Productos y Precios en Stripe Dashboard

Crear 3 productos:

#### Plan Free
- **Producto**: "MCP Forensics Free"
- **Precio**: $0/mes
- **ID**: `price_free_monthly`
- **Características**:
  - 1 agente LLM (phi4-mini)
  - 100 queries/mes
  - 1 GB storage
  - Soporte community

#### Plan Pro
- **Producto**: "MCP Forensics Pro"
- **Precio**: $99/mes
- **ID**: `price_pro_monthly`
- **Características**:
  - 3 agentes LLM (phi4-mini)
  - 1,000 queries/mes
  - 10 GB storage
  - Soporte email (48h)
  - M365 integration

#### Plan Enterprise
- **Producto**: "MCP Forensics Enterprise"
- **Precio**: $499/mes
- **ID**: `price_enterprise_monthly`
- **Características**:
  - 10 agentes LLM (cualquier modelo)
  - Unlimited queries
  - 100 GB storage
  - Soporte 24/7
  - M365 + Azure AD integration
  - Dedicated IP
  - SLA 99.9%

### 3. Webhooks a Configurar

URL: `https://tu-dominio.com/api/onboarding/webhook`

**Eventos a escuchar**:
```
checkout.session.completed     → Activar cuenta
customer.subscription.created  → Crear suscripción
customer.subscription.updated  → Actualizar plan
customer.subscription.deleted  → Cancelar/pausar cuenta
invoice.paid                   → Confirmar pago
invoice.payment_failed         → Suspender cuenta
payment_intent.succeeded       → Procesar pago exitoso
```

---

## 📝 Flujo de Registro Detallado

### Paso 1: Formulario de Registro
**Endpoint**: `POST /api/onboarding/register`

**Request**:
```json
{
  "company_name": "Empresa Corp",
  "admin_email": "admin@empresa.com",
  "admin_name": "Juan Pérez",
  "phone": "+1234567890",
  "country": "US",
  "company_size": "50-200",
  "selected_plan": "pro"
}
```

**Response**:
```json
{
  "registration_id": "reg_abc123",
  "status": "pending_payment",
  "tenant_id": "empresa-corp",
  "next_step": "checkout",
  "checkout_url": "https://checkout.stripe.com/c/pay/cs_xxx"
}
```

### Paso 2: Stripe Checkout
**Endpoint**: `POST /api/onboarding/checkout`

Backend crea Checkout Session:
```python
checkout_session = stripe.checkout.Session.create(
    mode='subscription',
    customer_email=admin_email,
    line_items=[{
        'price': price_id,  # price_pro_monthly
        'quantity': 1
    }],
    success_url=f"{FRONTEND_URL}/onboarding/success?session_id={{CHECKOUT_SESSION_ID}}",
    cancel_url=f"{FRONTEND_URL}/pricing",
    metadata={
        'tenant_id': tenant_id,
        'registration_id': registration_id
    }
)
```

Usuario es redirigido a Stripe Checkout (hosted).

### Paso 3: Webhook - Provisión Automática
**Endpoint**: `POST /api/onboarding/webhook`

Cuando `checkout.session.completed`:
```python
async def handle_checkout_completed(session):
    tenant_id = session.metadata['tenant_id']
    
    # 1. Crear tenant en DB
    tenant = await create_tenant(tenant_id, session)
    
    # 2. Crear usuario admin
    user = await create_admin_user(tenant_id, session.customer_email)
    
    # 3. Provisionar agentes LLM según plan
    agents = await provision_llm_agents(tenant_id, plan)
    
    # 4. Setup M365 (si aplica)
    if plan in ['pro', 'enterprise']:
        await setup_m365_credentials(tenant_id)
    
    # 5. Crear suscripción en DB
    await create_subscription(tenant_id, session.subscription)
    
    # 6. Enviar email de bienvenida
    await send_welcome_email(user.email, tenant_id, credentials)
    
    # 7. Log audit
    await log_onboarding_event(tenant_id, 'completed')
```

### Paso 4: Acceso al Dashboard
Usuario recibe email con:
- URL de acceso: `https://app.forensics.com/login`
- Credenciales temporales
- Link para cambiar password
- Guía de inicio rápido

---

## 🔧 Implementación Backend

### Estructura de Archivos
```
api/
├── routes/
│   ├── onboarding.py         # Endpoints de onboarding
│   └── billing.py            # Gestión de facturación
├── services/
│   ├── onboarding_service.py # Lógica de provisión
│   ├── stripe_service.py     # Integración Stripe
│   └── email_service.py      # Envío de emails
└── models/
    ├── subscription.py       # Modelo de suscripción
    └── onboarding.py         # Modelo de registro
```

### Modelos de Base de Datos

**Tabla: subscriptions**
```sql
CREATE TABLE subscriptions (
    id UUID PRIMARY KEY,
    tenant_id VARCHAR(100) REFERENCES tenants(id),
    stripe_customer_id VARCHAR(100) UNIQUE NOT NULL,
    stripe_subscription_id VARCHAR(100) UNIQUE NOT NULL,
    plan VARCHAR(50) NOT NULL,  -- free, pro, enterprise
    status VARCHAR(50) NOT NULL,  -- active, canceled, past_due
    current_period_start TIMESTAMP,
    current_period_end TIMESTAMP,
    cancel_at_period_end BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_subscriptions_tenant ON subscriptions(tenant_id);
CREATE INDEX idx_subscriptions_stripe_customer ON subscriptions(stripe_customer_id);
```

**Tabla: onboarding_requests**
```sql
CREATE TABLE onboarding_requests (
    id UUID PRIMARY KEY,
    registration_id VARCHAR(100) UNIQUE NOT NULL,
    tenant_id VARCHAR(100),
    company_name VARCHAR(200) NOT NULL,
    admin_email VARCHAR(200) NOT NULL,
    admin_name VARCHAR(200),
    phone VARCHAR(50),
    country VARCHAR(10),
    selected_plan VARCHAR(50) NOT NULL,
    status VARCHAR(50) NOT NULL,  -- pending, processing, completed, failed
    stripe_checkout_session_id VARCHAR(200),
    stripe_customer_id VARCHAR(100),
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);
```

**Tabla: usage_tracking**
```sql
CREATE TABLE usage_tracking (
    id UUID PRIMARY KEY,
    tenant_id VARCHAR(100) REFERENCES tenants(id),
    metric_name VARCHAR(100) NOT NULL,  -- queries, storage_gb, agents
    metric_value DECIMAL(10,2),
    recorded_at TIMESTAMP DEFAULT NOW(),
    period_start DATE,
    period_end DATE
);

CREATE INDEX idx_usage_tenant_period ON usage_tracking(tenant_id, period_start, period_end);
```

### Endpoints de Onboarding

**Archivo**: `/api/routes/onboarding.py`
```python
from fastapi import APIRouter, HTTPException, Request, BackgroundTasks
from pydantic import BaseModel, EmailStr
import stripe
import logging

router = APIRouter(prefix="/api/onboarding", tags=["Onboarding"])
logger = logging.getLogger(__name__)

# ============================================================================
# MODELS
# ============================================================================

class RegistrationRequest(BaseModel):
    company_name: str
    admin_email: EmailStr
    admin_name: str
    phone: str
    country: str
    company_size: str
    selected_plan: str  # free, pro, enterprise

class RegistrationResponse(BaseModel):
    registration_id: str
    status: str
    tenant_id: str
    next_step: str
    checkout_url: Optional[str] = None

# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post("/register", response_model=RegistrationResponse)
async def register_new_tenant(
    request: RegistrationRequest,
    background_tasks: BackgroundTasks
):
    """
    Paso 1: Registro inicial del tenant
    """
    try:
        # Validar email único
        existing = await check_email_exists(request.admin_email)
        if existing:
            raise HTTPException(400, "Email ya registrado")
        
        # Generar tenant_id
        tenant_id = generate_tenant_id(request.company_name)
        
        # Crear registro en DB
        registration = await create_onboarding_request({
            "tenant_id": tenant_id,
            "company_name": request.company_name,
            "admin_email": request.admin_email,
            "admin_name": request.admin_name,
            "phone": request.phone,
            "country": request.country,
            "selected_plan": request.selected_plan,
            "status": "pending"
        })
        
        # Si plan es FREE, provisionar inmediatamente
        if request.selected_plan == "free":
            background_tasks.add_task(
                provision_free_tenant,
                registration.id,
                tenant_id,
                request
            )
            return RegistrationResponse(
                registration_id=registration.id,
                status="processing",
                tenant_id=tenant_id,
                next_step="provisioning"
            )
        
        # Si plan es pago, crear Checkout Session
        checkout_session = await create_stripe_checkout(
            tenant_id=tenant_id,
            plan=request.selected_plan,
            email=request.admin_email,
            metadata={"registration_id": registration.id}
        )
        
        # Actualizar registro con session ID
        await update_onboarding_request(
            registration.id,
            {"stripe_checkout_session_id": checkout_session.id}
        )
        
        return RegistrationResponse(
            registration_id=registration.id,
            status="pending_payment",
            tenant_id=tenant_id,
            next_step="checkout",
            checkout_url=checkout_session.url
        )
    
    except Exception as e:
        logger.error(f"Error en registro: {e}", exc_info=True)
        raise HTTPException(500, f"Error en registro: {str(e)}")


@router.post("/webhook")
async def stripe_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Webhook de Stripe para eventos de pago
    """
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        raise HTTPException(400, "Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(400, "Invalid signature")
    
    # Manejar eventos
    if event.type == "checkout.session.completed":
        session = event.data.object
        background_tasks.add_task(
            handle_checkout_completed,
            session
        )
    
    elif event.type == "customer.subscription.updated":
        subscription = event.data.object
        background_tasks.add_task(
            handle_subscription_updated,
            subscription
        )
    
    elif event.type == "customer.subscription.deleted":
        subscription = event.data.object
        background_tasks.add_task(
            handle_subscription_canceled,
            subscription
        )
    
    elif event.type == "invoice.payment_failed":
        invoice = event.data.object
        background_tasks.add_task(
            handle_payment_failed,
            invoice
        )
    
    return {"received": True}


@router.get("/status/{registration_id}")
async def get_onboarding_status(registration_id: str):
    """
    Verificar estado de onboarding
    """
    registration = await get_onboarding_request(registration_id)
    if not registration:
        raise HTTPException(404, "Registro no encontrado")
    
    return {
        "registration_id": registration_id,
        "status": registration.status,
        "tenant_id": registration.tenant_id,
        "created_at": registration.created_at,
        "completed_at": registration.completed_at,
        "error_message": registration.error_message
    }
```

### Servicio de Provisión

**Archivo**: `/api/services/onboarding_service.py`
```python
async def provision_tenant(
    tenant_id: str,
    registration: OnboardingRequest,
    subscription: stripe.Subscription
):
    """
    Provisión completa de tenant
    """
    try:
        # 1. Crear tenant en DB
        tenant = await create_tenant({
            "id": tenant_id,
            "display_name": registration.company_name,
            "domain": extract_domain(registration.admin_email),
            "plan": registration.selected_plan,
            "is_active": True
        })
        
        # 2. Crear usuario admin
        password = generate_secure_password()
        user = await create_user({
            "email": registration.admin_email,
            "display_name": registration.admin_name,
            "tenant_id": tenant_id,
            "role": "admin",
            "password": hash_password(password),
            "is_active": True
        })
        
        # 3. Provisionar agentes LLM según plan
        plan_config = get_plan_configuration(registration.selected_plan)
        agents = []
        
        for i in range(plan_config['agents_count']):
            agent_name = f"{tenant_id}-agent{i+1}"
            port = await get_next_available_port()
            
            agent = await llm_agents_service.create_agent({
                "name": agent_name,
                "tenant_id": tenant_id,
                "model": plan_config['default_model'],
                "port": port,
                "memory_limit": plan_config['memory_per_agent']
            })
            agents.append(agent)
        
        # 4. Crear suscripción en DB
        await create_subscription_record({
            "tenant_id": tenant_id,
            "stripe_customer_id": subscription.customer,
            "stripe_subscription_id": subscription.id,
            "plan": registration.selected_plan,
            "status": subscription.status,
            "current_period_start": subscription.current_period_start,
            "current_period_end": subscription.current_period_end
        })
        
        # 5. Enviar email de bienvenida
        await send_welcome_email(
            to_email=registration.admin_email,
            tenant_id=tenant_id,
            password=password,
            plan=registration.selected_plan,
            agents=agents
        )
        
        # 6. Marcar onboarding como completado
        await update_onboarding_request(
            registration.id,
            {
                "status": "completed",
                "completed_at": datetime.utcnow()
            }
        )
        
        logger.info(f"✅ Tenant {tenant_id} provisionado exitosamente")
        return tenant
    
    except Exception as e:
        logger.error(f"❌ Error provisionando tenant {tenant_id}: {e}")
        await update_onboarding_request(
            registration.id,
            {
                "status": "failed",
                "error_message": str(e)
            }
        )
        raise


def get_plan_configuration(plan: str) -> dict:
    """
    Configuración por plan
    """
    configs = {
        "free": {
            "agents_count": 1,
            "default_model": "phi4-mini",
            "memory_per_agent": "4g",
            "storage_gb": 1,
            "queries_per_month": 100
        },
        "pro": {
            "agents_count": 3,
            "default_model": "phi4-mini",
            "memory_per_agent": "6g",
            "storage_gb": 10,
            "queries_per_month": 1000
        },
        "enterprise": {
            "agents_count": 10,
            "default_model": "phi4-mini",
            "memory_per_agent": "8g",
            "storage_gb": 100,
            "queries_per_month": -1  # unlimited
        }
    }
    return configs.get(plan, configs["free"])
```

---

## 🎨 Implementación Frontend

### Página de Precios

**Archivo**: `/frontend-react/src/pages/Pricing.jsx`
```jsx
import React from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box, Container, Grid, Card, CardContent, CardActions,
  Typography, Button, List, ListItem, ListItemIcon, ListItemText,
  Chip
} from '@mui/material';
import { Check as CheckIcon } from '@mui/icons-material';

const plans = [
  {
    id: 'free',
    name: 'Free',
    price: 0,
    description: 'Para empezar y probar',
    features: [
      '1 agente LLM (phi4-mini)',
      '100 queries/mes',
      '1 GB storage',
      'Soporte community',
      'API access'
    ],
    buttonText: 'Comenzar Gratis',
    popular: false
  },
  {
    id: 'pro',
    name: 'Pro',
    price: 99,
    description: 'Para equipos profesionales',
    features: [
      '3 agentes LLM',
      '1,000 queries/mes',
      '10 GB storage',
      'Soporte email (48h)',
      'M365 integration',
      'Advanced analytics',
      'Custom models'
    ],
    buttonText: 'Comenzar Prueba',
    popular: true
  },
  {
    id: 'enterprise',
    name: 'Enterprise',
    price: 499,
    description: 'Para grandes organizaciones',
    features: [
      '10+ agentes LLM',
      'Unlimited queries',
      '100 GB storage',
      'Soporte 24/7',
      'M365 + Azure AD',
      'Dedicated IP',
      'SLA 99.9%',
      'Custom deployment',
      'On-premise option'
    ],
    buttonText: 'Contactar Ventas',
    popular: false
  }
];

const Pricing = () => {
  const navigate = useNavigate();

  const handleSelectPlan = (planId) => {
    navigate(`/signup?plan=${planId}`);
  };

  return (
    <Container maxWidth="lg" sx={{ py: 8 }}>
      <Typography variant="h2" align="center" gutterBottom>
        Planes y Precios
      </Typography>
      <Typography variant="h5" align="center" color="text.secondary" sx={{ mb: 6 }}>
        Elige el plan perfecto para tu organización
      </Typography>

      <Grid container spacing={4} alignItems="stretch">
        {plans.map((plan) => (
          <Grid item xs={12} md={4} key={plan.id}>
            <Card
              sx={{
                height: '100%',
                display: 'flex',
                flexDirection: 'column',
                position: 'relative',
                border: plan.popular ? '2px solid' : '1px solid',
                borderColor: plan.popular ? 'primary.main' : 'divider'
              }}
            >
              {plan.popular && (
                <Chip
                  label="MÁS POPULAR"
                  color="primary"
                  size="small"
                  sx={{
                    position: 'absolute',
                    top: 16,
                    right: 16
                  }}
                />
              )}
              
              <CardContent sx={{ flexGrow: 1, pt: 4 }}>
                <Typography variant="h4" gutterBottom>
                  {plan.name}
                </Typography>
                
                <Box sx={{ mb: 2 }}>
                  <Typography variant="h3" component="span">
                    ${plan.price}
                  </Typography>
                  <Typography variant="h6" component="span" color="text.secondary">
                    /mes
                  </Typography>
                </Box>
                
                <Typography color="text.secondary" paragraph>
                  {plan.description}
                </Typography>

                <List dense>
                  {plan.features.map((feature, idx) => (
                    <ListItem key={idx} disableGutters>
                      <ListItemIcon sx={{ minWidth: 36 }}>
                        <CheckIcon color="primary" />
                      </ListItemIcon>
                      <ListItemText primary={feature} />
                    </ListItem>
                  ))}
                </List>
              </CardContent>

              <CardActions sx={{ p: 2 }}>
                <Button
                  fullWidth
                  variant={plan.popular ? 'contained' : 'outlined'}
                  size="large"
                  onClick={() => handleSelectPlan(plan.id)}
                >
                  {plan.buttonText}
                </Button>
              </CardActions>
            </Card>
          </Grid>
        ))}
      </Grid>
    </Container>
  );
};

export default Pricing;
```

### Página de Registro

**Archivo**: `/frontend-react/src/pages/Signup.jsx`
```jsx
import React, { useState, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import {
  Box, Container, Paper, Stepper, Step, StepLabel,
  TextField, Button, Typography, Alert, CircularProgress
} from '@mui/material';
import { onboardingService } from '../services/onboarding';

const steps = ['Información', 'Pago', 'Confirmación'];

const Signup = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [activeStep, setActiveStep] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  
  const [formData, setFormData] = useState({
    company_name: '',
    admin_email: '',
    admin_name: '',
    phone: '',
    country: 'US',
    company_size: '1-10',
    selected_plan: searchParams.get('plan') || 'pro'
  });

  const handleRegister = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await onboardingService.register(formData);
      
      if (response.next_step === 'checkout') {
        // Redirigir a Stripe Checkout
        window.location.href = response.checkout_url;
      } else {
        // Plan free, ir a paso 3
        setActiveStep(2);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Container maxWidth="md" sx={{ py: 8 }}>
      <Paper sx={{ p: 4 }}>
        <Typography variant="h4" gutterBottom>
          Crear Cuenta
        </Typography>

        <Stepper activeStep={activeStep} sx={{ mb: 4 }}>
          {steps.map((label) => (
            <Step key={label}>
              <StepLabel>{label}</StepLabel>
            </Step>
          ))}
        </Stepper>

        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        {activeStep === 0 && (
          <Box>
            <TextField
              fullWidth
              label="Nombre de la Empresa"
              value={formData.company_name}
              onChange={(e) => setFormData({...formData, company_name: e.target.value})}
              margin="normal"
              required
            />
            
            <TextField
              fullWidth
              label="Email del Administrador"
              type="email"
              value={formData.admin_email}
              onChange={(e) => setFormData({...formData, admin_email: e.target.value})}
              margin="normal"
              required
            />
            
            <TextField
              fullWidth
              label="Nombre Completo"
              value={formData.admin_name}
              onChange={(e) => setFormData({...formData, admin_name: e.target.value})}
              margin="normal"
              required
            />
            
            <TextField
              fullWidth
              label="Teléfono"
              value={formData.phone}
              onChange={(e) => setFormData({...formData, phone: e.target.value})}
              margin="normal"
            />

            <Button
              fullWidth
              variant="contained"
              size="large"
              onClick={handleRegister}
              disabled={loading || !formData.company_name || !formData.admin_email}
              sx={{ mt: 3 }}
            >
              {loading ? <CircularProgress size={24} /> : 'Continuar al Pago'}
            </Button>
          </Box>
        )}

        {activeStep === 2 && (
          <Box textAlign="center">
            <Typography variant="h5" color="success.main" gutterBottom>
              ¡Cuenta Creada Exitosamente!
            </Typography>
            <Typography paragraph>
              Hemos enviado un email a {formData.admin_email} con tus credenciales de acceso.
            </Typography>
            <Button
              variant="contained"
              onClick={() => navigate('/login')}
              sx={{ mt: 2 }}
            >
              Ir al Login
            </Button>
          </Box>
        )}
      </Paper>
    </Container>
  );
};

export default Signup;
```

### Servicio de Onboarding

**Archivo**: `/frontend-react/src/services/onboarding.js`
```javascript
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8888';

class OnboardingService {
  async register(formData) {
    const response = await fetch(`${API_BASE_URL}/api/onboarding/register`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(formData)
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Error en registro');
    }

    return response.json();
  }

  async getStatus(registrationId) {
    const response = await fetch(
      `${API_BASE_URL}/api/onboarding/status/${registrationId}`
    );

    if (!response.ok) {
      throw new Error('Error obteniendo estado');
    }

    return response.json();
  }
}

export const onboardingService = new OnboardingService();
export default onboardingService;
```

---

## 🔔 Webhooks y Eventos

### Configuración de Webhooks en Stripe

1. Ir a Stripe Dashboard → Developers → Webhooks
2. Click "Add endpoint"
3. URL: `https://tu-dominio.com/api/onboarding/webhook`
4. Seleccionar eventos:
   - `checkout.session.completed`
   - `customer.subscription.created`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
   - `invoice.paid`
   - `invoice.payment_failed`

### Manejo de Eventos

**checkout.session.completed**:
```python
async def handle_checkout_completed(session):
    # Recuperar registration_id del metadata
    registration_id = session.metadata['registration_id']
    registration = await get_onboarding_request(registration_id)
    
    # Obtener suscripción
    subscription = stripe.Subscription.retrieve(session.subscription)
    
    # Provisionar tenant
    await provision_tenant(
        tenant_id=registration.tenant_id,
        registration=registration,
        subscription=subscription
    )
```

**customer.subscription.deleted**:
```python
async def handle_subscription_canceled(subscription):
    # Encontrar tenant por stripe_subscription_id
    sub = await get_subscription_by_stripe_id(subscription.id)
    
    # Pausar agentes LLM
    agents = await llm_agents_service.list_agents(sub.tenant_id)
    for agent in agents:
        await llm_agents_service.stop_agent(agent.name)
    
    # Marcar tenant como inactivo
    await deactivate_tenant(sub.tenant_id)
    
    # Enviar email de cancelación
    await send_cancelation_email(sub.tenant_id)
```

**invoice.payment_failed**:
```python
async def handle_payment_failed(invoice):
    customer_id = invoice.customer
    sub = await get_subscription_by_stripe_customer(customer_id)
    
    # Enviar notificación
    await send_payment_failed_email(sub.tenant_id, invoice)
    
    # Si es el 3er intento fallido, suspender
    if invoice.attempt_count >= 3:
        await suspend_tenant(sub.tenant_id)
```

---

## 💰 Planes y Precios

| Característica | Free | Pro | Enterprise |
|----------------|------|-----|------------|
| **Precio** | $0/mes | $99/mes | $499/mes |
| **Agentes LLM** | 1 | 3 | 10+ |
| **Modelo** | phi4-mini | phi4-mini | Cualquiera |
| **Queries/mes** | 100 | 1,000 | Ilimitadas |
| **Storage** | 1 GB | 10 GB | 100 GB |
| **M365 Integration** | ❌ | ✅ | ✅ |
| **Azure AD** | ❌ | ❌ | ✅ |
| **Soporte** | Community | Email 48h | 24/7 |
| **SLA** | - | - | 99.9% |
| **Dedicated IP** | ❌ | ❌ | ✅ |
| **Custom Models** | ❌ | ✅ | ✅ |
| **API Rate Limit** | 10 req/min | 100 req/min | 1000 req/min |

---

## 🧪 Testing

### Test de Registro (Free Plan)
```bash
curl -X POST http://localhost:8888/api/onboarding/register \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "Test Company",
    "admin_email": "test@example.com",
    "admin_name": "Test User",
    "phone": "+1234567890",
    "country": "US",
    "company_size": "1-10",
    "selected_plan": "free"
  }'
```

### Test de Webhook (usando Stripe CLI)
```bash
# Instalar Stripe CLI
stripe listen --forward-to localhost:8888/api/onboarding/webhook

# Trigger evento de prueba
stripe trigger checkout.session.completed
```

### Test End-to-End
1. Visitar `/pricing`
2. Seleccionar plan Pro
3. Completar formulario de registro
4. Usar tarjeta de prueba Stripe: `4242 4242 4242 4242`
5. Verificar email de bienvenida
6. Login con credenciales recibidas
7. Verificar agentes LLM creados

---

## 🚀 Deployment

### 1. Configurar Variables de Entorno
```bash
# .env
STRIPE_PUBLISHABLE_KEY=pk_live_xxxxx
STRIPE_SECRET_KEY=sk_live_xxxxx
STRIPE_WEBHOOK_SECRET=whsec_xxxxx
STRIPE_SUCCESS_URL=https://app.forensics.com/onboarding/success
STRIPE_CANCEL_URL=https://app.forensics.com/pricing

# Stripe Price IDs (desde Stripe Dashboard)
STRIPE_PRICE_FREE=price_free_monthly
STRIPE_PRICE_PRO=price_pro_monthly
STRIPE_PRICE_ENTERPRISE=price_enterprise_monthly
```

### 2. Actualizar nginx para Servir Frontend
```nginx
server {
    listen 80;
    server_name app.forensics.com;

    # Frontend React (build estático)
    root /var/www/frontend/build;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    # API Backend
    location /api {
        proxy_pass http://mcp_api;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 3. Build Frontend
```bash
cd frontend-react
npm run build
cp -r build/* /var/www/frontend/build/
```

### 4. Reiniciar Servicios
```bash
docker-compose restart mcp-forensics-api
sudo systemctl reload nginx
```

### 5. Verificar Webhook
```bash
curl https://app.forensics.com/api/onboarding/webhook \
  -X POST \
  -H "stripe-signature: test" \
  -d '{}'

# Debe retornar 400 (signature inválida) si está configurado
```

---

## ✅ Checklist de Implementación

### Backend
- [ ] Crear modelos de DB (subscriptions, onboarding_requests, usage_tracking)
- [ ] Implementar `/api/routes/onboarding.py`
- [ ] Implementar `/api/services/onboarding_service.py`
- [ ] Implementar `/api/services/stripe_service.py`
- [ ] Configurar Stripe SDK (`pip install stripe`)
- [ ] Añadir webhooks handlers
- [ ] Configurar email service (SendGrid/AWS SES)
- [ ] Testing con Stripe CLI

### Frontend
- [ ] Crear `/pages/Pricing.jsx`
- [ ] Crear `/pages/Signup.jsx`
- [ ] Crear `/pages/OnboardingSuccess.jsx`
- [ ] Implementar `/services/onboarding.js`
- [ ] Integrar Stripe Elements (opcional para custom checkout)
- [ ] Añadir rutas al router principal
- [ ] Testing E2E

### Stripe
- [ ] Crear cuenta Stripe
- [ ] Crear productos y precios
- [ ] Configurar webhook endpoint
- [ ] Configurar email de Stripe
- [ ] Habilitar modo producción
- [ ] Configurar métodos de pago (tarjetas, ACH, etc.)

### Deployment
- [ ] Configurar variables de entorno
- [ ] Actualizar nginx para servir frontend
- [ ] Build y deploy frontend
- [ ] Configurar DNS (app.forensics.com)
- [ ] Habilitar SSL/TLS (Let's Encrypt)
- [ ] Probar onboarding completo en producción

---

## 📊 Métricas a Monitorear

- **Conversión**: Registros → Suscripciones pagadas
- **Churn Rate**: Cancelaciones por mes
- **MRR** (Monthly Recurring Revenue): Ingresos recurrentes
- **ARPU** (Average Revenue Per User): Ingreso promedio por usuario
- **LTV** (Lifetime Value): Valor de vida del cliente
- **CAC** (Customer Acquisition Cost): Costo de adquisición

---

**Versión**: 1.0.0  
**Estado**: 📋 Listo para Implementación  
**Próximo paso**: Crear modelos de DB y endpoints backend
