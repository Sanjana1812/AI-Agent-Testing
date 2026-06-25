import { useLocation } from 'react-router-dom'

const pageTitles = {
  '/dashboard': 'Dashboard',
  '/run-test': 'Run Test',
  '/results': 'Results',
}
export default function Topbar() {
  const { pathname } = useLocation()
  const title = pageTitles[pathname] || 'AI Testing Platform'

  return (
    <header className="border-b border-slate-200 bg-card px-6 py-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-heading">{title}</h2>
          <p className="text-sm text-slate-500">Enterprise test management</p>        </div>
        <div className="flex h-9 w-9 items-center justify-center rounded-full bg-primary text-sm font-semibold text-white">
          AT
        </div>
      </div>
    </header>
  )
}
