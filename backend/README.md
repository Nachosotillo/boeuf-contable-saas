# Boeuf Contable SaaS — Backend API

Sistema contable multitenant para PyMES venezolanas.  
**Python 3.11 · FastAPI · PostgreSQL · SQLAlchemy 2.0 async**

---

## Módulos implementados

| Módulo | Endpoints | Descripción |
|--------|-----------|-------------|
| Auth | `/api/v1/auth/` | Registro empresa + usuario, login JWT |
| Empresas | `/api/v1/empresas/` | CRUD empresa |
| Catálogo | `/api/v1/catalogo/` | Plan de cuentas editable, catálogo default venezolano |
| Asientos | `/api/v1/asientos/` | CRUD + validación Debe=Haber + reversión |
| Ajustes | `/api/v1/ajustes/` | Depreciaciones, provisiones, diferimientos |
| Reportes | `/api/v1/reportes/` | Balance comp., Balance ajustado, Mayor general, Estado resultado, Situación financiera |
| SENIAT | `/api/v1/seniat/` | TXT IVA Ventas, IVA Compras, Retenciones ISLR, IGTF |
| Nómina | `/api/v1/nomina/` | ISLR progresivo 6 tramos, cargas sociales, asiento automático |
| Inventario | `/api/v1/inventario/` | Entradas/salidas PEPS, saldo en tiempo real |
| Activos Fijos | `/api/v1/activos/` | Línea recta, asiento depreciación automático |
| IVA | `/api/v1/iva/` | Libros compras/ventas, liquidación automática |
| IGTF | `/api/v1/igtf/` | Registro operaciones divisas, cálculo 3% |
| Retenciones ISLR | `/api/v1/retenciones/` | Decreto 1808, 8 conceptos, TXT SENIAT |
| Tasas BCV | `/api/v1/tasas/` | Actualización diaria automática 8:00 AM |

---

## Setup rápido (desarrollo local)

### 1. Clonar y configurar
```bash
git clone https://github.com/tu-org/boeuf-contable-api.git
cd boeuf-contable-api
cp .env.example .env
# Edita .env con tus valores
```

### 2. Levantar PostgreSQL con Docker
```bash
docker compose up postgres -d
```

### 3. Instalar dependencias Python
```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 4. Iniciar API
```bash
uvicorn main:app --reload --port 8000
```

### 5. Abrir documentación interactiva
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

---

## Setup producción (Docker completo)
```bash
cp .env.example .env
# Configurar SECRET_KEY con: openssl rand -hex 32
docker compose up -d
```

---

## Flujo de uso típico

```
1. POST /api/v1/auth/registro     → Crear empresa + usuario admin
2. POST /api/v1/auth/login        → Obtener JWT token
3. GET  /api/v1/catalogo/         → Ver catálogo de cuentas
4. POST /api/v1/asientos/         → Crear asientos contables
5. GET  /api/v1/reportes/balance-comprobacion → Ver balance
6. GET  /api/v1/seniat/exportar-iva-ventas?mes=1&anio=2025 → Descargar TXT
```

---

## Validaciones tributarias Venezuela implementadas

- ✅ IVA 16% (alícuota general), 8% y 31% configurables
- ✅ Retención IVA 75% automática si cliente es SPE
- ✅ IGTF 3% en operaciones divisas (no-SPE)
- ✅ ISLR progresivo 6 tramos (tabla 2025)
- ✅ SSO 4%/9%, FAOV 1%/2%, INCES 0.5%/2%
- ✅ Protección Pensiones 9%/9%
- ✅ Retenciones ISLR Decreto 1808 (8 conceptos)
- ✅ TXT SENIAT IVA, ISLR e IGTF en formato oficial

---

## Estructura de carpetas

```
boeuf-contable-api/
├── main.py              # Punto de entrada FastAPI
├── config.py            # Settings (env vars)
├── database.py          # Conexión async PostgreSQL
├── models.py            # ORM SQLAlchemy (15 tablas)
├── schemas.py           # Pydantic v2 validación
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .env.example
├── routers/
│   ├── auth.py          # JWT login/registro
│   ├── empresas.py
│   ├── catalogo.py      # + catálogo default venezolano
│   ├── asientos.py      # + reversión automática
│   ├── ajustes.py
│   ├── reportes.py      # 5 reportes financieros
│   ├── seniat.py        # 4 exportadores TXT
│   ├── nomina.py        # ISLR progresivo
│   ├── inventario.py    # PEPS
│   ├── activos.py       # Línea recta
│   ├── iva.py
│   ├── igtf.py
│   ├── retenciones.py
│   └── tasas.py         # API BCV
├── utils/
│   └── auditoria.py
└── tasks/
    └── scheduler.py     # APScheduler tasa BCV
```

---

## Deployment Railway.app

```bash
# 1. Instalar Railway CLI
npm i -g @railway/cli

# 2. Login y crear proyecto
railway login
railway init

# 3. Agregar PostgreSQL
railway add --plugin postgresql

# 4. Configurar variables de entorno
railway variables set SECRET_KEY=$(openssl rand -hex 32)
railway variables set DEBUG=false

# 5. Deploy
railway up
```

Frontend → Vercel: `vercel --prod`
