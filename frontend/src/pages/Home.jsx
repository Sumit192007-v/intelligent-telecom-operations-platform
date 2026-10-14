import React from 'react'
import { Link } from 'react-router-dom'
import SignalField from '../components/SignalField.jsx'
import './home-hero.css'

export default function Home() {
  return (
    <main className="home-page home-v2">
      <section className="hero">
        <div className="hero-copy">
          <h1>Catch network trouble before the complaints pile up</h1>
          <p>
            Customers report problems. Operators see which towers are slow,
            who is affected, and who should fix it.
          </p>
          <ul className="hero-legend" aria-label="Tower states">
            <li><i className="dot ok" />Healthy</li>
            <li><i className="dot slow" />Slow</li>
            <li><i className="dot down" />Down</li>
          </ul>
        </div>
        <SignalField />
      </section>

      <section className="routes" aria-label="Choose a workspace">
        <Link to="/customer" className="route route-customer">
          <h2>I'm a customer</h2>
          <p>Report a problem, follow its progress, and check network status near you.</p>
          <span className="route-go">Open customer workspace</span>
        </Link>
        <Link to="/company" className="route route-company">
          <h2>I run the network</h2>
          <p>Triage complaints, assign teams, and watch coverage and latency on the map.</p>
          <span className="route-go">Open operations workspace</span>
        </Link>
      </section>
    </main>
  )
}
