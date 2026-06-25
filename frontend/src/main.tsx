import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import './index.css'
import AppLayout from './components/AppLayout'
import ArticlesPage from './pages/ArticlesPage'
import BatchesPage from './pages/BatchesPage'
import ClustersPage from './pages/ClustersPage'
import ClusterDetailPage from './pages/ClusterDetailPage'
import MonitorPage from './pages/MonitorPage'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter>
      <Routes>
        <Route element={<AppLayout />}>
          <Route index element={<Navigate to="/articles" replace />} />
          <Route path="/articles" element={<ArticlesPage />} />
          <Route path="/batches" element={<BatchesPage />} />
          <Route path="/clusters" element={<ClustersPage />} />
          <Route path="/clusters/:id" element={<ClusterDetailPage />} />
          <Route path="/monitor" element={<MonitorPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  </React.StrictMode>,
)
