import { useEffect, useState } from 'react'
import {
  assignComplaint,
  getStaff,
} from '../../services/api'
import { useAuth } from '../../AuthContext'

function AssignComplaint() {
  const { token } = useAuth()
  const [complaintId, setComplaintId] = useState('')
  const [assignedTo, setAssignedTo] = useState('')
  const [department, setDepartment] = useState('Technical')

  const [staff, setStaff] = useState([])
  const [loadingStaff, setLoadingStaff] = useState(true)

  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    async function loadStaff() {
      if (!token) {
        setError('Sign in to load staff members.')
        setLoadingStaff(false)
        return
      }

      try {
        const data = await getStaff(token)
        setStaff(data)
      } catch (err) {
        setError('Unable to load staff members.')
      } finally {
        setLoadingStaff(false)
      }
    }

    loadStaff()
  }, [token])

  async function handleAssign(event) {
    event.preventDefault()

    setMessage('')
    setError('')

    if (!complaintId || !assignedTo || !department) {
      setError('Please fill in all fields.')
      return
    }

    try {
      setLoading(true)

      const result = await assignComplaint(
        Number(complaintId),
        Number(assignedTo),
        department
      )

      setMessage(
        `Complaint CMP-${String(result.complaint_id).padStart(3, '0')} assigned successfully.`
      )

      setComplaintId('')
      setAssignedTo('')
    } catch (err) {
      setError('Unable to assign complaint.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="complaints-page">
      <div className="complaints-header">
        <div>
          <h1>Assign Complaint</h1>
          <p>Assign a complaint to a team member.</p>
        </div>
      </div>

      <form className="complaint-card" onSubmit={handleAssign}>
        <div className="complaint-form-group">
          <label>Complaint ID</label>

          <input
            type="number"
            value={complaintId}
            onChange={(e) => setComplaintId(e.target.value)}
            placeholder="Example: 1"
          />
        </div>

        <div className="complaint-form-group">
          <label>Assign To</label>

          <select
            value={assignedTo}
            onChange={(e) => setAssignedTo(e.target.value)}
            disabled={loadingStaff}
          >
            <option value="">
              {loadingStaff
                ? 'Loading staff...'
                : 'Select staff member'}
            </option>

            {staff.map((s) => (
              <option key={s.id} value={s.id}>
                {s.email} - {s.department}
              </option>
            ))}
          </select>
        </div>

        <div className="complaint-form-group">
          <label>Department</label>

          <select
            value={department}
            onChange={(e) => setDepartment(e.target.value)}
          >
            <option value="Technical">Technical</option>
            <option value="Network">Network</option>
            <option value="Billing">Billing</option>
            <option value="Customer Support">
              Customer Support
            </option>
          </select>
        </div>

        <button type="submit" disabled={loading || loadingStaff}>
          {loading ? 'Assigning...' : 'Assign Complaint'}
        </button>

        {message && (
          <p className="complaint-success">{message}</p>
        )}

        {error && (
          <p className="complaints-error">{error}</p>
        )}
      </form>
    </div>
  )
}

export default AssignComplaint