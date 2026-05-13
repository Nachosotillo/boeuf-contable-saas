// ─── Formatters ────────────────────────────────────────────────────────────

export const fmtBs = (n: number | string | undefined): string => {
  const num = typeof n === 'string' ? parseFloat(n) : (n ?? 0)
  return 'Bs. ' + num.toLocaleString('es-VE', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

export const fmtNum = (n: number | string | undefined): string => {
  const num = typeof n === 'string' ? parseFloat(n) : (n ?? 0)
  return num.toLocaleString('es-VE', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

export const fmtPct = (n: number): string => `${(n * 100).toFixed(1)}%`

export const fmtDate = (d: string | undefined): string => {
  if (!d) return '—'
  return new Date(d + 'T00:00:00').toLocaleDateString('es-VE', {
    day: '2-digit', month: '2-digit', year: 'numeric'
  })
}

export const fmtDateISO = (d: Date): string => d.toISOString().split('T')[0]

export const todayISO = (): string => fmtDateISO(new Date())

export const MESES = [
  'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
  'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre',
]

export const mesActual = (): number => new Date().getMonth() + 1
export const anioActual = (): number => new Date().getFullYear()

// ─── Excel Export ──────────────────────────────────────────────────────────

export function exportarExcel(
  data: Record<string, unknown>[],
  filename: string,
  sheetName = 'Datos'
) {
  import('xlsx').then((XLSX) => {
    const ws = XLSX.utils.json_to_sheet(data)
    const wb = XLSX.utils.book_new()
    XLSX.utils.book_append_sheet(wb, ws, sheetName)
    XLSX.writeFile(wb, `${filename}_${todayISO()}.xlsx`)
  })
}

export function exportarExcelMultiHoja(
  sheets: { name: string; data: Record<string, unknown>[] }[],
  filename: string
) {
  import('xlsx').then((XLSX) => {
    const wb = XLSX.utils.book_new()
    sheets.forEach(({ name, data }) => {
      const ws = XLSX.utils.json_to_sheet(data)
      XLSX.utils.book_append_sheet(wb, ws, name)
    })
    XLSX.writeFile(wb, `${filename}_${todayISO()}.xlsx`)
  })
}

// ─── Clsx helper ───────────────────────────────────────────────────────────

export function cn(...classes: (string | undefined | null | false)[]): string {
  return classes.filter(Boolean).join(' ')
}

// ─── Error extractor ───────────────────────────────────────────────────────

export function extractError(err: unknown): string {
  if (err && typeof err === 'object' && 'response' in err) {
    const res = (err as { response: { data: { detail?: string | { msg: string }[] } } }).response
    const detail = res?.data?.detail
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail)) return detail.map(d => d.msg).join(', ')
  }
  return 'Ocurrió un error inesperado'
}

// ─── ISLR Cálculo local (misma lógica que backend) ─────────────────────────

export function calcularISLR(salario: number): number {
  if (salario <= 3000) return 0
  if (salario <= 5000) return (salario - 3000) * 0.06
  if (salario <= 10000) return 120 + (salario - 5000) * 0.09
  if (salario <= 15000) return 570 + (salario - 10000) * 0.12
  if (salario <= 20000) return 1170 + (salario - 15000) * 0.16
  return 1970 + (salario - 20000) * 0.34
}
