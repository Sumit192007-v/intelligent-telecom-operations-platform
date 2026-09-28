import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { getComplaintSummary } from '../../services/api'

function CompanyDashboard() {
  const [summary, setSummary] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    async function loadSummary() {
      try {
        const data = await getComplaintSummary()
        setSummary(data)
      } catch (err) {
        setError('Unable to load complaint summary')
      } finally {
        setLoading(false)
      }
    }

    loadSummary()
  }, [])

  if (loading) {
    return <div className="complaints-page">Loading dashboard...</div>
  }

  if (error) {
    return <div className="complaints-page complaints-error">{error}</div>
  }

  return (
    <div className="complaints-page">
      <div className="complaints-header">
        <div>
          <h1>Company Dashboard</h1>
          <p>Overview of current telecom operations.</p>
        </div>
      </div>

      <div className="dashboard-stats">
        <div className="dashboard-stat-card">
          <span>Total Complaints</span>
          <strong>{summary.total}</strong>
        </div>

        <div className="dashboard-stat-card">
          <span>Pending</span>
          <strong>{summary.pending}</strong>
        </div>

        <div className="dashboard-stat-card">
          <span>Assigned</span>
          <strong>{summary.assigned}</strong>
        </div>

        <div className="dashboard-stat-card">
          <span>In Progress</span>
          <strong>{summary.in_progress}</strong>
        </div>

        <div className="dashboard-stat-card">
          <span>Resolved</span>
          <strong>{summary.resolved}</strong>
        </div>

        <div className="dashboard-stat-card">
          <span>Closed</span>
          <strong>{summary.closed}</strong>
        </div>
      </div>

      <div className="company-actions">
        <h2>Operations</h2>

        <div className="company-action-grid">
          <Link to="/company/complaints" className="company-action-card">
            <h3>All Complaints</h3>
            <p>View and manage all customer complaints.</p>
          </Link>

          <Link to="/company/assign" className="company-action-card">
            <h3>Assign Complaint</h3>
            <p>Assign complaints to support agents or engineers.</p>
          </Link>

          <Link to="/company/departments" className="company-action-card">
            <h3>Departments</h3>
            <p>Manage complaint departments and teams.</p>
          </Link>

          <Link to="/company/network" className="company-action-card">
            <h3>Network Insights</h3>
            <p>View network measurements and ML predictions.</p>
          </Link>
        </div>
      </div>
    </div>
  )
}

export default CompanyDashboard