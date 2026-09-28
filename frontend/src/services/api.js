const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

export async function getHealth() {
  const response = await fetch(`${API_BASE}/health`)
  return response.json()
}

export async function login(email, password) {
  const response = await fetch(`${API_BASE}/api/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  })

  if (!response.ok) {
    throw new Error('Invalid email or password')
  }

  return response.json()
}

export async function submitComplaint(complaint) {
  const response = await fetch(`${API_BASE}/api/complaints/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(complaint),
  })

  if (!response.ok) {
    throw new Error('Failed to submit complaint')
  }

  return response.json()
}
export async function getCustomerComplaints(customerId) {
  const response = await fetch(
    `${API_BASE}/api/complaints/${customerId}`
  )

  if (!response.ok) {
    throw new Error('Failed to fetch complaints')
  }

  return response.json()
}
export async function getAllComplaints() {
  const response = await fetch(`${API_BASE}/api/complaints/`)

  if (!response.ok) {
    throw new Error('Failed to fetch complaints')
  }

  return response.json()
}
export async function assignComplaint(
  complaintId,
  assignedTo,
  department
) {
  const response = await fetch(
    `${API_BASE}/api/complaints/${complaintId}/assign`,
    {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        assigned_to: assignedTo,
        department: department,
      }),
    }
  )

  if (!response.ok) {
    throw new Error('Failed to assign complaint')
  }

  return response.json()
}
export async function getStaff(token) {
  const response = await fetch(`${API_BASE}/api/complaints/staff`, {
    headers: { Authorization: `Bearer ${token}` },
  })

  if (!response.ok) {
    throw new Error('Failed to fetch staff')
  }

  return response.json()
}
export async function getComplaintSummary() {
  const response = await fetch(`${API_BASE}/api/complaints/summary`)

  if (!response.ok) {
    throw new Error('Failed to fetch complaint summary')
  }

  return response.json()
}
export async function getDepartmentSummary() {
  const response = await fetch(
    `${API_BASE}/api/complaints/departments`
  )

  if (!response.ok) {
    throw new Error('Failed to fetch department summary')
  }

  return response.json()
}
export async function getNetworkMeasurements(operator = '') {
  const url = operator
    ? `${API_BASE}/api/network/measurements?operator=${encodeURIComponent(operator)}`
    : `${API_BASE}/api/network/measurements`

  const response = await fetch(url)

  if (!response.ok) {
    throw new Error('Failed to fetch network measurements')
  }

  return response.json()
}

export async function getNetworkMapData(token) {
  const response = await fetch(`${API_BASE}/api/network/map-data`, {
    headers: { Authorization: `Bearer ${token}` },
  })

  if (!response.ok) {
    const error = new Error('Failed to fetch network map data')
    error.status = response.status
    throw error
  }

  return response.json()
}

export async function predictLatency(data) {
  const response = await fetch(`${API_BASE}/api/predict/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(data),
  })

  if (!response.ok) {
    throw new Error('Failed to get latency prediction')
  }

  return response.json()
}
export async function updateComplaintStatus(
  complaintId,
  status
) {
  const response = await fetch(
    `${API_BASE}/api/complaints/${complaintId}/status`,
    {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        status: status,
      }),
    }
  )

  if (!response.ok) {
    throw new Error(
      'Failed to update complaint status'
    )
  }

  return response.json()
}