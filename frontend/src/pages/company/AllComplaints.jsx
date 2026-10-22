import { useEffect, useState } from 'react'
import { getAllComplaints } from '../../services/api'
import { useAuth } from '../../AuthContext'
import ResolutionTimeline from '../../components/complaints/ResolutionTimeline'
import StatusTransitionModal from '../../components/complaints/StatusTransitionModal'
import AssignmentBadge from '../../components/complaints/AssignmentBadge'
import '../../styles/complaint-operations.css'

function AllComplaints() {
  const { token, user, department: userDept } = useAuth()
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
        const data = await getAllComplaints(token)
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
    return <div className="complaints-page">Loading complaints...</div>
  }

  if (error) {
    return <div className="complaints-page complaints-error">{error}</div>
  }

  return (
    <div className="complaints-page">
      <div className="complaints-header">
        <div>
          <h1>{userDept ? `${userDept} Complaints` : 'All Complaints'}</h1>
          <p>
            {userDept
              ? `View, route, and manage ${userDept} customer complaints across their full lifecycle.`
              : 'View, route, and manage customer complaints across their full lifecycle.'}
          </p>
        </div>

        <div className="complaints-count">
          {complaints.length} Complaint{complaints.length !== 1 ? 's' : ''}
        </div>
      </div>

      {complaints.length === 0 ? (
        <div className="empty-complaints">
          <h3>No complaints found</h3>
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

                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <AssignmentBadge
                    department={complaint.department}
                    assignedTo={complaint.assigned_to}
                  />
                  <span
                    className={`complaint-status status-${complaint.status
                      .toLowerCase()
                      .replace(/\s+/g, '-')}`}
                  >
                    {complaint.status}
                  </span>
                </div>
              </div>

              <p className="complaint-description">
                {complaint.description}
              </p>

              {/* Lifecycle Progress Timeline */}
              <ResolutionTimeline complaint={complaint} />

              <div className="complaint-details">
                <div>
                  <span>Customer ID</span>
                  <strong>{complaint.customer_id}</strong>
                </div>

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

                <div>
                  <span>Assigned To</span>
                  <strong>
                    {complaint.assigned_to ? `#${complaint.assigned_to}` : 'Not assigned'}
                  </strong>
                </div>
              </div>

              {/* Valid Lifecycle Transition Actions with Resolution Notes Prompt */}
              <StatusTransitionModal
                complaint={complaint}
                userRole={user?.role || 'staff'}
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

export default AllComplaints