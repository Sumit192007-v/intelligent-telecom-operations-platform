import React from 'react'
import { Navigate, Routes, Route } from 'react-router-dom'
import { useAuth } from './AuthContext.jsx'

import Layout from './Layout.jsx'
import Home from './pages/Home.jsx'
import CustomerDashboard from './pages/customer/CustomerDashboard.jsx'
import CompanyDashboard from './pages/company/CompanyDashboard.jsx'
import SubmitComplaint from './pages/customer/SubmitComplaint.jsx'
import MyComplaints from './pages/customer/MyComplaints.jsx'
import ComplaintStatus from './pages/customer/ComplaintStatus.jsx'
import NetworkStatus from './pages/customer/NetworkStatus.jsx'
import AllComplaints from './pages/company/AllComplaints.jsx'
import AssignComplaint from './pages/company/AssignComplaint.jsx'
import DepartmentManagement from './pages/company/DepartmentManagement.jsx'
import NetworkInsights from './pages/company/NetworkInsights.jsx'
import Login from './pages/Login.jsx'
import InteractiveBackground from './components/InteractiveBackground.jsx'

function ProtectedLayout({ role }) {
  const { token, user, sessionReady } = useAuth()

  if (!sessionReady) return <main>Checking session...</main>
  if (!token || !user) return <Navigate to="/login" replace />
  if (user.role !== role) {
    return (
      <Navigate
        to={user.role === 'customer' ? '/customer' : '/company'}
        replace
      />
    )
  }
  return <Layout />
}

function LoginRoute() {
  const { token, user, sessionReady } = useAuth()

  if (!sessionReady) return <main>Checking session...</main>
  if (token && user) {
    return (
      <Navigate
        to={user.role === 'customer' ? '/customer' : '/company'}
        replace
      />
    )
  }
  return <Login />
}

export default function App() {
  return (
    <>
      <InteractiveBackground />
      <Routes>
        <Route path="/login" element={<LoginRoute />} />
        <Route element={<Layout />}>
          <Route path="/" element={<Home />} />
        </Route>
        <Route element={<ProtectedLayout role="customer" />}>
          <Route path="/customer" element={<CustomerDashboard />} />
          <Route path="/customer/complaint" element={<SubmitComplaint />} />
          <Route path="/customer/complaints" element={<MyComplaints />} />
          <Route path="/customer/status" element={<ComplaintStatus />} />
          <Route path="/customer/network" element={<NetworkStatus />} />
        </Route>
        <Route element={<ProtectedLayout role="staff" />}>
          <Route path="/company" element={<CompanyDashboard />} />
          <Route path="/company/complaints" element={<AllComplaints />} />
          <Route path="/company/assign" element={<AssignComplaint />} />
          <Route path="/company/departments" element={<DepartmentManagement />} />
          <Route path="/company/network" element={<NetworkInsights />} />
        </Route>
      </Routes>
    </>
  )
}