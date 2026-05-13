import { ReactNode, useEffect } from 'react'
import { MESES } from '@/utils'

// ─── Modal ────────────────────────────────────────────────────────────────

interface ModalProps {
  open: boolean
  onClose: () => void
  title: string
  children: ReactNode
  footer?: ReactNode
  size?: 'sm' | 'md' | 'lg' | 'xl'
}

const sizeMap = { sm: 'max-w-md', md: 'max-w-lg', lg: 'max-w-2xl', xl: 'max-w-4xl' }

export function Modal({ open, onClose, title, children, footer, size = 'md' }: ModalProps) {
  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    if (open) document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [open, onClose])

  if (!open) return null
  return (
    <div className="modal-overlay" onClick={e => { if (e.target === e.currentTarget) onClose() }}>
      <div className={`modal-box w-full ${sizeMap[size]}`} onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <h2 className="text-base font-semibold text-surface-900">{title}</h2>
          <button onClick={onClose} className="btn-icon text-surface-400 hover:text-surface-700">
            <i className="ti ti-x text-base" />
          </button>
        </div>
        <div className="modal-body">{children}</div>
        {footer && <div className="modal-footer">{footer}</div>}
      </div>
    </div>
  )
}

// ─── Page Header ─────────────────────────────────────────────────────────

interface PageHeaderProps {
  title: string
  subtitle?: string
  actions?: ReactNode
}

export function PageHeader({ title, subtitle, actions }: PageHeaderProps) {
  return (
    <div className="flex items-start justify-between mb-5">
      <div>
        <h1 className="text-xl font-bold font-display text-surface-900">{title}</h1>
        {subtitle && <p className="text-sm text-surface-500 mt-0.5">{subtitle}</p>}
      </div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </div>
  )
}

// ─── Empty State ─────────────────────────────────────────────────────────

export function EmptyState({ icon, message, action }: { icon: string; message: string; action?: ReactNode }) {
  return (
    <div className="empty-state">
      <i className={`ti ${icon}`} />
      <p className="mb-3">{message}</p>
      {action}
    </div>
  )
}

// ─── Loading Spinner ─────────────────────────────────────────────────────

export function Spinner({ size = 'md' }: { size?: 'sm' | 'md' | 'lg' }) {
  const s = { sm: 'text-base', md: 'text-2xl', lg: 'text-4xl' }[size]
  return (
    <div className="flex items-center justify-center py-12">
      <i className={`ti ti-loader-2 animate-spin text-brand-500 ${s}`} />
    </div>
  )
}

// ─── Mes Selector ─────────────────────────────────────────────────────────

export function MesSelector({
  mes, onChange
}: { mes: number | undefined; onChange: (v: number | undefined) => void }) {
  return (
    <select
      value={mes ?? ''}
      onChange={e => onChange(e.target.value ? Number(e.target.value) : undefined)}
      className="input input-sm w-40"
    >
      <option value="">Todos los meses</option>
      {MESES.map((m, i) => <option key={i} value={i + 1}>{m}</option>)}
    </select>
  )
}

// ─── Export Bar ───────────────────────────────────────────────────────────

interface ExportBarProps {
  onAdd?: () => void
  addLabel?: string
  onExcelExport?: () => void
  extraActions?: ReactNode
  count?: number
  countLabel?: string
}

export function ExportBar({
  onAdd, addLabel = 'Nuevo', onExcelExport, extraActions, count, countLabel
}: ExportBarProps) {
  return (
    <div className="flex items-center gap-2 mb-4 flex-wrap">
      {onAdd && (
        <button onClick={onAdd} className="btn-primary btn-sm">
          <i className="ti ti-plus" /> {addLabel}
        </button>
      )}
      {onExcelExport && (
        <button onClick={onExcelExport} className="btn-secondary btn-sm">
          <i className="ti ti-file-spreadsheet" /> Excel
        </button>
      )}
      {extraActions}
      {count !== undefined && (
        <span className="ml-auto text-xs text-surface-400">
          {count} {countLabel ?? 'registros'}
        </span>
      )}
    </div>
  )
}

// ─── Form Field ───────────────────────────────────────────────────────────

interface FieldProps {
  label: string
  error?: string
  required?: boolean
  children: ReactNode
}

export function Field({ label, error, required, children }: FieldProps) {
  return (
    <div>
      <label className="label">
        {label}{required && <span className="text-danger ml-0.5">*</span>}
      </label>
      {children}
      {error && <p className="text-xs text-danger mt-1">{error}</p>}
    </div>
  )
}

// ─── Cuadre Bar ───────────────────────────────────────────────────────────

export function CuadreBar({ debe, haber }: { debe: number; haber: number }) {
  const ok = Math.abs(debe - haber) < 0.01 && debe > 0
  const fmt = (n: number) => n.toLocaleString('es-VE', { minimumFractionDigits: 2 })
  return (
    <div className={ok ? 'cuadre-ok' : 'cuadre-fail'}>
      <div className="flex items-center justify-between">
        <span>
          <i className={`ti ${ok ? 'ti-check' : 'ti-alert-triangle'} mr-1.5`} />
          Debe: <strong>{fmt(debe)}</strong> | Haber: <strong>{fmt(haber)}</strong>
        </span>
        <span className="font-semibold">{ok ? 'CUADRA ✓' : 'NO CUADRA ✗'}</span>
      </div>
    </div>
  )
}

// ─── Table totals footer ──────────────────────────────────────────────────

export function TableFooter({ cols }: { cols: { label: string; value: string; color?: string }[] }) {
  return (
    <div className="flex items-center justify-end gap-6 px-4 py-3 bg-surface-50 border-t border-surface-200 rounded-b-xl">
      {cols.map(({ label, value, color }) => (
        <div key={label} className="text-sm">
          <span className="text-surface-500">{label}: </span>
          <span className={`font-mono font-semibold ${color ?? 'text-surface-900'}`}>{value}</span>
        </div>
      ))}
    </div>
  )
}
