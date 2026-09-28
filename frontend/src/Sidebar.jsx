import React from 'react'
import { NavLink } from 'react-router-dom'

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
      </nav>
    </aside>
  )
}