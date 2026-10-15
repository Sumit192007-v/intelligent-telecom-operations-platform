import { useEffect, useState } from 'react'
import { useAuth } from '../../AuthContext'
import { getCustomerComplaints } from '../../services/api'
import ResolutionTimeline from '../../components/complaints/ResolutionTimeline'
import StatusTransitionModal from '../../components/complaints/StatusTransitionModal'
import AssignmentBadge from '../../components/complaints/AssignmentBadge'
import '../../styles/complaint-operations.css'

function ComplaintStatus() {
  const { token } = useAuth()
  const [complaints, setComplaints] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const handleStatusUpdated = (updated) => {
    setComplaints((prev) =>
      prev.map((c) => (c.id === updated.complaint_id ? { ...c, ...updated } : c))
    )
  }

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
          <p>Track the real-time resolution lifecycle of your complaints.</p>
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

                <AssignmentBadge
                  department={complaint.department}
                  assignedTo={complaint.assigned_to}
                />
              </div>

              {/* Lifecycle Progress Stepper */}
              <ResolutionTimeline complaint={complaint} />

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
                Last updated:{' '}
                {complaint.updated_at
                  ? new Date(complaint.updated_at).toLocaleString()
                  : 'Not available'}
              </p>

              {/* Customer Actions (e.g. Confirm & Close once Resolved) */}
              <StatusTransitionModal
                complaint={complaint}
                userRole="customer"
                token={token}
                onStatusUpdated={handleStatusUpdated}
              />
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default ComplaintStatus