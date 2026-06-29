import { NavLink, Outlet } from 'react-router-dom'

const navItems = [
  { to: '/workbench', label: '叙事雷达' },
  { to: '/articles', label: '文章池' },
  { to: '/batches', label: '研究批次' },
  { to: '/themes', label: '融合主题' },
  { to: '/monitor', label: '监控' },
]

export default function AppLayout() {
  return (
    <div className="min-h-screen bg-slate-50 text-slate-800">
      <div className="flex min-h-screen">
        <aside className="hidden w-56 shrink-0 border-r border-slate-200 bg-white lg:flex lg:flex-col">
          <div className="border-b border-slate-100 px-5 py-4">
            <div className="text-base font-semibold text-slate-950">Narrative Synthesizer</div>
            <div className="mt-1 text-xs text-slate-400">投研叙事融合工作台</div>
          </div>
          <nav className="flex-1 space-y-1 px-3 py-4">
            {navItems.map(item => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  `flex items-center rounded-md px-3 py-2 text-sm font-medium transition-colors ${
                    isActive
                      ? 'bg-brand-50 text-brand-700'
                      : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'
                  }`
                }
              >
                {item.label}
              </NavLink>
            ))}
          </nav>
          <div className="border-t border-slate-100 px-5 py-4 text-xs text-slate-400">
            v0.2 · Workflow MVP
          </div>
        </aside>

        <div className="flex min-w-0 flex-1 flex-col">
          <header className="border-b border-slate-200 bg-white px-4 py-3 lg:hidden">
            <div className="font-semibold text-slate-950">Narrative Synthesizer</div>
            <nav className="mt-3 flex gap-1 overflow-x-auto">
              {navItems.map(item => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  className={({ isActive }) =>
                    `whitespace-nowrap rounded px-3 py-1.5 text-sm font-medium ${
                      isActive ? 'bg-brand-50 text-brand-700' : 'text-slate-600'
                    }`
                  }
                >
                  {item.label}
                </NavLink>
              ))}
            </nav>
          </header>
          <main className="min-w-0 flex-1 px-4 py-4 lg:px-5">
            <Outlet />
          </main>
        </div>
      </div>
    </div>
  )
}
