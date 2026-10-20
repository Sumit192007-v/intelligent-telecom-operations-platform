import React, { useState } from 'react'
import {
  getAllowedTransitions,
  updateComplaintStatusWithNotes,
} from '../../services/complaintOperationsApi'
import '../../styles/complaint-operations.css'

export default function StatusTransitionModal({
  complaint,
  userRole = 'staff',
  token,
  onStatusUpdated,
}) {
  const [submitting, setSubmitting] = useState(false)
  const [errorMessage, setErrorMessage] = useState('')
  const [showNotesModal, setShowNotesModal] = useState(false)
  const [targetStatus, setTargetStatus] = useState('')
  const [resolutionNotes, setResolutionNotes] = useState('')

  if (!complaint) return null

  const currentStatus = complaint.status || 'Pending'
  const allowed = getAllowedTransitions(currentStatus, userRole)

  if (!allowed || allowed.length === 0) {
    return null
  }

  const getButtonConfig = (status) => {
    switch (status) {
      case 'In Progress':
        return {
          label: currentStatus === 'Resolved' || currentStatus === 'Closed' ? 'Reopen' : 'Start Investigation',
          className: currentStatus === 'Resolved' || currentStatus === 'Closed' ? 'co-action-reopen' : 'co-action-progress',
          requiresNotes: false,
        }
      case 'Resolved':
        return {
          label: 'Mark Resolved',
          className: 'co-action-resolve',
          requiresNotes: true,
        }
      case 'Closed':
        return {
          label: userRole === 'customer' ? 'Confirm & Close' : 'Close Complaint',
          className: 'co-action-close',
          requiresNotes: false,
        }
      case 'Assigned':
        return {
          label: 'Return to Assigned',
          className: 'co-action-progress',
          requiresNotes: false,
        }
      case 'Pending':
        return {
          label: 'Return to Pending',
          className: 'co-action-close',
          requiresNotes: false,
        }
      default:
        return {
          label: `Move to ${status}`,
          className: 'co-action-progress',
          requiresNotes: false,
        }
    }
  }

  const handleActionClick = (status) => {
    const config = getButtonConfig(status)
    setErrorMessage('')

    if (config.requiresNotes) {
      setTargetStatus(status)
      setResolutionNotes('')
      setShowNotesModal(true)
    } else {
      executeTransition(status, null)
    }
  }

  const executeTransition = async (status, notes) => {
    try {
      setSubmitting(true)
      setErrorMessage('')
      const updated = await updateComplaintStatusWithNotes(
        complaint.id,
        status,
        notes,
        token
      )
      setShowNotesModal(false)
      if (onStatusUpdated) {
        onStatusUpdated(updated)
      }
    } catch (err) {
      setErrorMessage(err.message || 'Failed to update complaint status.')
    } finally {
      setSubmitting(false)
    }
  }

  const handleModalSubmit = (e) => {
    e.preventDefault()
    if (!resolutionNotes.trim()) {
      setErrorMessage('Please provide a brief description of the resolution.')
      return
    }
    executeTransition(targetStatus, resolutionNotes.trim())
  }

  return (
    <div className="co-actions-wrapper">
      <div className="co-actions-panel">
        <span style={{ fontSize: '12px', color: 'var(--text-dim)', marginRight: '4px' }}>
          Available Actions:
        </span>
        {allowed.map((nextStatus) => {
          const config = getButtonConfig(nextStatus)
          return (
            <button
              key={nextStatus}
              type="button"
              className={`co-action-btn ${config.className}`}
              disabled={submitting}
              onClick={() => handleActionClick(nextStatus)}
            >
              {submitting ? 'Updating...' : config.label}
            </button>
          )
        })}
      </div>

      {errorMessage && (
        <p style={{ color: 'var(--red, #ef4444)', fontSize: '12px', marginTop: '6px' }}>
          {errorMessage}
        </p>
      )}

      {/* Resolution Notes Modal */}
      {showNotesModal && (
        <div className="co-modal-backdrop" onClick={() => setShowNotesModal(false)}>
          <div className="co-modal-card" onClick={(e) => e.stopPropagation()}>
            <h3 className="co-modal-title">Record Complaint Resolution</h3>
            <p className="co-modal-description">
              Please enter the resolution details and actions taken to fix CMP-
              {String(complaint.id).padStart(3, '0')}.
            </p>

            <form onSubmit={handleModalSubmit}>
              <textarea
                className="co-modal-textarea"
                placeholder="Describe resolution (e.g. Spliced fiber line at sector 4, replaced ONT modem, verified latency)."
                value={resolutionNotes}
                onChange={(e) => setResolutionNotes(e.target.value)}
                required
              />

              <div className="co-modal-actions">
                <button
                  type="button"
                  className="co-modal-btn-cancel"
                  disabled={submitting}
                  onClick={() => setShowNotesModal(false)}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="co-modal-btn-confirm"
                  disabled={submitting || !resolutionNotes.trim()}
                >
                  {submitting ? 'Saving...' : 'Resolve & Complete'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
