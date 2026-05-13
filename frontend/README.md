# Boeuf Contable SaaS — Frontend

React 18 + TypeScript + Vite + Tailwind CSS  
Sistema contable completo para PyMES venezolanas

---

## Stack

| Tecnología | Versión | Uso |
|-----------|---------|-----|
| React | 18.3 | UI framework |
| TypeScript | 5.4 | Tipado estático |
| Vite | 5.3 | Build tool |
| Tailwind CSS | 3.4 | Estilos utilitarios |
| TanStack Query | 5 | Cache + fetching de datos |
| React Hook Form | 7 | Formularios con validación |
| Recharts | 2 | Gráficos del Dashboard |
| Zustand | 4 | Estado global (extendible) |
| React Router DOM | 6 | Routing |
| Axios | 1.7 | HTTP client con interceptores JWT |
| SheetJS (xlsx) | 0.18 | Exportar a Excel |
| react-hot-toast | 2.4 | Notificaciones |

---

## Páginas implementadas (18 rutas)

| Ruta | Página | Descripción |
|------|--------|-------------|
| `/dashboard` | DashboardPage | Métricas, gráfico Recharts, accesos rápidos, tasa BCV |
| `/diario` | DiarioPage | Asientos con expansión de líneas, reversión |
| `/ajustes` | AjustesPage | Depreciaciones, provisiones, diferimientos |
| `/catalogo` | CatalogoPage | Plan de cuentas, búsqueda, agregar cuentas |
| `/mayor` | MayorPage | Mayor General por cuenta con saldo acumulado |
| `/balance` | BalancePage | Balance de Comprobación |
| `/balance-ajustado` | BalanceAjustadoPage | 8 columnas BC + Ajustes |
| `/resultado` | EstadoResultadoPage | Estado de Resultados con totales |
| `/situacion` | SituacionFinancieraPage | Activos, Pasivos, Patrimonio en 2 columnas |
| `/iva` | IvaPage | Libros IVA compras+ventas, liquidación automática |
| `/igtf` | IgtfPage | Operaciones divisas, cálculo 3% en tiempo real |
| `/retenciones` | RetencionesPage | Decreto 1808, 8 conceptos, cálculo automático |
| `/nomina` | NominaPage | ISLR progresivo, cargas sociales, asiento automático |
| `/provisiones` | ProvisionesPage | Vacaciones, utilidades, prima antigüedad |
| `/inventario` | InventarioPage | Entradas/salidas PEPS con saldo en tiempo real |
| `/activos` | ActivosPage | Activos fijos, depreciación mensual automática |
| `/seniat` | SeniatPage | Hub exportación TXT IVA, ISLR, IGTF |
| `/login` | LoginPage | Autenticación JWT |

---

## Componentes reutilizables

### `src/components/Common/index.tsx`
- `Modal` — Modal con Escape + click-outside
- `PageHeader` — Encabezado consistente con acciones
- `EmptyState` — Estado vacío uniforme
- `Spinner` — Loader animado
- `MesSelector` — Dropdown de mes 1-12
- `ExportBar` — Barra de acciones con botón Excel
- `Field` — Wrapper de input con label + error
- `CuadreBar` — Indicador visual Debe=Haber
- `TableFooter` — Pie de tabla con totales

### `src/components/Forms/AsientoModal.tsx`
- Modal central para crear asientos y ajustes
- Validación Debe=Haber en tiempo real
- Selector de cuentas del catálogo
- Correlativo automático desde backend

### `src/components/Layout/Layout.tsx`
- Sidebar con 18 links de navegación
- Tasa BCV en tiempo real (actualizada cada 5 min)
- Info de usuario + logout
- Responsive con scroll interno

---

## Setup rápido

### 1. Prerequisitos
- Node.js 18+
- Backend corriendo en `localhost:8000`

### 2. Instalar
```bash
git clone ...
cd boeuf-contable-frontend
cp .env.example .env
npm install
```

### 3. Desarrollo
```bash
npm run dev
# → http://localhost:3000
```

### 4. Build producción
```bash
npm run build
# Genera: dist/
```

---

## Deploy en Vercel

```bash
# Instalar CLI
npm i -g vercel

# Login
vercel login

# Deploy
vercel --prod

# Variables de entorno en Vercel dashboard:
# VITE_API_URL = https://boeuf-contable-api.railway.app
```

---

## Estructura de carpetas

```
src/
├── App.tsx               # Router principal (18 rutas)
├── main.tsx              # Entry point + QueryClient + Toaster
├── index.css             # Tailwind + design system completo
├── types/
│   └── index.ts          # Todos los tipos TS (matching backend)
├── services/
│   └── api.ts            # Axios + interceptores JWT + todos los endpoints
├── utils/
│   └── index.ts          # fmtBs, fmtDate, exportarExcel, calcularISLR, cn
├── contexts/
│   └── AuthContext.tsx   # Autenticación global (localStorage)
├── components/
│   ├── Layout/
│   │   └── Layout.tsx    # Sidebar + outlet
│   ├── Common/
│   │   └── index.tsx     # 9 componentes reutilizables
│   └── Forms/
│       └── AsientoModal.tsx  # Modal central de contabilidad
└── pages/
    ├── LoginPage.tsx
    ├── DashboardPage.tsx
    ├── DiarioPage.tsx
    ├── AjustesPage.tsx
    ├── CatalogoPage.tsx
    ├── MayorPage.tsx
    ├── BalancePage.tsx
    ├── BalanceAjustadoPage.tsx
    ├── EstadoResultadoPage.tsx
    ├── SituacionFinancieraPage.tsx
    ├── IvaPage.tsx
    ├── IgtfPage.tsx
    ├── RetencionesPage.tsx
    ├── NominaPage.tsx
    ├── ProvisionesPage.tsx
    ├── InventarioPage.tsx
    ├── ActivosPage.tsx
    └── SeniatPage.tsx
```

---

## Design System

```
Fuentes:
  display → Syne 600–800 (encabezados)
  body    → DM Sans 300–600 (texto)
  mono    → JetBrains Mono 400–500 (números, código)

Color primario:
  brand-500 → #1D9E75 (verde Boeuf)

Tokens CSS:
  --sidebar-width: 220px
  --topbar-height: 56px

Componentes Tailwind:
  .btn, .btn-primary, .btn-secondary, .btn-danger, .btn-ghost
  .input, .input-sm, .input-error
  .card, .card-hover
  .badge, .badge-green, .badge-red, .badge-blue, .badge-amber
  .data-table, .table-wrap
  .nav-item, .nav-section
  .modal-overlay, .modal-box
  .metric-card
  .empty-state
  .cuadre-ok, .cuadre-fail
```

---

## Stack completo del sistema

```
Frontend (Vercel)    →  boeuf-contable.vercel.app
Backend (Railway)    →  boeuf-contable-api.railway.app
PostgreSQL (Railway) →  Plugin PostgreSQL en Railway
Tasa BCV             →  ve.dolarapi.com (actualización diaria 8 AM)
```
