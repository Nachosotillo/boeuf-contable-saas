/// <reference types="vite/client" />
import axios from 'axios'

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export const api = axios.create({
  baseURL: `${BASE_URL}/api/v1`,
  headers: { 'Content-Type': 'application/json' },
})

// Inyectar token JWT en cada request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('boeuf_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// Manejar 401 → redirigir a login
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('boeuf_token')
      localStorage.removeItem('boeuf_user')
      window.location.href = '/login'
    }
    return Promise.reject(err)
  }
)

// ─── Auth ──────────────────────────────────────────────────────────────────

export const authApi = {
  login: (email: string, password: string) =>
    api.post('/auth/login', new URLSearchParams({ username: email, password }),
      { headers: { 'Content-Type': 'application/x-www-form-urlencoded' } }),
  me: () => api.get('/auth/me'),
}

// ─── Tasa BCV ──────────────────────────────────────────────────────────────

export const tasasApi = {
  actual: () => api.get('/tasas/actual'),
  historico: (limit = 30) => api.get(`/tasas/historico?limit=${limit}`),
  forzarActualizacion: () => api.post('/tasas/forzar-actualizacion'),
}

// ─── Empresa ───────────────────────────────────────────────────────────────

export const empresaApi = {
  me: () => api.get('/empresas/me'),
  actualizar: (data: unknown) => api.put('/empresas/me', data),
}

// ─── Catálogo ──────────────────────────────────────────────────────────────

export const catalogoApi = {
  listar: () => api.get('/catalogo/'),
  crear: (data: unknown) => api.post('/catalogo/', data),
  actualizar: (id: number, data: unknown) => api.put(`/catalogo/${id}`, data),
  desactivar: (id: number) => api.delete(`/catalogo/${id}`),
}

// ─── Asientos ──────────────────────────────────────────────────────────────

export const asientosApi = {
  listar: (params?: { mes?: number; anio?: number; skip?: number; limit?: number }) =>
    api.get('/asientos/', { params }),
  obtener: (id: number) => api.get(`/asientos/${id}`),
  crear: (data: unknown) => api.post('/asientos/', data),
  reversar: (id: number) => api.delete(`/asientos/${id}`),
  proximoNumero: () => api.get('/asientos/proximo-numero'),
}

// ─── Ajustes ───────────────────────────────────────────────────────────────

export const ajustesApi = {
  listar: (mes?: number) => api.get('/ajustes/', { params: { mes } }),
  crear: (data: unknown) => api.post('/ajustes/', data),
}

// ─── Reportes ──────────────────────────────────────────────────────────────

export const reportesApi = {
  balanceComprobacion: (mes?: number) =>
    api.get('/reportes/balance-comprobacion', { params: { mes } }),
  balanceAjustado: (mes?: number) =>
    api.get('/reportes/balance-ajustado', { params: { mes } }),
  mayorGeneral: (cuenta_codigo: string, mes?: number) =>
    api.get('/reportes/mayor-general', { params: { cuenta_codigo, mes } }),
  estadoResultado: (mes?: number) =>
    api.get('/reportes/estado-resultado', { params: { mes } }),
  situacionFinanciera: () => api.get('/reportes/situacion-financiera'),
}

// ─── SENIAT ────────────────────────────────────────────────────────────────

export const seniatApi = {
  exportarIvaVentas: (mes: number, anio: number) =>
    api.get('/seniat/exportar-iva-ventas', { params: { mes, anio }, responseType: 'blob' }),
  exportarIvaCompras: (mes: number, anio: number) =>
    api.get('/seniat/exportar-iva-compras', { params: { mes, anio }, responseType: 'blob' }),
  exportarIslr: (mes: number, anio: number) =>
    api.get('/seniat/exportar-islr', { params: { mes, anio }, responseType: 'blob' }),
  exportarIgtf: (mes: number, anio: number) =>
    api.get('/seniat/exportar-igtf', { params: { mes, anio }, responseType: 'blob' }),
}

// ─── Nómina ────────────────────────────────────────────────────────────────

export const nominaApi = {
  listarEmpleados: () => api.get('/nomina/empleados'),
  crearEmpleado: (data: unknown) => api.post('/nomina/empleados', data),
  calcular: () => api.get('/nomina/calcular'),
  generarAsiento: () => api.post('/nomina/generar-asiento'),
  tablaIslr: () => api.get('/nomina/islr-tabla'),
}

// ─── Inventario ────────────────────────────────────────────────────────────

export const inventarioApi = {
  listarArticulos: () => api.get('/inventario/articulos'),
  crearArticulo: (data: unknown) => api.post('/inventario/articulos', data),
  actualizarArticulo: (id: number, data: unknown) => api.put(`/inventario/articulos/${id}`, data),
  listarMovimientos: (articulo_id?: number) => api.get('/inventario/movimientos', { params: { articulo_id } }),
  registrarMovimiento: (data: unknown) => api.post('/inventario/movimientos', data),
  saldo: () => api.get('/inventario/saldo'),
}

// ─── Activos Fijos ─────────────────────────────────────────────────────────

export const activosApi = {
  listar: () => api.get('/activos/'),
  crear: (data: unknown) => api.post('/activos/', data),
  generarDepreciacion: () => api.post('/activos/generar-depreciacion'),
}

// ─── IVA ───────────────────────────────────────────────────────────────────

export const ivaApi = {
  listarCompras: (mes?: number) => api.get('/iva/compras', { params: { mes } }),
  listarVentas: (mes?: number) => api.get('/iva/ventas', { params: { mes } }),
  registrarCompra: (data: unknown) => api.post('/iva/compras', data),
  registrarVenta: (data: unknown) => api.post('/iva/ventas', data),
  liquidacion: (mes?: number) => api.get('/iva/liquidacion', { params: { mes } }),
}

// ─── IGTF ──────────────────────────────────────────────────────────────────

export const igtfApi = {
  listar: () => api.get('/igtf/'),
  registrar: (data: unknown) => api.post('/igtf/', data),
}

// ─── Retenciones ───────────────────────────────────────────────────────────

export const retencionesApi = {
  listar: (mes?: number) => api.get('/retenciones/', { params: { mes } }),
  crear: (data: unknown) => api.post('/retenciones/', data),
  conceptos: () => api.get('/retenciones/conceptos'),
}

// ─── Utilidades ────────────────────────────────────────────────────────────

export function descargarBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}
