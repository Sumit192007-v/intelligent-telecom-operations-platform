import React, { useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../../AuthContext'
import { submitComplaint } from '../../services/api'

export default function SubmitComplaint() {
  const { user } = useAuth()
  const [complaintType, setComplaintType] = useState('Network Issue')
  const [subject, setSubject] = useState('')
  const [description, setDescription] = useState('')
  const [priority, setPriority] = useState('Medium')
  const [latitude, setLatitude] = useState(null)
  const [longitude, setLongitude] = useState(null)
  const [locationMessage, setLocationMessage] = useState('')
  const [detectingLocation, setDetectingLocation] = useState(false)
  const [message, setMessage] = useState('')
  const [loading, setLoading] = useState(false)

  const handleDetectLocation = () => {
    if (!navigator.geolocation) {
      setLocationMessage('Location detection is not supported by this browser.')
      return
    }

    setDetectingLocation(true)
    setLocationMessage('')
    navigator.geolocation.getCurrentPosition(
      ({ coords }) => {
        setLatitude(coords.latitude)
        setLongitude(coords.longitude)
        setLocationMessage('Location detected.')
        setDetectingLocation(false)
      },
      () => {
        setLocationMessage('Unable to detect location. Check browser permissions.')
        setDetectingLocation(false)
      },
      { maximumAge: 60000, timeout: 10000 }
    )
  }

  const handleSubmit = async (event) => {
    event.preventDefault()

    setLoading(true)
    setMessage('')

    try {
      const result = await submitComplaint({
        customer_id: user?.id ?? 1,
        complaint_type: complaintType,
        subject,
        description,
        priority,
        latitude,
        longitude,
      })

      setMessage(
        `Complaint submitted successfully. Complaint ID: CMP-${String(
          result.complaint_id
        ).padStart(3, '0')}`
      )

      setSubject('')
      setDescription('')
      setPriority('Medium')
      setLatitude(null)
      setLongitude(null)
      setLocationMessage('')
    } catch (error) {
      setMessage('Unable to submit complaint. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="dashboard-page">
      <header className="dashboard-header">
        <Link to="/customer">← Back to Customer Dashboard</Link>

        <h1>Submit Complaint</h1>
        <p>Report an issue with your telecom service.</p>
      </header>

      <section className="complaint-form-card">
        <form onSubmit={handleSubmit}>
          <label>
            Complaint Type
            <select
              value={complaintType}
              onChange={(event) => setComplaintType(event.target.value)}
            >
              <option>Network Issue</option>
              <option>Call Issue</option>
              <option>Internet Issue</option>
              <option>Billing Issue</option>
              <option>Technical Issue</option>
              <option>Other</option>
            </select>
          </label>

          <label>
            Subject
            <input
              type="text"
              value={subject}
              onChange={(event) => setSubject(event.target.value)}
              placeholder="Enter complaint subject"
              required
            />
          </label>

          <label>
            Description
            <textarea
              rows="6"
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              placeholder="Describe your problem..."
              required
            />
          </label>

          <label>
            Priority
            <select
              value={priority}
              onChange={(event) => setPriority(event.target.value)}
            >
              <option>Low</option>
              <option>Medium</option>
              <option>High</option>
              <option>Critical</option>
            </select>
          </label>

          <button
            type="button"
            onClick={handleDetectLocation}
            disabled={detectingLocation}
          >
            {detectingLocation ? 'Detecting location...' : 'Detect My Location'}
          </button>

          <label>
            Latitude
            <input type="number" value={latitude ?? ''} readOnly />
          </label>

          <label>
            Longitude
            <input type="number" value={longitude ?? ''} readOnly />
          </label>

          {locationMessage && <p className="form-message">{locationMessage}</p>}

          <button type="submit" disabled={loading}>
            {loading ? 'Submitting...' : 'Submit Complaint'}
          </button>

          {message && (
            <p className="form-message">
              {message}
            </p>
          )}
        </form>
      </section>
    </main>
  )
}