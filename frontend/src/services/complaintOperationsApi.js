const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

async function apiFetch(url, options) {
  const response = await fetch(url, options)
  if (response.status === 401 && typeof window !== 'undefined') {
    window.dispatchEvent(new Event('auth:unauthorized'))
  }
  return response
}

/**
 * Fetch a single complaint by its ID (for customer owner or staff).
 */
export async function getComplaintById(complaintId, token) {
  const response = await apiFetch(`${API_BASE}/api/complaints/${complaintId}`, {
    headers: { Authorization: `Bearer ${token}` },
  })

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}))
    throw new Error(errorData.detail || 'Failed to fetch complaint details')
  }

  return response.json()
}

/**
 * Update complaint status with optional resolution notes and full lifecycle transition support.
 */
export async function updateComplaintStatusWithNotes(
  complaintId,
  status,
  resolutionNotes = null,
  token
) {
  const payload = { status }
  if (resolutionNotes !== null && resolutionNotes !== undefined) {
    payload.resolution_notes = resolutionNotes
  }

  const response = await apiFetch(
    `${API_BASE}/api/complaints/${complaintId}/status`,
    {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(payload),
    }
  )

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}))
    throw new Error(errorData.detail || 'Failed to update complaint status')
  }

  return response.json()
}

/**
 * Lifecycle stage definitions and transition mapping matching backend business rules.
 */
export const LIFECYCLE_STAGES = [
  'Pending',
  'Assigned',
  'In Progress',
  'Resolved',
  'Closed',
]

export const ALLOWED_TRANSITIONS = {
  Pending: ['Assigned', 'In Progress', 'Closed'],
  Assigned: ['In Progress', 'Pending', 'Closed'],
  'In Progress': ['Resolved', 'Assigned'],
  Resolved: ['Closed', 'In Progress'],
  Closed: ['In Progress'],
}

export function getAllowedTransitions(currentStatus, role = 'staff') {
  if (role === 'customer') {
    return currentStatus === 'Resolved' ? ['Closed'] : []
  }
  return ALLOWED_TRANSITIONS[currentStatus] || []
}
