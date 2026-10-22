import React, { useState, useEffect, useRef } from 'react'
import { sendChatMessage, fetchChatbotConfig } from '../../services/chatbotApi'
import { useAuth } from '../../AuthContext'
import './chatbot.css'

const CUSTOM_LOGO_URL = '/chatbot-logo.png'

const SUGGESTED_PROMPTS = [
  'Slow Internet',
  'No Network',
  'Call Drops',
  'Check My Plan',
  'Register a Complaint',
]

function renderInlineFormatting(str) {
  const parts = []
  let remaining = str
  let key = 0

  while (remaining.length > 0) {
    const boldMatch = remaining.match(/\*\*(.+?)\*\*/)
    const codeMatch = remaining.match(/`([^`]+)`/)

    let nextMatch = null
    let type = null

    if (boldMatch && (!codeMatch || boldMatch.index < codeMatch.index)) {
      nextMatch = boldMatch
      type = 'bold'
    } else if (codeMatch) {
      nextMatch = codeMatch
      type = 'code'
    }

    if (nextMatch) {
      if (nextMatch.index > 0) {
        parts.push(remaining.substring(0, nextMatch.index))
      }
      if (type === 'bold') {
        parts.push(<strong key={key++}>{nextMatch[1]}</strong>)
      } else if (type === 'code') {
        parts.push(
          <code key={key++} className="chatbot-inline-code">
            {nextMatch[1]}
          </code>
        )
      }
      remaining = remaining.substring(nextMatch.index + nextMatch[0].length)
    } else {
      parts.push(remaining)
      break
    }
  }

  return parts
}

function renderFormattedMessage(text) {
  if (!text) return null
  const lines = text.split('\n')
  return (
    <div className="chatbot-rendered-text">
      {lines.map((line, idx) => {
        const trimmed = line.trim()
        if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
          return (
            <div key={idx} className="chatbot-list-item">
              <span className="chatbot-bullet">•</span>
              <span>{renderInlineFormatting(trimmed.slice(2))}</span>
            </div>
          )
        }
        const numMatch = trimmed.match(/^(\d+)\.\s+(.*)$/)
        if (numMatch) {
          return (
            <div key={idx} className="chatbot-list-item">
              <span className="chatbot-num-badge">{numMatch[1]}.</span>
              <span>{renderInlineFormatting(numMatch[2])}</span>
            </div>
          )
        }
        if (trimmed.startsWith('### ')) {
          return (
            <h4 key={idx} className="chatbot-heading">
              {renderInlineFormatting(trimmed.slice(4))}
            </h4>
          )
        }
        if (trimmed.startsWith('## ')) {
          return (
            <h3 key={idx} className="chatbot-heading">
              {renderInlineFormatting(trimmed.slice(3))}
            </h3>
          )
        }
        if (!trimmed) {
          return <div key={idx} className="chatbot-line-spacer" />
        }
        return (
          <p key={idx} className="chatbot-paragraph">
            {renderInlineFormatting(line)}
          </p>
        )
      })}
    </div>
  )
}

function LogoAvatar({ size = 34, className = '' }) {
  const [hasError, setHasError] = useState(false)

  if (hasError) {
    return (
      <div
        className={`chatbot-logo-fallback ${className}`}
        style={{ width: size, height: size }}
        title="Telecom AI Assistant"
      >
        <svg
          viewBox="0 0 24 24"
          width={size * 0.6}
          height={size * 0.6}
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
        >
          <rect x="3" y="11" width="18" height="10" rx="2" />
          <circle cx="12" cy="5" r="2" />
          <path d="M12 7v4" />
          <line x1="8" y1="16" x2="8" y2="16.01" />
          <line x1="16" y1="16" x2="16" y2="16.01" />
        </svg>
      </div>
    )
  }

  return (
    <img
      src={CUSTOM_LOGO_URL}
      alt="Telecom AI Assistant Logo"
      className={`chatbot-logo-img ${className}`}
      style={{ width: size, height: size }}
      onError={() => setHasError(true)}
    />
  )
}

export default function ChatbotWidget() {
  const { token, user } = useAuth()
  const [isOpen, setIsOpen] = useState(false)
  const [messages, setMessages] = useState([
    {
      id: 'welcome',
      role: 'assistant',
      content:
        "👋 Welcome to NetPulse Support! I am your **Telecom AI Assistant** powered by Groq.\n\nI can help you troubleshoot connection issues, check live network status, look up existing complaints, or register a new issue. What can I do for you today?",
    },
  ])
  const [inputValue, setInputValue] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [lastFailedMessage, setLastFailedMessage] = useState(null)
  const [serverConfig, setServerConfig] = useState(null)

  const messagesEndRef = useRef(null)
  const textareaRef = useRef(null)

  // Fetch server config on mount
  useEffect(() => {
    fetchChatbotConfig().then((cfg) => {
      if (cfg) setServerConfig(cfg)
    })
  }, [])

  // Auto-scroll on new messages
  useEffect(() => {
    if (isOpen) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }
  }, [messages, isLoading, isOpen])

  // Focus textarea when opening
  useEffect(() => {
    if (isOpen) {
      setTimeout(() => textareaRef.current?.focus(), 150)
    }
  }, [isOpen])

  async function handleSendMessage(textToSend) {
    const text = (textToSend || inputValue).trim()
    if (!text || isLoading) return

    setInputValue('')
    setLastFailedMessage(null)

    const userMsg = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: text,
    }

    const updatedMessages = [...messages, userMsg]
    setMessages(updatedMessages)
    setIsLoading(true)

    // Build history excluding welcome and error messages
    const history = updatedMessages
      .filter((m) => m.id !== 'welcome' && !m.isError)
      .map((m) => ({ role: m.role, content: m.content }))

    try {
      const data = await sendChatMessage({
        message: text,
        conversationHistory: history.slice(0, -1),
        token,
      })

      const assistantMsg = {
        id: `assistant-${Date.now()}`,
        role: 'assistant',
        content:
          data.response ||
          "I'm here to help. Please let me know what else you'd like to check.",
        status: data.status,
      }
      setMessages((prev) => [...prev, assistantMsg])
    } catch (err) {
      console.error('Chatbot request error:', err)
      setLastFailedMessage(text)
      const errorMsg = {
        id: `error-${Date.now()}`,
        role: 'assistant',
        content: `⚠️ ${err.message || 'Unable to connect to the AI Assistant service.'} Please check that the backend server is running and try again.`,
        isError: true,
      }
      setMessages((prev) => [...prev, errorMsg])
    } finally {
      setIsLoading(false)
    }
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSendMessage()
    }
  }

  function handleRestart() {
    setMessages([
      {
        id: 'welcome',
        role: 'assistant',
        content:
          "Conversation restarted. 👋 How can I assist you with your telecom service today?",
      },
    ])
    setLastFailedMessage(null)
    setInputValue('')
  }

  return (
    <div className="chatbot-container" data-chatbot-active={isOpen}>
      {/* Floating launcher button */}
      {!isOpen && (
        <button
          type="button"
          className="chatbot-launcher"
          onClick={() => setIsOpen(true)}
          aria-label="Open Telecom AI Assistant"
          title="Open Telecom AI Assistant"
        >
          <LogoAvatar size={48} className="chatbot-launcher-logo" />
          <span className="chatbot-launcher-badge" aria-hidden="true" />
          <span className="chatbot-launcher-tooltip">Chat with Telecom AI</span>
        </button>
      )}

      {/* Chat Window */}
      {isOpen && (
        <div
          className="chatbot-window"
          role="dialog"
          aria-label="Telecom AI Assistant Chat Window"
        >
          {/* Header */}
          <div className="chatbot-header">
            <div className="chatbot-header-identity">
              <LogoAvatar size={40} className="chatbot-header-logo" />
              <div className="chatbot-header-text">
                <div className="chatbot-header-title-row">
                  <span className="chatbot-header-title">
                    Telecom AI Assistant
                  </span>
                  <span
                    className={`chatbot-status-indicator ${
                      serverConfig?.status === 'ready'
                        ? 'status-online'
                        : 'status-standby'
                    }`}
                    title={
                      serverConfig?.status === 'ready'
                        ? `Powered by Groq (${serverConfig?.model || 'Llama 3.3'})`
                        : 'Awaiting Groq API key'
                    }
                  >
                    {serverConfig?.status === 'ready' ? 'Groq AI' : 'Ready'}
                  </span>
                </div>
                <span className="chatbot-header-subtitle">
                  Your network and connectivity support assistant
                </span>
              </div>
            </div>

            <div className="chatbot-header-actions">
              <button
                type="button"
                className="chatbot-icon-btn"
                onClick={handleRestart}
                title="Restart conversation"
                aria-label="Restart conversation"
              >
                <svg
                  viewBox="0 0 24 24"
                  width="16"
                  height="16"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                >
                  <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8" />
                  <path d="M3 3v5h5" />
                </svg>
              </button>
              <button
                type="button"
                className="chatbot-icon-btn"
                onClick={() => setIsOpen(false)}
                title="Close chat"
                aria-label="Close chat"
              >
                <svg
                  viewBox="0 0 24 24"
                  width="18"
                  height="18"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                >
                  <line x1="18" y1="6" x2="6" y2="18" />
                  <line x1="6" y1="6" x2="18" y2="18" />
                </svg>
              </button>
            </div>
          </div>

          {/* User status badge bar */}
          <div className="chatbot-account-banner">
            <span className="chatbot-account-dot" />
            <span className="chatbot-account-text">
              {user
                ? `Logged in as ${user.name || user.role} (${user.role})`
                : 'Browsing as Guest • Sign in to file & view tickets'}
            </span>
          </div>

          {/* Quick Suggestions Chips */}
          <div
            className="chatbot-suggestions-bar"
            role="toolbar"
            aria-label="Quick suggestions"
          >
            {SUGGESTED_PROMPTS.map((prompt) => (
              <button
                key={prompt}
                type="button"
                className="chatbot-suggestion-chip"
                onClick={() => handleSendMessage(prompt)}
                disabled={isLoading}
              >
                {prompt}
              </button>
            ))}
          </div>

          {/* Message Area */}
          <div
            className="chatbot-messages"
            tabIndex={0}
            aria-live="polite"
            aria-relevant="additions text"
          >
            {messages.map((msg) => (
              <div
                key={msg.id}
                className={`chatbot-message-row ${
                  msg.role === 'user' ? 'row-user' : 'row-assistant'
                } ${msg.isError ? 'row-error' : ''}`}
              >
                {msg.role === 'assistant' && (
                  <div className="chatbot-msg-avatar">
                    <LogoAvatar size={28} />
                  </div>
                )}
                <div
                  className={`chatbot-bubble ${
                    msg.role === 'user' ? 'bubble-user' : 'bubble-assistant'
                  }`}
                >
                  {renderFormattedMessage(msg.content)}
                  {msg.isError && lastFailedMessage && (
                    <button
                      type="button"
                      className="chatbot-retry-btn"
                      onClick={() => handleSendMessage(lastFailedMessage)}
                    >
                      ↻ Retry last message
                    </button>
                  )}
                </div>
              </div>
            ))}

            {isLoading && (
              <div className="chatbot-message-row row-assistant">
                <div className="chatbot-msg-avatar">
                  <LogoAvatar size={28} />
                </div>
                <div className="chatbot-bubble bubble-assistant bubble-loading">
                  <span className="chatbot-typing-dot" />
                  <span className="chatbot-typing-dot" />
                  <span className="chatbot-typing-dot" />
                  <span className="chatbot-loading-label">
                    Analyzing network request...
                  </span>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Input Footer */}
          <div className="chatbot-footer">
            <form
              className="chatbot-input-form"
              onSubmit={(e) => {
                e.preventDefault()
                handleSendMessage()
              }}
            >
              <textarea
                ref={textareaRef}
                rows={1}
                className="chatbot-textarea"
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask about internet speed, call drops, outages, complaints..."
                maxLength={2000}
                disabled={isLoading}
                aria-label="Type your message"
              />
              <button
                type="submit"
                className="chatbot-send-btn"
                disabled={!inputValue.trim() || isLoading}
                aria-label="Send message"
                title="Send message (Enter)"
              >
                <svg
                  viewBox="0 0 24 24"
                  width="18"
                  height="18"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <line x1="22" y1="2" x2="11" y2="13" />
                  <polygon points="22 2 15 22 11 13 2 9 22 2" />
                </svg>
              </button>
            </form>
            <div className="chatbot-footer-hint">
              <span>Press Enter to send, Shift+Enter for new line</span>
              <span>{inputValue.length}/2000</span>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
