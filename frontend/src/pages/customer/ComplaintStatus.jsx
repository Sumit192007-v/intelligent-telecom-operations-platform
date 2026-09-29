import { useEffect, useState } from 'react'
import { useAuth } from '../../AuthContext'
import { getCustomerComplaints } from '../../services/api'

function ComplaintStatus() {
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
        setError('Unable to load complaint status')
      } finally {
        setLoading(false)
      }
    }

    loadComplaints()
  }, [token])

  if (loading) {
    return <div className="complaints-page">Loading...</div>
  }

  if (error) {
    return <div className="complaints-page complaints-error">{error}</div>
  }

  return (
    <div className="complaints-page">
      <div className="complaints-header">
        <div>
          <h1>Complaint Status</h1>
          <p>Track the current status of your complaints.</p>
        </div>
      </div>

      {complaints.length === 0 ? (
        <div className="empty-complaints">
          <h3>No complaints found</h3>
          <p>Submit a complaint to track its status here.</p>
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

              <p className="complaint-description">
                Last updated: {complaint.updated_at
                  ? new Date(complaint.updated_at).toLocaleString()
                  : 'Not available'}
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default ComplaintStatus