import React from 'react'
import { NavLink } from 'react-router-dom'

const ICONS = {
  home: 'M3 11l9-8 9 8M5 10v10h14V10',
  grid: 'M4 4h7v7H4zM13 4h7v7h-7zM4 13h7v7H4zM13 13h7v7h-7z',
  plus: 'M12 5v14M5 12h14',
  list: 'M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01',
  pulse: 'M22 12h-4l-3 9L9 3l-3 9H2',
  signal: 'M5 12.5a10 10 0 0 1 14 0M8.5 16a5 5 0 0 1 7 0M12 20h.01',
  inbox: 'M22 12h-6l-2 3h-4l-2-3H2M5.5 5h13L22 12v6a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2v-6z',
  userPlus: 'M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM19 8v6M22 11h-6',
  building: 'M3 21h18M5 21V7l7-4 7 4v14M9 9h.01M9 13h.01M9 17h.01M15 9h.01M15 13h.01M15 17h.01',
  chart: 'M18 20V10M12 20V4M6 20v-6',
}

const customerLinks = [
  { to: '/customer', label: 'Dashboard', end: true, icon: 'grid', color: '#38bdf8' },
  { to: '/customer/complaint', label: 'Submit Complaint', icon: 'plus', color: '#34d399' },
  { to: '/customer/complaints', label: 'My Complaints', icon: 'list', color: '#fbbf24' },
  { to: '/customer/status', label: 'Complaint Status', icon: 'pulse', color: '#f472b6' },
  { to: '/customer/network', label: 'Network Status', icon: 'signal', color: '#2dd4bf' },
]

const companyLinks = [
  { to: '/company', label: 'Dashboard', end: true, icon: 'grid', color: '#818cf8' },
  { to: '/company/complaints', label: 'All Complaints', icon: 'inbox', color: '#fb923c' },
  { to: '/company/assign', label: 'Assign Complaint', icon: 'userPlus', color: '#a78bfa' },
  { to: '/company/departments', label: 'Departments', icon: 'building', color: '#f472b6' },
  { to: '/company/network', label: 'Network Insights', icon: 'chart', color: '#22d3ee' },
]

function linkClass({ isActive }) {
  return `sidebar-link${isActive ? ' active' : ''}`
}

function Item({ link }) {
  return (
    <NavLink
      to={link.to}
      end={link.end}
      className={linkClass}
      style={{ '--c': link.color }}
    >
      <span className="sidebar-ico" aria-hidden="true">
        <svg viewBox="0 0 24 24"><path d={ICONS[link.icon]} /></svg>
      </span>
      {link.label}
    </NavLink>
  )
}

export default function Sidebar() {
  return (
    <aside className="app-sidebar">
      <div className="sidebar-brand">
        <span className="sidebar-brand-mark">IT</span>
        <span className="sidebar-brand-name">Telecom Ops</span>
      </div>

      <nav className="sidebar-nav">
        <Item link={{ to: '/', label: 'Home', end: true, icon: 'home', color: '#22d3ee' }} />

        <div className="sidebar-group">
          <span className="sidebar-group-label">Customer</span>
          {customerLinks.map((link) => <Item key={link.to} link={link} />)}
        </div>

        <div className="sidebar-group">
          <span className="sidebar-group-label">Company</span>
          {companyLinks.map((link) => <Item key={link.to} link={link} />)}
        </div>
      </nav>
    </aside>
  )
}
