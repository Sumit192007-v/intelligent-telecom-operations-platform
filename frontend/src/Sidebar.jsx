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

function getEmployeeLinks(user, department) {
  const isManager =
    user?.role === 'manager' ||
    user?.role === 'admin' ||
    department === 'Operations'

  if (isManager) {
    return [
      { to: '/company', label: 'Operations Dashboard', end: true },
      { to: '/company/complaints', label: 'All Complaints' },
      { to: '/company/assign', label: 'Assign Complaint' },
      { to: '/company/departments', label: 'Departments' },
      { to: '/company/network', label: 'Network Insights' },
    ]
  }

  if (department === 'Network') {
    return [
      { to: '/company', label: 'Network Dashboard', end: true },
      { to: '/company/network', label: 'Network Insights' },
      { to: '/company/complaints', label: 'Network Complaints' },
    ]
  }

  if (department === 'Technical') {
    return [
      { to: '/company', label: 'Technical Dashboard', end: true },
      { to: '/company/complaints', label: 'Technical Complaints' },
      { to: '/company/assign', label: 'Assign Complaint' },
    ]
  }

  if (department === 'Billing') {
    return [
      { to: '/company', label: 'Billing Dashboard', end: true },
      { to: '/company/complaints', label: 'Billing Complaints' },
    ]
  }

  if (department === 'Customer Support') {
    return [
      { to: '/company', label: 'Support Dashboard', end: true },
      { to: '/company/complaints', label: 'Support Complaints' },
      { to: '/company/assign', label: 'Assign Complaint' },
    ]
  }

  return [
    { to: '/company', label: 'Dashboard', end: true },
    { to: '/company/complaints', label: 'Complaints' },
  ]
}

function linkClass({ isActive }) {
  return `sidebar-link${isActive ? ' active' : ''}`
}

export default function Sidebar() {
  const { user, isCustomer, isEmployee, department, logout } = useAuth()
  const navigate = useNavigate()

  function handleLogout() {
    logout()
    navigate('/login', { replace: true })
  }

  const employeeLinks = isEmployee ? getEmployeeLinks(user, department) : []
  const groupLabel =
    user?.role === 'manager' || user?.role === 'admin'
      ? 'Management'
      : department
      ? `${department} Department`
      : 'Company'

  return (
    <aside className="app-sidebar">
      <div className="sidebar-brand">
        <span className="sidebar-brand-mark">IT</span>
        <span className="sidebar-brand-name">Telecom Ops</span>
      </div>

      {user && (
        <div
          style={{
            padding: '10px 12px',
            marginBottom: '16px',
            background: 'rgba(255, 255, 255, 0.04)',
            borderRadius: '8px',
            border: '1px solid rgba(255, 255, 255, 0.08)',
          }}
        >
          <div
            style={{
              fontSize: '13px',
              fontWeight: 600,
              color: '#fff',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
            }}
            title={user.email}
          >
            {user.name || user.email}
          </div>
          <div
            style={{
              fontSize: '11px',
              color: '#60a5fa',
              textTransform: 'capitalize',
              marginTop: '2px',
            }}
          >
            {user.role ? user.role.replace('_', ' ') : 'User'}
            {department
              ? ` • ${department}`
              : isEmployee
              ? ' • Unassigned'
              : ''}
          </div>
          {isEmployee && !department && user.role !== 'manager' && user.role !== 'admin' && (
            <div
              style={{
                marginTop: '6px',
                fontSize: '10.5px',
                color: '#fbbf24',
                lineHeight: '1.3',
              }}
            >
              ⚠️ Dept not assigned
            </div>
          )}
        </div>
      )}

      <nav className="sidebar-nav">
        <NavLink to="/" end className={linkClass}>
          Home
        </NavLink>

        {isCustomer && (
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
        )}

        {isEmployee && (
          <div className="sidebar-group">
            <span className="sidebar-group-label">{groupLabel}</span>
            {employeeLinks.map((link) => (
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
        )}

        {user && (
          <button
            type="button"
            className="sidebar-link sidebar-sign-out"
            onClick={handleLogout}
          >
            Sign out
          </button>
        )}
      </nav>
    </aside>
  )
}