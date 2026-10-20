import React from 'react'
import '../../styles/complaint-operations.css'

export default function AssignmentBadge({ department, assignedTo }) {
  return (
    <div className="co-assignment-badge">
      <span>Dept:</span>
      <strong>{department || 'Unassigned'}</strong>
      {assignedTo ? (
        <>
          <span style={{ margin: '0 2px' }}>•</span>
          <span>Staff:</span>
          <strong>#{assignedTo}</strong>
        </>
      ) : (
        <span style={{ color: 'var(--amber, #eab308)', marginLeft: '4px' }}>
          (Triage Pending)
        </span>
      )}
    </div>
  )
}
