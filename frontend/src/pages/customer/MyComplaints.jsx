import { useEffect, useState } from 'react'
import { useAuth } from '../../AuthContext'
import { getCustomerComplaints } from '../../services/api'

function MyComplaints() {
  const { token } = useAuth()
  const [complaints, setComplaints] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    async function loadComplaints() {
      try {
        const data = await getCustomerComplaints(token)
        setComplaints(data)
      } catch (err) {
        setError('Unable to load complaints')
      } finally {
        setLoading(false)
      }
    }

    loadComplaints()
  }, [token])

  if (loading) {
    return (
      <div className="complaints-page">
        <h1>My Complaints</h1>
        <p className="complaints-message">Loading complaints...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="complaints-page">
        <h1>My Complaints</h1>
        <p className="complaints-error">{error}</p>
      </div>
    )
  }

  return (
    <div className="complaints-page">
      <div className="complaints-header">
        <div>
          <h1>My Complaints</h1>
          <p>Track and manage your submitted complaints.</p>
        </div>

        <div className="complaints-count">
          {complaints.length} Complaint{complaints.length !== 1 ? 's' : ''}
        </div>
      </div>

      {complaints.length === 0 ? (
        <div className="empty-complaints">
          <h3>No complaints found</h3>
          <p>You haven't submitted any complaints yet.</p>
        </div>
      ) : (
        <div className="complaints-list">
          {complaints.map((complaint) => (
            <div className="complaint-card" key={complaint.id}>
              <div className="complaint-card-top">
                <div>
                  <span className="complaint-id">
                    CMP-{String(complaint.id).padStart(3, '0')}
                  </span>

                  <h2>{complaint.subject}</h2>
                </div>

                <span
                  className={`complaint-status status-${complaint.status
                    .toLowerCase()
                    .replace(/\s+/g, '-')}`}
                >
                  {complaint.status}
                </span>
              </div>

              <p className="complaint-description">
                {complaint.description}
              </p>

              <div className="complaint-details">
                <div>
                  <span>Type</span>
                  <strong>{complaint.complaint_type}</strong>
                </div>

                <div>
                  <span>Priority</span>
                  <strong>{complaint.priority}</strong>
                </div>

                <div>
                  <span>Department</span>
                  <strong>{complaint.department || 'Not assigned'}</strong>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default MyComplaints