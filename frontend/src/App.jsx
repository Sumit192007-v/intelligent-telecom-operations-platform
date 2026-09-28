import React from 'react'
import { Routes, Route } from 'react-router-dom'

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

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route element={<Layout />}>
        <Route path="/" element={<Home />} />
        <Route path="/customer" element={<CustomerDashboard />} />
        <Route path="/customer/complaint" element={<SubmitComplaint />} />
        <Route path="/customer/complaints" element={<MyComplaints />} />
        <Route path="/customer/status" element={<ComplaintStatus />} />
        <Route path="/customer/network" element={<NetworkStatus />} />
        <Route path="/company" element={<CompanyDashboard />} />
        <Route path="/company/complaints" element={<AllComplaints />} />
        <Route path="/company/assign" element={<AssignComplaint />} />
        <Route path="/company/departments" element={<DepartmentManagement />} />
        <Route path="/company/network" element={<NetworkInsights />} />
      </Route>
    </Routes>
  )
}