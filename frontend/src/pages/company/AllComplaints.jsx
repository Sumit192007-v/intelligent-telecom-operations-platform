import { useEffect, useState } from 'react'
import {
  getAllComplaints,
  updateComplaintStatus,
} from '../../services/api'

function AllComplaints() {
  const [complaints, setComplaints] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  async function handleStatusChange(
  complaintId,
  status
) {
  try {
    await updateComplaintStatus(
      complaintId,
      status
    )

    const data = await getAllComplaints()
    setComplaints(data)
  } catch (err) {
    console.error(err)
    alert('Failed to update complaint status')
  }
}

  useEffect(() => {
    async function loadComplaints() {
      try {
        const data = await getAllComplaints()
        setComplaints(data)
      } catch (err) {
        setError('Unable to load complaints')
      } finally {
        setLoading(false)
      }
    }

    loadComplaints()
  }, [])

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
          <h1>All Complaints</h1>
          <p>View and manage customer complaints.</p>
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

                <select
  className={`complaint-status status-${complaint.status
    .toLowerCase()
    .replace(/\s+/g, '-')}`}
  value={complaint.status}
  onChange={(e) =>
    handleStatusChange(
      complaint.id,
      e.target.value
    )
  }
>
  <option value="Pending">Pending</option>
  <option value="Assigned">Assigned</option>
  <option value="In Progress">In Progress</option>
  <option value="Resolved">Resolved</option>
  <option value="Closed">Closed</option>
</select>
              </div>

              <p className="complaint-description">
                {complaint.description}
              </p>

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
                    {complaint.assigned_to || 'Not assigned'}
                  </strong>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default AllComplaints