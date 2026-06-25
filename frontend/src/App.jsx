import { Navigate, Route, Routes } from 'react-router-dom'
import AppLayout from './layouts/AppLayout'
import Dashboard from './pages/Dashboard'
import Results from './pages/Results'
import RunTest from './pages/RunTest'

export default function App() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="dashboard" element={<Dashboard />} />
        <Route path="run-test" element={<RunTest />} />
        <Route path="results" element={<Results />} />
      </Route>
    </Routes>
  )
}