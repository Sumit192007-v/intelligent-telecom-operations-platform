import { useEffect, useState } from 'react'
import { getDepartmentSummary } from '../../services/api'
import { useAuth } from '../../AuthContext'

function DepartmentManagement() {
  const { token } = useAuth()
  const [departments, setDepartments] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    async function loadDepartments() {
      try {
        const data = await getDepartmentSummary(token)
        setDepartments(data)
      } catch (err) {
        setError('Unable to load departments')
      } finally {
        setLoading(false)
      }
    }

    loadDepartments()
  }, [token])

  if (loading) {
    return <div className="complaints-page">Loading departments...</div>
  }

  if (error) {
    return <div className="complaints-page complaints-error">{error}</div>
  }

  return (
    <div className="complaints-page">
      <div className="complaints-header">
        <div>
          <h1>Departments</h1>
          <p>Complaint distribution across departments.</p>
        </div>
      </div>

      <div className="department-grid">
        {departments.map((department) => (
          <div
            className="dashboard-stat-card"
            key={department.department}
          >
            <span>{department.department}</span>
            <strong>{department.complaints}</strong>
            <small>Complaints</small>
          </div>
        ))}
      </div>
    </div>
  )
}

export default DepartmentManagement