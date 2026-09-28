import React from 'react'
import { Link } from 'react-router-dom'

export default function NetworkStatus() {
  return (
    <main className="dashboard-page">
      <header className="dashboard-header">
        <Link to="/customer">← Back to Customer Dashboard</Link>

        <h1>Network Status</h1>
        <p>View your current network and service information.</p>
      </header>

      <section className="dashboard-cards">

        <article className="dashboard-card">
          <h2>Network Availability</h2>
          <p>Network service information will appear here.</p>
          <strong>Available</strong>
        </article>

        <article className="dashboard-card">
          <h2>Connection Quality</h2>
          <p>Current connection quality information.</p>
          <strong>Monitoring</strong>
        </article>

        <article className="dashboard-card">
          <h2>Service Issues</h2>
          <p>Check whether there are known network issues in your area.</p>
          <strong>No reported issue</strong>
        </article>

        <article className="dashboard-card">
          <h2>Latency Prediction</h2>
          <p>ML-based network latency prediction will appear here.</p>
          <strong>Coming from ML service</strong>
        </article>

      </section>
    </main>
  )
}