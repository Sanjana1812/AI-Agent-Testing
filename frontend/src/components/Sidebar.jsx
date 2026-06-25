import { NavLink } from 'react-router-dom'

export default function Sidebar({ items }) {
  return (
    <aside className="flex w-64 flex-col border-r border-slate-200 bg-card">
      <div className="border-b border-slate-200 px-6 py-5">
        <p className="text-xs font-semibold uppercase tracking-wider text-primary">
          AI Testing
        </p>
        <h1 className="mt-1 text-lg font-semibold text-heading">Platform</h1>
      </div>

      <nav className="flex flex-1 flex-col gap-1 p-4">
        {items.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              [
                'rounded-lg px-4 py-2.5 text-sm font-medium transition-colors',
                isActive
                  ? 'bg-primary text-white'
                  : 'text-slate-600 hover:bg-slate-100 hover:text-heading',
              ].join(' ')
            }
          >
            {item.label}
          </NavLink>
        ))}
      </nav>
    </aside>
  )
}
