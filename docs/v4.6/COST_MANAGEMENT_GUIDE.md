# 🎯 Sistema de Gestión de Costos - Guía Rápida

## ✅ Estado: IMPLEMENTADO

### 📊 **Tablas Creadas en PostgreSQL**

1. **`service_plans`** - Planes de servicio (Free, Professional, Enterprise)
2. **`resource_costs`** - Costos por recurso/herramienta
3. **`resource_usage`** - Registro de consumo (particionada por mes)
4. **`custom_pricing`** - Precios personalizados por tenant

### 💰 **Planes Configurados**

| Plan | Precio Mensual | Precio Anual | Usuarios | Casos/Mes | Análisis/Mes |
|------|---------------|--------------|----------|-----------|--------------|
| **Free** | $0 | $0 | 1 | 5 | 10 |
| **Professional** | $99 | $950.40 | 5 | 50 | 200 |
| **Enterprise** | $499 | $4,790.40 | Ilimitado | Ilimitado | Ilimitado |

**Ahorro anual**: 20% al pagar anualmente

### 🔧 **Costos de Herramientas Configurados**

| Herramienta | Costo por Uso | Tipo |
|------------|---------------|------|
| Sparrow (M365) | $5.00 | analysis |
| Hawk (Exchange) | $3.00 | analysis |
| O365 Extractor | $2.00 | analysis |
| Loki Scanner | $1.00 | analysis |
| YARA Scan | $0.50 | analysis |
| OSQuery | $0.75 | analysis |
| Volatility | $10.00 | analysis |
| HIBP Check | $0.01 | analysis |
| Dehashed | $0.05 | analysis |
| Evidence Storage | $0.10/GB | storage |

### 📡 **API Endpoints Disponibles**

#### Planes
- `GET /api/costs/plans` - Lista todos los planes
- `GET /api/costs/plans/{code}` - Detalles de un plan
- `POST /api/costs/plans` - Crear plan (admin)
- `PUT /api/costs/plans/{id}` - Actualizar plan (admin)

#### Costos de Recursos
- `GET /api/costs/resources` - Lista costos configurados
- `GET /api/costs/resources/{id}` - Detalles de costo
- `POST /api/costs/resources` - Crear costo (admin)
- `PUT /api/costs/resources/{id}` - Actualizar costo (admin)

#### Registro de Uso
- `POST /api/costs/usage` - Registrar consumo
- `GET /api/costs/usage/tenant/{id}` - Costos del tenant
- `GET /api/costs/usage/tenant/{id}/by-tool` - Costos por herramienta
- `GET /api/costs/usage/case/{id}` - Costos de un caso

#### Calculadora
- `POST /api/costs/calculate` - Calcular costo estimado

### 🔌 **Integración con Backend**

**Registrar uso automáticamente:**
```python
from api.services.cost_tracker import track_resource_usage

# En cada análisis forense
await track_resource_usage(
    tenant_id=tenant_id,
    resource_type="analysis",
    resource_name="Sparrow Analysis",
    units=1,
    case_id=case_id,
    tool_name="sparrow",
    execution_seconds=120
)
```

### 📝 **Función SQL para Registrar Uso**

```sql
SELECT register_resource_usage(
    'tenant-uuid'::UUID,           -- tenant_id
    'analysis',                     -- resource_type
    'Sparrow Analysis',             -- resource_name
    1,                              -- units
    'user-uuid'::UUID,              -- user_id
    'case-uuid'::UUID,              -- case_id
    'analysis-uuid'::UUID,          -- analysis_id
    'sparrow',                      -- tool_name
    120                             -- execution_seconds
);
```

### 📊 **Vistas Disponibles**

1. **`v_tenant_costs_summary`** - Resumen de costos por tenant/período
2. **`v_tool_costs_summary`** - Costos agregados por herramienta

### 🎨 **Próximos Pasos para Stripe**

1. ✅ **Sistema de costos configurado**
2. ⏳ **Crear productos en Stripe** (usar plan_code como reference)
3. ⏳ **Sincronizar `stripe_product_id` y `stripe_price_*_id`**
4. ⏳ **Implementar webhook de Stripe** para actualizar suscripciones
5. ⏳ **Conectar billing con resource_usage**

### 🔒 **Consideraciones de Seguridad**

- Todos los endpoints de admin requieren autenticación
- Los tenants solo pueden ver sus propios costos
- Los precios están en centavos (evita problemas de float)
- Particionado mensual para performance en queries de facturación

### 📈 **Ejemplo de Flujo Completo**

1. **Usuario se registra** → Se asigna plan "free"
2. **Ejecuta análisis Sparrow** → Se registra uso ($5.00)
3. **Fin de mes** → Se genera factura con total de costos
4. **Stripe cobra** → Se marca `is_billed=true` en resource_usage
5. **Usuario upgradea a Professional** → Cambio de plan en Stripe

---

## 🚀 **Comandos de Verificación**

```bash
# Ver planes
docker exec mcp-forensics-db psql -U forensics -d forensics_db -c "SELECT * FROM service_plans;"

# Ver costos de recursos
docker exec mcp-forensics-db psql -U forensics -d forensics_db -c "SELECT * FROM resource_costs;"

# Ver uso registrado (vacío hasta que haya consumo)
docker exec mcp-forensics-db psql -U forensics-d forensics_db -c "SELECT * FROM resource_usage;"
```

---

**✅ LISTO PARA INTEGRAR CON STRIPE**
