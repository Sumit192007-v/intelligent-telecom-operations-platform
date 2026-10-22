const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

export async function sendChatMessage({ message, conversationHistory = [], token = null }) {
  const headers = {
    'Content-Type': 'application/json',
  }

  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  const response = await fetch(`${API_BASE}/api/chatbot/message`, {
    method: 'POST',
    headers,
    body: JSON.stringify({
      message,
      conversation_history: conversationHistory.map((m) => ({
        role: m.role,
        content: m.content,
      })),
    }),
  })

  if (!response.ok) {
    let errorDetail = 'Failed to get response from AI Assistant'
    try {
      const errorJson = await response.json()
      if (errorJson.detail) errorDetail = errorJson.detail
    } catch {
      // Keep default error text
    }
    const err = new Error(errorDetail)
    err.status = response.status
    throw err
  }

  return response.json()
}

export async function fetchChatbotConfig() {
  try {
    const response = await fetch(`${API_BASE}/api/chatbot/config`)
    if (response.ok) {
      return await response.json()
    }
  } catch (err) {
    console.warn('Could not fetch chatbot config:', err)
  }
  return null
}
