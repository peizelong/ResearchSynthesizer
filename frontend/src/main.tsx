import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import './index.css'
import AppLayout from './components/AppLayout'
import WorkbenchPage from './pages/WorkbenchPage'
import ArticlesPage from './pages/ArticlesPage'
import BatchesPage from './pages/BatchesPage'
import ThemesPage from './pages/ThemesPage'
import ThemeDetailPage from './pages/ThemeDetailPage'
import MonitorPage from './pages/MonitorPage'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter>
      <Routes>
        <Route element={<AppLayout />}>
          <Route index element={<Navigate to="/workbench" replace />} />
          <Route path="/workbench" element={<WorkbenchPage />} />
          <Route path="/articles" element={<ArticlesPage />} />
          <Route path="/batches" element={<BatchesPage />} />
          <Route path="/themes" element={<ThemesPage />} />
          <Route path="/themes/:id" element={<ThemeDetailPage />} />
          <Route path="/monitor" element={<MonitorPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  </React.StrictMode>,
)
