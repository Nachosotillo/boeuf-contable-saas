import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from '@/contexts/AuthContext'
import Layout from '@/components/Layout/Layout'
import LoginPage from '@/pages/LoginPage'
import DashboardPage from '@/pages/DashboardPage'
import DiarioPage from '@/pages/DiarioPage'
import AjustesPage from '@/pages/AjustesPage'
import CatalogoPage from '@/pages/CatalogoPage'
import MayorPage from '@/pages/MayorPage'
import BalancePage from '@/pages/BalancePage'
import BalanceAjustadoPage from '@/pages/BalanceAjustadoPage'
import EstadoResultadoPage from '@/pages/EstadoResultadoPage'
import SituacionFinancieraPage from '@/pages/SituacionFinancieraPage'
import IvaPage from '@/pages/IvaPage'
import IgtfPage from '@/pages/IgtfPage'
import RetencionesPage from '@/pages/RetencionesPage'
import NominaPage from '@/pages/NominaPage'
import ProvisionesPage from '@/pages/ProvisionesPage'
import InventarioPage from '@/pages/InventarioPage'
import ActivosPage from '@/pages/ActivosPage'
import SeniatPage from '@/pages/SeniatPage'

function RequireAuth({ children }: { children: JSX.Element }) {
  const { isAuthenticated } = useAuth()
  return isAuthenticated ? children : <Navigate to="/login" replace />
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/" element={<RequireAuth><Layout /></RequireAuth>}>
            <Route index element={<Navigate to="/dashboard" replace />} />
            <Route path="dashboard" element={<DashboardPage />} />
            <Route path="diario" element={<DiarioPage />} />
            <Route path="ajustes" element={<AjustesPage />} />
            <Route path="catalogo" element={<CatalogoPage />} />
            <Route path="mayor" element={<MayorPage />} />
            <Route path="balance" element={<BalancePage />} />
            <Route path="balance-ajustado" element={<BalanceAjustadoPage />} />
            <Route path="resultado" element={<EstadoResultadoPage />} />
            <Route path="situacion" element={<SituacionFinancieraPage />} />
            <Route path="iva" element={<IvaPage />} />
            <Route path="igtf" element={<IgtfPage />} />
            <Route path="retenciones" element={<RetencionesPage />} />
            <Route path="nomina" element={<NominaPage />} />
            <Route path="provisiones" element={<ProvisionesPage />} />
            <Route path="inventario" element={<InventarioPage />} />
            <Route path="activos" element={<ActivosPage />} />
            <Route path="seniat" element={<SeniatPage />} />
          </Route>
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  )
}
