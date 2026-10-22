import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { getComplaintSummary } from '../../services/api'
import { useAuth } from '../../AuthContext'

function getDashboardDetails(user, department) {
  const isManager =
    user?.role === 'manager' ||
    user?.role === 'admin' ||
    department === 'Operations'

  if (isManager) {
    return {
      title: 'Executive Operations Dashboard',
      subtitle: 'Comprehensive telecom operations overview across all departments.',
      actions: [
        {
          to: '/company/complaints',
          title: 'All Complaints',
          desc: 'View and manage all customer complaints across departments.',
        },
        {
          to: '/company/assign',
          title: 'Assign Complaint',
          desc: 'Assign complaints to support agents or engineers.',
        },
        {
          to: '/company/departments',
          title: 'Department Overview',
          desc: 'Complaint distribution across departments.',
        },
        {
          to: '/company/network',
          title: 'Network Insights',
          desc: 'View network measurements, tower map, and ML predictions.',
        },
      ],
    }
  }

  if (department === 'Network') {
    return {
      title: 'Network Operations Dashboard',
      subtitle: 'Real-time network telemetry, tower performance, and network complaints.',
      actions: [
        {
          to: '/company/network',
          title: 'Network Insights',
          desc: 'Explore live cell towers, network telemetry, and ML latency forecasts.',
        },
        {
          to: '/company/complaints',
          title: 'Network Complaints',
          desc: 'Investigate and resolve network-related customer incidents.',
        },
      ],
    }
  }

  if (department === 'Technical') {
    return {
      title: 'Technical Operations Dashboard',
      subtitle: 'Technical incident diagnosis, field engineering, and complaint resolution.',
      actions: [
        {
          to: '/company/complaints',
          title: 'Technical Complaints',
          desc: 'View and resolve technical operational complaints.',
        },
        {
          to: '/company/assign',
          title: 'Assign Complaint',
          desc: 'Route technical issues to engineering staff.',
        },
      ],
    }
  }

  if (department === 'Billing') {
    return {
      title: 'Billing Operations Dashboard',
      subtitle: 'Billing inquiries, dispute investigations, and account operations.',
      actions: [
        {
          to: '/company/complaints',
          title: 'Billing Complaints',
          desc: 'Investigate and resolve billing inquiries and payment disputes.',
        },
      ],
    }
  }

  if (department === 'Customer Support') {
    return {
      title: 'Customer Support Dashboard',
      subtitle: 'Customer service ticketing, communication, and issue tracking.',
      actions: [
        {
          to: '/company/complaints',
          title: 'Support Complaints',
          desc: 'Manage customer tickets and communicate resolution status.',
        },
        {
          to: '/company/assign',
          title: 'Assign Complaint',
          desc: 'Assign customer complaints to specialized teams.',
        },
      ],
    }
  }

  return {
    title: 'Company Operations Dashboard',
    subtitle: 'Overview of current telecom operations.',
    actions: [
      {
        to: '/company/complaints',
        title: 'Complaints',
        desc: 'View assigned customer complaints.',
      },
    ],
  }
}

function CompanyDashboard() {
  const { token, user, department } = useAuth()
  const [summary, setSummary] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    async function loadSummary() {
      try {
        const data = await getComplaintSummary(token)
        setSummary(data)
      } catch (err) {
        setError('Unable to load complaint summary')
      } finally {
        setLoading(false)
      }
    }

    loadSummary()
  }, [token])

  if (loading) {
    return <div className="complaints-page">Loading dashboard...</div>
  }

  if (error) {
    return <div className="complaints-page complaints-error">{error}</div>
  }

  const effectiveDept = department || summary?.department
  const isManager =
    user?.role === 'manager' ||
    user?.role === 'admin' ||
    effectiveDept === 'Operations'
  const isUnassigned = !isManager && !effectiveDept
  const details = getDashboardDetails(user, effectiveDept)

  return (
    <div className="complaints-page">
      <div className="complaints-header">
        <div>
          <h1>{details.title}</h1>
          <p>{details.subtitle}</p>
        </div>
      </div>

      {isUnassigned && (
        <div
          style={{
            background: 'rgba(239, 68, 68, 0.1)',
            border: '1px solid rgba(239, 68, 68, 0.3)',
            borderRadius: '8px',
            padding: '14px 18px',
            marginBottom: '20px',
            color: '#fca5a5',
          }}
        >
          <strong>⚠️ Department Assignment Required</strong>
          <p style={{ margin: '4px 0 0 0', fontSize: '13px', color: '#fecaca' }}>
            Your employee account does not currently have a valid department
            assigned in the database. Please contact your system administrator to
            configure your department.
          </p>
        </div>
      )}

      <div className="dashboard-stats">
        <div className="dashboard-stat-card">
          <span>Total Complaints</span>
          <strong>{summary?.total ?? 0}</strong>
        </div>

        <div className="dashboard-stat-card">
          <span>Pending</span>
          <strong>{summary?.pending ?? 0}</strong>
        </div>

        <div className="dashboard-stat-card">
          <span>Assigned</span>
          <strong>{summary?.assigned ?? 0}</strong>
        </div>

        <div className="dashboard-stat-card">
          <span>In Progress</span>
          <strong>{summary?.in_progress ?? 0}</strong>
        </div>

        <div className="dashboard-stat-card">
          <span>Resolved</span>
          <strong>{summary?.resolved ?? 0}</strong>
        </div>

        <div className="dashboard-stat-card">
          <span>Closed</span>
          <strong>{summary?.closed ?? 0}</strong>
        </div>
      </div>

      <div className="company-actions">
        <h2>Operations</h2>

        <div className="company-action-grid">
          {details.actions.map((action) => (
            <Link
              key={action.to}
              to={action.to}
              className="company-action-card"
            >
              <h3>{action.title}</h3>
              <p>{action.desc}</p>
            </Link>
          ))}
        </div>
      </div>
    </div>
  )
}

export default CompanyDashboard