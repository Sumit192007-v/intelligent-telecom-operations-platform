import React from 'react'
import { LIFECYCLE_STAGES } from '../../services/complaintOperationsApi'
import '../../styles/complaint-operations.css'

export default function ResolutionTimeline({ complaint }) {
  if (!complaint) return null

  const currentStatus = complaint.status || 'Pending'
  const currentIndex = LIFECYCLE_STAGES.indexOf(currentStatus)
  const safeIndex = currentIndex >= 0 ? currentIndex : 0

  const formatDate = (dateStr) => {
    if (!dateStr) return null
    try {
      return new Date(dateStr).toLocaleString(undefined, {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      })
    } catch {
      return dateStr
    }
  }

  return (
    <div className="co-timeline-container">
      <div className="co-timeline-header">
        <span className="co-timeline-title">Resolution Lifecycle</span>
        <span className={`complaint-status status-${currentStatus.toLowerCase().replace(/\s+/g, '-')}`}>
          {currentStatus}
        </span>
      </div>

      <div className="co-timeline-steps">
        {LIFECYCLE_STAGES.map((stage, idx) => {
          const isCompleted = idx < safeIndex || (currentStatus === 'Closed' && idx <= safeIndex)
          const isCurrent = idx === safeIndex

          let stepClass = 'co-timeline-step'
          if (isCompleted) stepClass += ' co-step-completed'
          if (isCurrent) stepClass += ' co-step-current'

          return (
            <div key={stage} className={stepClass}>
              <div className="co-step-dot">
                {isCompleted ? '✓' : idx + 1}
              </div>
              <span className="co-step-label">{stage}</span>

              {idx < LIFECYCLE_STAGES.length - 1 && (
                <div
                  className={`co-step-connector ${
                    idx < safeIndex ? 'completed' : ''
                  }`}
                />
              )}
            </div>
          )
        })}
      </div>

      {/* Resolution Notes & Timestamp Callout */}
      {(complaint.resolution_notes || complaint.resolved_at) && (
        <div className="co-resolution-notes-card">
          <div className="co-resolution-notes-title">
            <span>✓ Resolution Record</span>
            {complaint.resolved_at && (
              <span className="co-resolution-meta">
                Resolved on {formatDate(complaint.resolved_at)}
              </span>
            )}
          </div>
          {complaint.resolution_notes && (
            <p className="co-resolution-notes-body">
              {complaint.resolution_notes}
            </p>
          )}
        </div>
      )}
    </div>
  )
}
