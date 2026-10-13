const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

async function request(path, options) {
  return fetch(`${API_BASE}${path}`, options)
}

function jsonOptions(method, body) {
  return {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  }
}

export async function getHealth() {
  const response = await request('/health')
  return response.json()
}

export async function submitComplaint(complaint) {
  const response = await request('/api/complaints/', jsonOptions('POST', complaint))

  if (!response.ok) {
    throw new Error('Failed to submit complaint')
  }

  return response.json()
}

export async function getCustomerComplaints() {
  const response = await request('/api/complaints/my')

  if (!response.ok) {
    throw new Error('Failed to fetch complaints')
  }

  return response.json()
}

export async function getAllComplaints() {
  const response = await request('/api/complaints/')

  if (!response.ok) {
    throw new Error('Failed to fetch complaints')
  }

  return response.json()
}

export async function assignComplaint(complaintId, assignedTo, department) {
  const response = await request(
    `/api/complaints/${complaintId}/assign`,
    jsonOptions('PUT', { assigned_to: assignedTo, department })
  )

  if (!response.ok) {
    throw new Error('Failed to assign complaint')
  }

  return response.json()
}

export async function getStaff() {
  const response = await request('/api/complaints/staff')

  if (!response.ok) {
    throw new Error('Failed to fetch staff')
  }

  return response.json()
}

export async function getComplaintSummary() {
  const response = await request('/api/complaints/summary')

  if (!response.ok) {
    throw new Error('Failed to fetch complaint summary')
  }

  return response.json()
}

export async function getDepartmentSummary() {
  const response = await request('/api/complaints/departments')

  if (!response.ok) {
    throw new Error('Failed to fetch department summary')
  }

  return response.json()
}

export async function getNetworkMeasurements(operator = '') {
  const path = operator
    ? `/api/network/measurements?operator=${encodeURIComponent(operator)}`
    : '/api/network/measurements'
  const response = await request(path)

  if (!response.ok) {
    throw new Error('Failed to fetch network measurements')
  }

  return response.json()
}

export async function getNetworkMapData() {
  const response = await request('/api/network/map-data')

  if (!response.ok) {
    const error = new Error('Failed to fetch network map data')
    error.status = response.status
    throw error
  }

  return response.json()
}

export async function predictLatency(data) {
  const response = await request('/api/predict/', jsonOptions('POST', data))

  if (!response.ok) {
    throw new Error('Failed to get latency prediction')
  }

  return response.json()
}

export async function updateComplaintStatus(complaintId, status) {
  const response = await request(
    `/api/complaints/${complaintId}/status`,
    jsonOptions('PUT', { status })
  )

  if (!response.ok) {
    throw new Error('Failed to update complaint status')
  }

  return response.json()
}
