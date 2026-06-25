import { Outlet } from 'react-router-dom'
import Sidebar from '../components/Sidebar'
import Topbar from '../components/Topbar'

const navItems = [
  { to: '/dashboard', label: 'Dashboard' },
  { to: '/run-test', label: 'Run Test' },
  { to: '/results', label: 'Results' },
]
export default function AppLayout() {
  return (
    <div className="flex min-h-screen bg-background">
      <Sidebar items={navItems} />
      <div className="flex flex-1 flex-col">
        <Topbar />
        <main className="flex-1 p-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
