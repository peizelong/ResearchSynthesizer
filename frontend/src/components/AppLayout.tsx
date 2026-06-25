import { NavLink, Outlet } from 'react-router-dom'

const navItems = [
  { to: '/articles', label: '文章' },
  { to: '/batches', label: '研究批次' },
  { to: '/clusters', label: '聚类' },
  { to: '/monitor', label: '监控' },
]

export default function AppLayout() {
  return (
    <div className="min-h-screen flex flex-col">
      <header className="bg-white border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-6 py-3 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-lg font-semibold text-brand-700">Research Synthesizer</span>
            <span className="text-xs text-slate-400">v0.1</span>
          </div>
          <nav className="flex gap-1">
            {navItems.map(item => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  `px-3 py-1.5 rounded text-sm font-medium transition-colors ${
                    isActive
                      ? 'bg-brand-50 text-brand-700'
                      : 'text-slate-600 hover:bg-slate-100'
                  }`
                }
              >
                {item.label}
              </NavLink>
            ))}
          </nav>
        </div>
      </header>
      <main className="flex-1 max-w-7xl mx-auto w-full px-6 py-6">
        <Outlet />
      </main>
      <footer className="border-t border-slate-200 bg-white">
        <div className="max-w-7xl mx-auto px-6 py-3 text-xs text-slate-400">
          Research Synthesizer · Phase 1 MVP
        </div>
      </footer>
    </div>
  )
}
