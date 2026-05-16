// ─── DiarioPage.tsx ─────────────────────────────────────────────────────────
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { asientosApi } from '@/services/api'
import { fmtBs, fmtDate, extractError } from '@/utils'
import { PageHeader, ExportBar, MesSelector, EmptyState, Spinner } from '@/components/Common'
import AsientoModal from '@/components/Forms/AsientoModal'
import type { AsientoOut } from '@/types'

// ─── Exportación formato diario contable venezolano ──────────────────────────
// Columnas: Fecha | Código | Cuenta | Descripción | Debe | Haber
// Cada asiento ocupa tantas filas como líneas tenga.
// La fecha y descripción solo aparecen en la primera línea del asiento.
// Al final de cada asiento se agrega una fila de subtotales.
// Al final del libro se agrega una fila de TOTALES GENERALES.

function exportarDiario(asientos: AsientoOut[], filename: string) {
  import('xlsx').then((XLSX) => {
    const filas: Record<string, unknown>[] = []

    let totalDebeGeneral = 0
    let totalHaberGeneral = 0

    for (const a of asientos) {
      const lineas = a.lineas ?? []
      let subtotalDebe = 0
      let subtotalHaber = 0

      lineas.forEach((l, idx) => {
        const debe  = Number(l.debe)  || 0
        const haber = Number(l.haber) || 0
        subtotalDebe  += debe
        subtotalHaber += haber

        filas.push({
          'Fecha':       idx === 0 ? a.fecha : '',          // solo primera línea
          'N° Asiento':  idx === 0 ? a.numero_asiento : '',
          'Código':      l.cuenta_codigo ?? '',
          'Cuenta':      l.cuenta_nombre ?? '',
          'Descripción': idx === 0 ? (a.descripcion ?? '') : '',
          'Debe':        debe  > 0 ? debe  : '',
          'Haber':       haber > 0 ? haber : '',
        })
      })

      // Fila de subtotal por asiento
      filas.push({
        'Fecha':       '',
        'N° Asiento':  '',
        'Código':      '',
        'Cuenta':      `SUBTOTAL ${a.numero_asiento}`,
        'Descripción': a.cuadra ? 'Cuadra ✓' : 'No cuadra ✗',
        'Debe':        subtotalDebe,
        'Haber':       subtotalHaber,
      })

      // Fila en blanco separadora
      filas.push({ 'Fecha': '', 'N° Asiento': '', 'Código': '', 'Cuenta': '', 'Descripción': '', 'Debe': '', 'Haber': '' })

      totalDebeGeneral  += subtotalDebe
      totalHaberGeneral += subtotalHaber
    }

    // Fila de totales generales
    filas.push({
      'Fecha':       '',
      'N° Asiento':  '',
      'Código':      '',
      'Cuenta':      'TOTALES GENERALES',
      'Descripción': '',
      'Debe':        totalDebeGeneral,
      'Haber':       totalHaberGeneral,
    })

    const ws = XLSX.utils.json_to_sheet(filas, {
      header: ['Fecha', 'N° Asiento', 'Código', 'Cuenta', 'Descripción', 'Debe', 'Haber'],
    })

    // ── Ancho de columnas ────────────────────────────────────────────────────
    ws['!cols'] = [
      { wch: 12 },  // Fecha
      { wch: 10 },  // N° Asiento
      { wch: 12 },  // Código
      { wch: 40 },  // Cuenta
      { wch: 35 },  // Descripción
      { wch: 14 },  // Debe
      { wch: 14 },  // Haber
    ]

    // ── Formato numérico para columnas Debe y Haber (F y G) ─────────────────
    const range = XLSX.utils.decode_range(ws['!ref'] ?? 'A1')
    for (let R = 1; R <= range.e.r; R++) {
      for (const col of ['F', 'G']) {
        const cell = ws[`${col}${R + 1}`]
        if (cell && typeof cell.v === 'number') {
          cell.z = '#,##0.00'
        }
      }
    }

    const wb = XLSX.utils.book_new()
    XLSX.utils.book_append_sheet(wb, ws, 'Diario General')

    const today = new Date().toISOString().split('T')[0]
    XLSX.writeFile(wb, `${filename}_${today}.xlsx`)
  })
}

// ─── Componente ──────────────────────────────────────────────────────────────

export function DiarioPage() {
  const [open, setOpen] = useState(false)
  const [mes, setMes] = useState<number | undefined>()
  const [expanded, setExpanded] = useState<number | null>(null)
  const qc = useQueryClient()

  const { data: asientos = [], isLoading } = useQuery<AsientoOut[]>({
    queryKey: ['asientos', mes],
    queryFn: () => asientosApi.listar({ mes }).then(r => r.data),
  })

  const reversar = useMutation({
    mutationFn: (id: number) => asientosApi.reversar(id),
    onSuccess: () => { toast.success('Asiento reversado'); qc.invalidateQueries({ queryKey: ['asientos'] }) },
    onError: (err) => toast.error(extractError(err)),
  })

  const handleExport = () => {
    if (!asientos.length) return toast.error('No hay asientos para exportar')
    exportarDiario(asientos, 'Diario_General')
  }

  return (
    <div>
      <PageHeader
        title="Diario General"
        subtitle="Registro de asientos contables"
        actions={
          <button onClick={() => setOpen(true)} className="btn-primary">
            <i className="ti ti-plus" /> Nuevo asiento
          </button>
        }
      />

      <ExportBar
        onExcelExport={handleExport}
        extraActions={<MesSelector mes={mes} onChange={setMes} />}
        count={asientos.length}
        countLabel="asientos"
      />

      {isLoading ? <Spinner /> : (
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>N°</th>
                <th>Fecha</th>
                <th>Descripción</th>
                <th>Referencia</th>
                <th className="text-right">Total Debe</th>
                <th className="text-right">Total Haber</th>
                <th>Estado</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {asientos.length ? asientos.map(a => (
                <>
                  <tr
                    key={a.id}
                    onClick={() => setExpanded(expanded === a.id ? null : a.id)}
                    className="cursor-pointer"
                  >
                    <td><span className="font-mono font-medium text-surface-900">{a.numero_asiento}</span></td>
                    <td className="font-mono text-xs">{fmtDate(a.fecha)}</td>
                    <td className="max-w-[200px] truncate">{a.descripcion || <span className="text-surface-400">—</span>}</td>
                    <td className="text-surface-400 text-xs">{a.referencia || '—'}</td>
                    <td className="text-right font-mono">{fmtBs(a.total_debe)}</td>
                    <td className="text-right font-mono">{fmtBs(a.total_haber)}</td>
                    <td>
                      <span className={`badge ${a.cuadra ? 'badge-green' : 'badge-red'}`}>
                        {a.cuadra ? '✓ Cuadra' : '✗ Error'}
                      </span>
                    </td>
                    <td>
                      <div className="flex gap-1">
                        <button
                          className="btn-icon text-surface-400 hover:text-brand-500"
                          onClick={e => { e.stopPropagation(); setExpanded(expanded === a.id ? null : a.id) }}
                        >
                          <i className={`ti ${expanded === a.id ? 'ti-chevron-up' : 'ti-chevron-down'}`} />
                        </button>
                        <button
                          className="btn-icon text-surface-400 hover:text-danger"
                          title="Reversar"
                          onClick={e => { e.stopPropagation(); if (confirm('¿Reversar asiento?')) reversar.mutate(a.id) }}
                        >
                          <i className="ti ti-rotate" />
                        </button>
                      </div>
                    </td>
                  </tr>

                  {expanded === a.id && (
                    <tr key={`exp-${a.id}`} className="bg-surface-50">
                      <td colSpan={8} className="px-4 py-3">
                        <div className="text-xs font-semibold text-surface-500 mb-2">LÍNEAS DEL ASIENTO</div>
                        <table className="w-full text-xs">
                          <thead>
                            <tr className="text-surface-400">
                              <th className="text-left pb-1">Código</th>
                              <th className="text-left pb-1">Cuenta</th>
                              <th className="text-right pb-1">Debe</th>
                              <th className="text-right pb-1">Haber</th>
                            </tr>
                          </thead>
                          <tbody>
                            {(a.lineas ?? []).map(l => (
                              <tr key={l.id}>
                                <td className="font-mono py-0.5 pr-3">{l.cuenta_codigo}</td>
                                <td className="py-0.5 pr-3 text-surface-700">{l.cuenta_nombre}</td>
                                <td className="text-right font-mono py-0.5 pr-3">{l.debe > 0 ? fmtBs(l.debe) : ''}</td>
                                <td className="text-right font-mono py-0.5">{l.haber > 0 ? fmtBs(l.haber) : ''}</td>
                              </tr>
                            ))}
                            {/* Subtotal inline */}
                            <tr className="border-t border-surface-200 font-semibold text-surface-700">
                              <td colSpan={2} className="pt-1 text-right pr-3 text-surface-400 font-normal">Subtotales</td>
                              <td className="text-right font-mono pt-1 pr-3">{fmtBs(a.total_debe)}</td>
                              <td className="text-right font-mono pt-1">{fmtBs(a.total_haber)}</td>
                            </tr>
                          </tbody>
                        </table>
                      </td>
                    </tr>
                  )}
                </>
              )) : (
                <tr>
                  <td colSpan={8}>
                    <EmptyState
                      icon="ti-notebook"
                      message="Sin asientos. Crea el primero."
                      action={<button onClick={() => setOpen(true)} className="btn-primary btn-sm">Nuevo asiento</button>}
                    />
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      <AsientoModal open={open} onClose={() => setOpen(false)} tipo="asiento" />
    </div>
  )
}

export default DiarioPage
