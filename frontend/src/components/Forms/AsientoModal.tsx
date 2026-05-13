import { useState, useEffect, useCallback } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { asientosApi, catalogoApi } from '@/services/api'
import { todayISO, extractError, fmtNum } from '@/utils'
import { Modal, CuadreBar, Field } from '@/components/Common'
import type { CatalogoCuenta } from '@/types'

interface Linea {
  cuenta_codigo: string
  debe: number
  haber: number
  descripcion?: string
}

interface Props {
  open: boolean
  onClose: () => void
  tipo?: 'asiento' | 'ajuste'
}

const TIPOS_AJUSTE = [
  { value: 'depr', label: 'Depreciación' },
  { value: 'prov', label: 'Provisión' },
  { value: 'difer', label: 'Diferimiento' },
  { value: 'otro', label: 'Otro' },
]

export default function AsientoModal({ open, onClose, tipo = 'asiento' }: Props) {
  const qc = useQueryClient()

  const [fecha, setFecha] = useState(todayISO())
  const [descripcion, setDescripcion] = useState('')
  const [referencia, setReferencia] = useState('')
  const [tipoAjuste, setTipoAjuste] = useState('depr')
  const [lineas, setLineas] = useState<Linea[]>([
    { cuenta_codigo: '', debe: 0, haber: 0 },
    { cuenta_codigo: '', debe: 0, haber: 0 },
  ])

  const { data: cuentas = [] } = useQuery<CatalogoCuenta[]>({
    queryKey: ['catalogo'],
    queryFn: () => catalogoApi.listar().then(r => r.data),
    enabled: open,
  })

  const { data: proximoNum } = useQuery({
    queryKey: ['proximo-num', tipo],
    queryFn: () => asientosApi.proximoNumero().then(r => r.data.numero),
    enabled: open,
  })

  const totalDebe = lineas.reduce((s, l) => s + (l.debe || 0), 0)
  const totalHaber = lineas.reduce((s, l) => s + (l.haber || 0), 0)
  const cuadra = Math.abs(totalDebe - totalHaber) < 0.01 && totalDebe > 0

  const mutation = useMutation({
    mutationFn: (data: unknown) =>
      tipo === 'asiento'
        ? asientosApi.crear(data)
        : import('@/services/api').then(m => m.ajustesApi.crear(data)),
    onSuccess: (_, vars: any) => {
      toast.success(`${tipo === 'asiento' ? 'Asiento' : 'Ajuste'} guardado ✓`)
      qc.invalidateQueries({ queryKey: tipo === 'asiento' ? ['asientos'] : ['ajustes'] })
      qc.invalidateQueries({ queryKey: ['estado-resultado'] })
      qc.invalidateQueries({ queryKey: ['proximo-num'] })
      handleClose()
    },
    onError: (err) => toast.error(extractError(err)),
  })

  const handleClose = useCallback(() => {
    setFecha(todayISO())
    setDescripcion('')
    setReferencia('')
    setLineas([
      { cuenta_codigo: '', debe: 0, haber: 0 },
      { cuenta_codigo: '', debe: 0, haber: 0 },
    ])
    onClose()
  }, [onClose])

  const addLinea = () => setLineas(prev => [...prev, { cuenta_codigo: '', debe: 0, haber: 0 }])

  const removeLinea = (i: number) => {
    if (lineas.length <= 2) return
    setLineas(prev => prev.filter((_, idx) => idx !== i))
  }

  const updateLinea = (i: number, field: keyof Linea, value: string | number) => {
    setLineas(prev => {
      const next = [...prev]
      next[i] = { ...next[i], [field]: value }
      return next
    })
  }

  const handleSave = () => {
    if (!cuadra) { toast.error('El asiento no cuadra'); return }
    const lineasValidas = lineas.filter(l => l.cuenta_codigo)
    if (lineasValidas.length < 2) { toast.error('Mínimo 2 líneas con cuenta'); return }

    const payload = tipo === 'asiento'
      ? { fecha, descripcion, referencia, lineas: lineasValidas }
      : { fecha, descripcion, referencia, tipo: tipoAjuste, lineas: lineasValidas }

    mutation.mutate(payload)
  }

  const cuentasOpts = cuentas.filter(c => c.tipo === 'Cuenta' && c.activa)

  const isAjuste = tipo === 'ajuste'
  const title = isAjuste ? 'Nuevo ajuste' : 'Nuevo asiento contable'

  return (
    <Modal
      open={open}
      onClose={handleClose}
      title={title}
      size="lg"
      footer={
        <>
          <button onClick={handleClose} className="btn-secondary">Cancelar</button>
          <button
            onClick={handleSave}
            disabled={!cuadra || mutation.isPending}
            className="btn-primary"
          >
            {mutation.isPending ? (
              <><i className="ti ti-loader-2 animate-spin" /> Guardando...</>
            ) : (
              <><i className="ti ti-check" /> Guardar {isAjuste ? 'ajuste' : 'asiento'}</>
            )}
          </button>
        </>
      }
    >
      <div className="space-y-4">
        {/* Header fields */}
        <div className="grid grid-cols-3 gap-3">
          <Field label="N° Correlativo">
            <input className="input bg-surface-50 text-surface-500" value={proximoNum ?? '...'} readOnly />
          </Field>
          <Field label="Fecha" required>
            <input type="date" className="input" value={fecha} onChange={e => setFecha(e.target.value)} />
          </Field>
          {isAjuste && (
            <Field label="Tipo de ajuste" required>
              <select className="input" value={tipoAjuste} onChange={e => setTipoAjuste(e.target.value)}>
                {TIPOS_AJUSTE.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
              </select>
            </Field>
          )}
          {!isAjuste && (
            <Field label="Referencia">
              <input className="input" placeholder="FAC-0001" value={referencia} onChange={e => setReferencia(e.target.value)} />
            </Field>
          )}
        </div>

        <Field label="Descripción">
          <input
            className="input"
            placeholder={isAjuste ? 'Ej: Depreciación mensual maquinaria' : 'Ej: Pago alquiler local industrial'}
            value={descripcion}
            onChange={e => setDescripcion(e.target.value)}
          />
        </Field>

        {/* Lineas */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <label className="label mb-0">Líneas del {isAjuste ? 'ajuste' : 'asiento'}</label>
            <button onClick={addLinea} className="btn-ghost btn-sm text-brand-600">
              <i className="ti ti-plus" /> Agregar línea
            </button>
          </div>

          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th className="w-[45%]">Cuenta</th>
                  <th className="w-[22%] text-right">Debe (Bs.)</th>
                  <th className="w-[22%] text-right">Haber (Bs.)</th>
                  <th className="w-[11%]"></th>
                </tr>
              </thead>
              <tbody>
                {lineas.map((linea, i) => (
                  <tr key={i}>
                    <td>
                      <select
                        className="input input-sm w-full"
                        value={linea.cuenta_codigo}
                        onChange={e => updateLinea(i, 'cuenta_codigo', e.target.value)}
                      >
                        <option value="">Seleccionar cuenta…</option>
                        {cuentasOpts.map(c => (
                          <option key={c.codigo} value={c.codigo}>
                            {c.codigo} — {c.nombre}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td>
                      <input
                        type="number"
                        min="0"
                        step="0.01"
                        className="input input-sm w-full text-right font-mono"
                        value={linea.debe || ''}
                        placeholder="0,00"
                        onChange={e => updateLinea(i, 'debe', parseFloat(e.target.value) || 0)}
                      />
                    </td>
                    <td>
                      <input
                        type="number"
                        min="0"
                        step="0.01"
                        className="input input-sm w-full text-right font-mono"
                        value={linea.haber || ''}
                        placeholder="0,00"
                        onChange={e => updateLinea(i, 'haber', parseFloat(e.target.value) || 0)}
                      />
                    </td>
                    <td className="text-center">
                      <button
                        onClick={() => removeLinea(i)}
                        disabled={lineas.length <= 2}
                        className="btn-icon text-surface-300 hover:text-danger disabled:opacity-30"
                      >
                        <i className="ti ti-trash text-sm" />
                      </button>
                    </td>
                  </tr>
                ))}
                {/* Totals row */}
                <tr className="bg-surface-50">
                  <td className="text-xs font-medium text-surface-500 text-right pr-2">TOTALES</td>
                  <td className="text-right font-mono font-semibold text-surface-900 text-sm">
                    {fmtNum(totalDebe)}
                  </td>
                  <td className="text-right font-mono font-semibold text-surface-900 text-sm">
                    {fmtNum(totalHaber)}
                  </td>
                  <td />
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        {/* Cuadre */}
        <CuadreBar debe={totalDebe} haber={totalHaber} />
      </div>
    </Modal>
  )
}
