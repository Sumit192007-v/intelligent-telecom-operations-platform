import React from 'react'
import { Outlet, useLocation } from 'react-router-dom'
import Sidebar from './Sidebar.jsx'

function getSection(pathname) {
  if (pathname.startsWith('/customer')) return 'customer'
  if (pathname.startsWith('/company')) return 'company'
  return 'home'
}

export default function Layout() {
  const location = useLocation()
  const section = getSection(location.pathname)

  return (
    <div className="app-shell" data-section={section}>
      <Sidebar />
      <div className="app-content">
        <Outlet />
      </div>
    </div>
  )
}