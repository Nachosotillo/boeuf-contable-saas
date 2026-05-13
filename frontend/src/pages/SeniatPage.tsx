// SeniatPage.tsx
import { useState } from 'react'
import toast from 'react-hot-toast'
import { seniatApi, descargarBlob } from '@/services/api'
import { MESES, mesActual, anioActual } from '@/utils'
import { PageHeader } from '@/components/Common'

interface ExportCard {
  title: string
  subtitle: string
  icon: string
  color: string
  endpoint: 'iva-ventas' | 'iva-compras' | 'islr' | 'igtf'
  base_legal: string
}

const EXPORTS: ExportCard[] = [
  { title: 'Libro IVA — Ventas', subtitle: 'IVA Débito Fiscal del período', icon: 'ti-file-invoice', color: 'text-brand-600 bg-brand-50 border-brand-200', endpoint: 'iva-ventas', base_legal: 'Art. 70-76 Ley IVA' },
  { title: 'Libro IVA — Compras', subtitle: 'IVA Crédito Fiscal del período', icon: 'ti-file-invoice', color: 'text-blue-600 bg-blue-50 border-blue-200', endpoint: 'iva-compras', base_legal: 'Art. 70-76 Ley IVA' },
  { title: 'Retenciones ISLR', subtitle: 'Comprobantes Decreto 1808', icon: 'ti-file-text', color: 'text-amber-600 bg-amber-50 border-amber-200', endpoint: 'islr', base_legal: 'Decreto 1808, Art. 9' },
  { title: 'IGTF', subtitle: 'Operaciones en divisas 3%', icon: 'ti-currency-dollar', color: 'text-purple-600 bg-purple-50 border-purple-200', endpoint: 'igtf', base_legal: 'Ley IGTF 2022, Art. 24' },
]

export default function SeniatPage() {
  const [mes, setMes] = useState(mesActual())
  const [anio, setAnio] = useState(anioActual())
  const [loading, setLoading] = useState<string | null>(null)

  const handleDownload = async (card: ExportCard) => {
    setLoading(card.endpoint)
    try {
      let res
      if (card.endpoint === 'iva-ventas') res = await seniatApi.exportarIvaVentas(mes, anio)
      else if (card.endpoint === 'iva-compras') res = await seniatApi.exportarIvaCompras(mes, anio)
      else if (card.endpoint === 'islr') res = await seniatApi.exportarIslr(mes, anio)
      else res = await seniatApi.exportarIgtf(mes, anio)
      const periodo = `${anio}${String(mes).padStart(2, '0')}`
      descargarBlob(res.data, `SENIAT_${card.endpoint.toUpperCase()}_${periodo}.txt`)
      toast.success(`${card.title} descargado ✓`)
    } catch {
      toast.error('Error al generar el archivo')
    } finally {
      setLoading(null)
    }
  }

  return (
    <div>
      <PageHeader title="Exportar SENIAT" subtitle="Genera archivos TXT en formato oficial para copiar en el portal de declaraciones" />

      {/* Periodo selector */}
      <div className="card p-4 mb-6 flex items-center gap-4">
        <i className="ti ti-calendar text-surface-400 text-xl" />
        <div>
          <div className="text-xs font-medium text-surface-500 mb-1">Período de declaración</div>
          <div className="flex items-center gap-2">
            <select className="input input-sm w-36" value={mes} onChange={e => setMes(Number(e.target.value))}>
              {MESES.map((m, i) => <option key={i} value={i + 1}>{m}</option>)}
            </select>
            <select className="input input-sm w-24" value={anio} onChange={e => setAnio(Number(e.target.value))}>
              {[anio - 1, anio, anio + 1].map(y => <option key={y} value={y}>{y}</option>)}
            </select>
            <span className="text-sm text-surface-500 ml-1">→ <strong>{MESES[mes - 1]} {anio}</strong></span>
          </div>
        </div>
        <div className="ml-auto flex items-center gap-2 text-xs text-surface-400">
          <i className="ti ti-info-circle" />
          <span>Los archivos .txt se descargan directamente</span>
        </div>
      </div>

      {/* Export cards */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {EXPORTS.map(card => (
          <div key={card.endpoint} className={`card p-5 border ${card.color.split(' ').find(c => c.startsWith('border-'))} hover:shadow-card-hover transition-shadow`}>
            <div className="flex items-start gap-4">
              <div className={`w-11 h-11 rounded-xl flex items-center justify-center flex-shrink-0 ${card.color.split(' ').filter(c => !c.startsWith('text-') && !c.startsWith('border-')).join(' ')}`}>
                <i className={`ti ${card.icon} text-xl ${card.color.split(' ').find(c => c.startsWith('text-'))}`} />
              </div>
              <div className="flex-1">
                <div className="font-semibold text-surface-900">{card.title}</div>
                <div className="text-sm text-surface-500 mt-0.5">{card.subtitle}</div>
                <div className="text-xs text-surface-400 mt-1">Base legal: {card.base_legal}</div>
              </div>
            </div>
            <button
              onClick={() => handleDownload(card)}
              disabled={loading === card.endpoint}
              className={`btn-primary w-full justify-center mt-4`}
            >
              {loading === card.endpoint ? (
                <><i className="ti ti-loader-2 animate-spin" /> Generando…</>
              ) : (
                <><i className="ti ti-download" /> Descargar TXT — {MESES[mes - 1]} {anio}</>
              )}
            </button>
          </div>
        ))}
      </div>

      {/* Instructions */}
      <div className="card p-5 mt-6 bg-surface-50">
        <div className="flex items-start gap-3">
          <i className="ti ti-bulb text-amber-500 text-xl mt-0.5" />
          <div>
            <div className="font-semibold text-surface-800 mb-2">Cómo usar los archivos TXT</div>
            <ol className="text-sm text-surface-600 space-y-1 list-decimal list-inside">
              <li>Descarga el archivo .txt para el período correspondiente</li>
              <li>Accede al portal SENIAT: <span className="font-mono text-xs bg-surface-200 px-1 rounded">declaraciones.seniat.gob.ve</span></li>
              <li>Selecciona la declaración correspondiente (IVA, ISLR, IGTF)</li>
              <li>Importa o copia el contenido del archivo en el portal</li>
              <li>Verifica los totales y confirma la declaración</li>
            </ol>
          </div>
        </div>
      </div>
    </div>
  )
}
