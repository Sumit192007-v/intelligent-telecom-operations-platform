import React from 'react'
import { Link } from 'react-router-dom'

export default function Home() {
  return (
    <main className="home-page">
      <header className="home-header">
        <h1>Intelligent Telecom Operations Platform</h1>
        <p>Smart network operations and complaint management</p>
        <Link to="/login">Staff sign in</Link>
      </header>

      <section className="role-selection">
        <h2>How would you like to continue?</h2>

        <div className="role-cards">
          <Link to="/customer" className="role-card">
            <h3>Customer</h3>
            <p>
              Submit complaints, track service issues, and monitor complaint
              status.
            </p>
            <span>Continue as Customer →</span>
          </Link>

          <Link to="/company" className="role-card">
            <h3>Company</h3>
            <p>
              Manage complaints, assign departments, track issues, and monitor
              network operations.
            </p>
            <span>Continue as Company →</span>
          </Link>
        </div>
      </section>
    </main>
  )
}