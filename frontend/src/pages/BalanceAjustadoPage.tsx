// BalanceAjustadoPage.tsx
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { reportesApi } from '@/services/api'
import { fmtBs, exportarExcel } from '@/utils'
import { PageHeader, ExportBar, MesSelector, Spinner, TableFooter } from '@/components/Common'
import type { BalanceAjustado } from '@/types'

export default function BalanceAjustadoPage() {
  const [mes, setMes] = useState<number | undefined>()
  const { data: balance, isLoading } = useQuery<BalanceAjustado>({
    queryKey: ['balance-ajustado', mes],
    queryFn: () => reportesApi.balanceAjustado(mes).then(r => r.data),
  })
  const handleExport = () => balance && exportarExcel(
    balance.lineas.map(l => ({ Código: l.codigo, Nombre: l.nombre, 'Debe BC': l.debe_bc, 'Haber BC': l.haber_bc, 'Aj. Debe': l.ajuste_debe, 'Aj. Haber': l.ajuste_haber, 'Saldo Deudor': l.saldo_ajustado_deudor, 'Saldo Acreedor': l.saldo_ajustado_acreedor })),
    'Balance_Ajustado'
  )
  return (
    <div>
      <PageHeader title="Balance Ajustado" subtitle="Balance de Comprobación + Ajustes del período"
        actions={balance && <span className={`badge ${balance.cuadra ? 'badge-green' : 'badge-red'}`}>{balance.cuadra ? '✓ Cuadra' : '✗ No cuadra'}</span>} />
      <ExportBar onExcelExport={handleExport} extraActions={<MesSelector mes={mes} onChange={setMes} />} count={balance?.lineas.length} />
      {isLoading ? <Spinner /> : balance && (
        <>
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Cód.</th><th>Cuenta</th>
                  <th className="text-right">Debe BC</th><th className="text-right">Haber BC</th>
                  <th className="text-right">Aj. Debe</th><th className="text-right">Aj. Haber</th>
                  <th className="text-right">Sdo. Ajust. Deudor</th><th className="text-right">Sdo. Ajust. Acreedor</th>
                </tr>
              </thead>
              <tbody>
                {balance.lineas.map(l => (
                  <tr key={l.codigo}>
                    <td className="font-mono text-xs">{l.codigo}</td>
                    <td className="max-w-[150px] truncate">{l.nombre}</td>
                    <td className="text-right font-mono text-xs">{l.debe_bc > 0 ? fmtBs(l.debe_bc) : ''}</td>
                    <td className="text-right font-mono text-xs">{l.haber_bc > 0 ? fmtBs(l.haber_bc) : ''}</td>
                    <td className="text-right font-mono text-xs text-brand-600">{l.ajuste_debe > 0 ? fmtBs(l.ajuste_debe) : ''}</td>
                    <td className="text-right font-mono text-xs text-amber-600">{l.ajuste_haber > 0 ? fmtBs(l.ajuste_haber) : ''}</td>
                    <td className="text-right font-mono text-xs font-semibold text-brand-700">{l.saldo_ajustado_deudor > 0 ? fmtBs(l.saldo_ajustado_deudor) : ''}</td>
                    <td className="text-right font-mono text-xs font-semibold text-danger">{l.saldo_ajustado_acreedor > 0 ? fmtBs(l.saldo_ajustado_acreedor) : ''}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <TableFooter cols={[{ label: 'Saldo Deudor Total', value: fmtBs(balance.total_deudor), color: 'text-brand-600' }, { label: 'Saldo Acreedor Total', value: fmtBs(balance.total_acreedor), color: 'text-danger' }]} />
        </>
      )}
    </div>
  )
}
