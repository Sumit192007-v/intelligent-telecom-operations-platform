import React from 'react'
import { NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from './AuthContext.jsx'

const customerLinks = [
  { to: '/customer', label: 'Dashboard', end: true },
  { to: '/customer/complaint', label: 'Submit Complaint' },
  { to: '/customer/complaints', label: 'My Complaints' },
  { to: '/customer/status', label: 'Complaint Status' },
  { to: '/customer/network', label: 'Network Status' },
]

const companyLinks = [
  { to: '/company', label: 'Dashboard', end: true },
  { to: '/company/complaints', label: 'All Complaints' },
  { to: '/company/assign', label: 'Assign Complaint' },
  { to: '/company/departments', label: 'Departments' },
  { to: '/company/network', label: 'Network Insights' },
]

function linkClass({ isActive }) {
  return `sidebar-link${isActive ? ' active' : ''}`
}

export default function Sidebar() {
  const { logout } = useAuth()
  const navigate = useNavigate()

  function handleLogout() {
    logout()
    navigate('/login', { replace: true })
  }

  return (
    <aside className="app-sidebar">
      <div className="sidebar-brand">
        <span className="sidebar-brand-mark">IT</span>
        <span className="sidebar-brand-name">Telecom Ops</span>
      </div>

      <nav className="sidebar-nav">
        <NavLink to="/" end className={linkClass}>
          Home
        </NavLink>

        <div className="sidebar-group">
          <span className="sidebar-group-label">Customer</span>
          {customerLinks.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              end={link.end}
              className={linkClass}
            >
              {link.label}
            </NavLink>
          ))}
        </div>

        <div className="sidebar-group">
          <span className="sidebar-group-label">Company</span>
          {companyLinks.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              end={link.end}
              className={linkClass}
            >
              {link.label}
            </NavLink>
          ))}
        </div>
        <button
          type="button"
          className="sidebar-link sidebar-sign-out"
          onClick={handleLogout}
        >
          Sign out
        </button>
      </nav>
    </aside>
  )
}