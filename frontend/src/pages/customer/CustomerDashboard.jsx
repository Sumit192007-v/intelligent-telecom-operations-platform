import React from 'react'
import { Link } from 'react-router-dom'

export default function CustomerDashboard() {
    return (
        <main className="dashboard-page">
            <header className="dashboard-header">
                <Link to="/">← Back to Home</Link>

                <h1>Customer Dashboard</h1>
                <p>Manage your telecom service complaints and issues.</p>
            </header>

            <section className="dashboard-cards">

                <Link to="/customer/complaint" className="dashboard-card">
                    <h2>Submit Complaint</h2>
                    <p>Report a network, service, billing, or technical issue.</p>
                </Link>

                <Link to="/customer/complaints" className="dashboard-card">
                    <h2>My Complaints</h2>
                    <p>View the complaints you have submitted.</p>
                </Link>

                <Link to="/customer/status" className="dashboard-card">
                    <h2>Complaint Status</h2>
                    <p>Track the progress of your reported issues.</p>
                </Link>

                <Link to="/customer/network" className="dashboard-card">
  <h2>Network Status</h2>
  <p>View available network and service information.</p>
</Link>

            </section>
        </main>
    )
}