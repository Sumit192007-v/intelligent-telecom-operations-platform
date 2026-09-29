import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { CircleMarker, MapContainer, TileLayer, Tooltip, useMap } from 'react-leaflet'
import { useAuth } from '../AuthContext'
import { getNetworkMapData, predictLatency } from '../services/api'

const statusStyles = {
  green: { fill: '#10b98188', stroke: '#059669' },
  orange: { fill: '#f59e0b88', stroke: '#d97706' },
  red: { fill: '#f43f5e99', stroke: '#e11d48' },
}

const operatorColors = {
  all: '#64748b',
  'AT&T': '#3b82f6',
  'T-Mobile': '#ec4899',
  Verizon: '#ef4444',
}

const operatorFilters = [
  { value: 'all', label: 'All Operators' },
  { value: 'AT&T', label: 'AT&T' },
  { value: 'T-Mobile', label: 'T-Mobile' },
  { value: 'Verizon', label: 'Verizon' },
]

const filters = [
  { value: 'all', label: 'All Nodes' },
  { value: 'green', label: 'Green' },
  { value: 'orange', label: 'Orange' },
  { value: 'red', label: 'Red' },
  { value: 'complaints', label: 'Complaints Only' },
]

const metroStops = [
  { label: 'Nationwide', center: [39.8, -98.5], zoom: 4 },
  { label: 'New York', center: [40.7128, -74.006], zoom: 10 },
  { label: 'Chicago', center: [41.8781, -87.6298], zoom: 10 },
  { label: 'Dallas', center: [32.7767, -96.797], zoom: 10 },
  { label: 'San Francisco', center: [37.7749, -122.4194], zoom: 10 },
  { label: 'Los Angeles', center: [34.0522, -118.2437], zoom: 10 },
]

function percentage(count, total) {
  return total ? `${((count / total) * 100).toFixed(1)}%` : '0.0%'
}

function FitMeasurementBounds({ measurements }) {
  const map = useMap()

  useEffect(() => {
    if (!measurements.length) return

    map.fitBounds(
      measurements.map((measurement) => [measurement.lat, measurement.lng]),
      { padding: [50, 50] }
    )
  }, [map, measurements])

  return null
}

function MetroFlyToControls() {
  const map = useMap()

  return (
    <nav className="metro-flyto" aria-label="Jump to network metro">
      {metroStops.map((stop) => (
        <button
          key={stop.label}
          type="button"
          onClick={() => map.flyTo(stop.center, stop.zoom, { duration: 1.6, easeLinearity: 0.25 })}
        >
          {stop.label}
        </button>
      ))}
    </nav>
  )
}

function telemetryValue(value, suffix = '') {
  return value === null || value === undefined || value === ''
    ? '—'
    : `${value}${suffix}`
}

export default function NetworkCoverageMap() {
  const { token, logout } = useAuth()
  const [measurements, setMeasurements] = useState([])
  const [statusFilter, setStatusFilter] = useState('all')
  const [operatorFilter, setOperatorFilter] = useState('all')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [retryCount, setRetryCount] = useState(0)
  const [predictions, setPredictions] = useState({})
  const [predictingId, setPredictingId] = useState(null)
  const [selectedMeasurement, setSelectedMeasurement] = useState(null)
  const [coordinatesCopied, setCoordinatesCopied] = useState(false)

  const statusCounts = measurements.reduce(
    (counts, measurement) => {
      counts[measurement.status] += 1
      return counts
    },
    { green: 0, orange: 0, red: 0 }
  )

  async function handlePredict(measurement) {
    setPredictingId(measurement.id)
    setPredictions((current) => ({ ...current, [measurement.id]: null }))
    const now = new Date()

    try {
      const result = await predictLatency({
        operator: measurement.operator,
        hour: now.getHours(),
        day_of_week: now.getDay(),
        frequency: measurement.frequency ?? 0,
        pci: measurement.pci ?? 0,
        earfcn: measurement.earfcn ?? 0,
      }, token)
      setPredictions((current) => ({
        ...current,
        [measurement.id]: { result },
      }))
    } catch {
      setPredictions((current) => ({
        ...current,
        [measurement.id]: { error: 'Prediction unavailable.' },
      }))
    } finally {
      setPredictingId(null)
    }
  }

  async function handleCopyCoordinates() {
    if (!selectedMeasurement) return

    try {
      await navigator.clipboard.writeText(
        `${selectedMeasurement.lat}, ${selectedMeasurement.lng}`
      )
      setCoordinatesCopied(true)
      window.setTimeout(() => setCoordinatesCopied(false), 1600)
    } catch {
      setCoordinatesCopied(false)
    }
  }

  useEffect(() => {
    let active = true

    async function loadMapData() {
      if (!token) {
        setError('session')
        setMeasurements([])
        setLoading(false)
        return
      }

      setLoading(true)
      setError('')
      try {
        const data = await getNetworkMapData(token)
        if (active) setMeasurements(data)
      } catch (requestError) {
        if (!active) return
        setMeasurements([])
        if (requestError.status === 401) {
          setError('session')
          logout()
        } else {
          setError('offline')
        }
      } finally {
        if (active) setLoading(false)
      }
    }

    loadMapData()
    return () => {
      active = false
    }
  }, [token, retryCount])

  useEffect(() => {
    if (!selectedMeasurement) return undefined

    function handleEscape(event) {
      if (event.key === 'Escape') setSelectedMeasurement(null)
    }

    window.addEventListener('keydown', handleEscape)
    return () => window.removeEventListener('keydown', handleEscape)
  }, [selectedMeasurement])

  const visibleMeasurements = measurements.filter((measurement) => {
    const matchesStatus = statusFilter === 'complaints'
      ? measurement.complaints > 0
      : statusFilter === 'all' || measurement.status === statusFilter
    const matchesOperator = operatorFilter === 'all'
      || measurement.operator === operatorFilter
    return matchesStatus && matchesOperator
  })

  return (
    <section className="coverage-map-section" aria-labelledby="coverage-map-title">
      <div className="coverage-map-header">
        <div>
          <h2 id="coverage-map-title">Network Coverage</h2>
          <p>{loading ? 'Loading live telemetry...' : `${visibleMeasurements.length.toLocaleString()} visible nodes`}</p>
        </div>
        <span className={`coverage-map-live ${error ? 'offline' : ''}`}>
          {error ? 'DEGRADED' : 'LIVE'}
        </span>
      </div>

      <div className="operations-marquee" aria-label="Live network telemetry">
        <div className="operations-marquee-track">
          <span>[LIVE TELEMETRY] • 4,500 Multi-Carrier Nodes Online • US-East Cluster RTT: 28.4ms (Normal) • Carrier Distribution: AT&amp;T (34.4%), T-Mobile (32.5%), Verizon (33.1%) • Active Automated Dispatch Engine: ACTIVE</span>
          <span aria-hidden="true">[LIVE TELEMETRY] • 4,500 Multi-Carrier Nodes Online • US-East Cluster RTT: 28.4ms (Normal) • Carrier Distribution: AT&amp;T (34.4%), T-Mobile (32.5%), Verizon (33.1%) • Active Automated Dispatch Engine: ACTIVE</span>
        </div>
      </div>

      <div className="coverage-map-stage">
        <MapContainer
          className="coverage-map"
          center={[39.8, -98.5]}
          zoom={4}
          scrollWheelZoom
          preferCanvas={true}
        >
          <FitMeasurementBounds measurements={measurements} />
          <MetroFlyToControls />
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          {visibleMeasurements.map((measurement) => {
            const style = statusStyles[measurement.status]

            return (
              <CircleMarker
                key={measurement.id}
                center={[measurement.lat, measurement.lng]}
                radius={measurement.status === 'red' ? 7 : measurement.status === 'green' ? 5 : 6}
                pathOptions={{
                  color: style.stroke,
                  fillColor: style.fill,
                  fillOpacity: 0.9,
                  weight: 1.5,
                }}
                eventHandlers={{
                  click: () => {
                    setSelectedMeasurement(measurement)
                    setCoordinatesCopied(false)
                  },
                }}
              >
                <Tooltip direction="top" offset={[0, -6]} sticky>
                  {measurement.operator} • Latency {measurement.latency.toFixed(1)} ms • {measurement.status}
                </Tooltip>
              </CircleMarker>
            )
          })}
        </MapContainer>

        {error && (
          <div className="telemetry-recovery-overlay" role="alert">
            <span className="telemetry-kicker">
              {error === 'session' ? 'AUTHENTICATION REQUIRED' : 'UPSTREAM CONNECTION'}
            </span>
            <h3>
              {error === 'session'
                ? 'Session Expired: Please re-authenticate to stream live telemetry.'
                : 'Telemetry Service Offline: Ensure FastAPI is running on port 8000.'}
            </h3>
            <p>
              {error === 'session'
                ? 'Your live session is no longer valid.'
                : 'The live node stream could not be reached.'}
            </p>
            {error === 'session' ? (
              <Link className="telemetry-recovery-action" to="/login">
                Sign In Again
              </Link>
            ) : (
              <button
                type="button"
                className="telemetry-recovery-action"
                onClick={() => setRetryCount((attempt) => attempt + 1)}
              >
                Retry Connection
              </button>
            )}
          </div>
        )}

        <aside
          className={`telemetry-drawer ${selectedMeasurement ? 'open' : ''}`}
          aria-label="Node telemetry inspector"
          aria-hidden={!selectedMeasurement}
        >
          {selectedMeasurement && (
            <div className="telemetry-drawer-content" key={selectedMeasurement.id}>
              <header className="telemetry-drawer-header">
                <div>
                  <span className="telemetry-kicker">SECTOR INSPECTOR</span>
                  <h3>{selectedMeasurement.operator}</h3>
                </div>
                <button
                  type="button"
                  className="telemetry-close"
                  aria-label="Close telemetry inspector"
                  onClick={() => setSelectedMeasurement(null)}
                >
                  ✕
                </button>
              </header>

              <div className="telemetry-carrier-row">
                <span
                  className="telemetry-carrier-badge"
                  style={{ '--operator-color': operatorColors[selectedMeasurement.operator] || '#64748b' }}
                >
                  {selectedMeasurement.operator}
                </span>
                <span className={`coverage-map-status status-${selectedMeasurement.status}`}>
                  {selectedMeasurement.status}
                </span>
              </div>

              <section className="telemetry-section">
                <div className="telemetry-section-heading">
                  <span>Signal latency</span>
                  <strong>{selectedMeasurement.latency.toFixed(1)} <small>ms</small></strong>
                </div>
                <div className={`latency-meter status-${selectedMeasurement.status}`}>
                  <span style={{ width: `${Math.min(selectedMeasurement.latency, 100)}%` }} />
                  <i className="threshold threshold-50" />
                  <i className="threshold threshold-75" />
                </div>
                <div className="latency-thresholds">
                  <span>0 ms</span><span>50 ms warning</span><span>75 ms critical</span>
                </div>
              </section>

              <section className="telemetry-section">
                <div className="telemetry-section-heading">
                  <span>RF telemetry</span>
                  <span className="telemetry-complaints">{selectedMeasurement.complaints} open complaints</span>
                </div>
                <div className="telemetry-grid">
                  <div><span>5G frequency</span><strong>{telemetryValue(selectedMeasurement.frequency, ' MHz')}</strong></div>
                  <div><span>PCI</span><strong>{telemetryValue(selectedMeasurement.pci)}</strong></div>
                  <div><span>LTE EARFCN</span><strong>{telemetryValue(selectedMeasurement.earfcn)}</strong></div>
                  <div><span>Latitude</span><strong>{Number(selectedMeasurement.lat).toFixed(5)}</strong></div>
                  <div><span>Longitude</span><strong>{Number(selectedMeasurement.lng).toFixed(5)}</strong></div>
                </div>
                <button type="button" className="copy-coordinates" onClick={handleCopyCoordinates}>
                  {coordinatesCopied ? 'Coordinates copied' : 'Copy Coordinates'}
                </button>
              </section>

              <section className="telemetry-action-panel">
                <span className="telemetry-kicker">PREDICTIVE ANALYSIS</span>
                <button
                  type="button"
                  className="coverage-map-predict-button"
                  disabled={predictingId === selectedMeasurement.id}
                  onClick={() => handlePredict(selectedMeasurement)}
                >
                  {predictingId === selectedMeasurement.id ? 'Calculating forecast…' : 'Run ML Latency Forecast'}
                </button>
                {predictions[selectedMeasurement.id]?.result && (
                  <span
                    className={`coverage-map-prediction ${
                      predictions[selectedMeasurement.id].result.prediction === 'Elevated Latency'
                        ? 'elevated'
                        : 'normal'
                    }`}
                  >
                    {predictions[selectedMeasurement.id].result.prediction === 'Elevated Latency'
                      ? 'Elevated (>= 75 ms)'
                      : 'Normal (< 75 ms)'}
                  </span>
                )}
                {predictions[selectedMeasurement.id]?.error && (
                  <span className="coverage-map-prediction-error">
                    {predictions[selectedMeasurement.id].error}
                  </span>
                )}
              </section>
            </div>
          )}
        </aside>

        <aside className="coverage-map-hud" aria-label="Live network operations">
          <div className="coverage-map-hud-heading">
            <span>NETWORK OPERATIONS</span>
            <span className="coverage-map-hud-live"><i /> LIVE</span>
          </div>
          <div className="coverage-map-metrics">
            <div className="coverage-map-metric total">
              <strong>{measurements.length.toLocaleString()}</strong>
              <span>Total nodes monitored</span>
            </div>
            <div className="coverage-map-metric green">
              <strong>{percentage(statusCounts.green, measurements.length)}</strong>
              <span>Optimal</span>
            </div>
            <div className="coverage-map-metric orange">
              <strong>{percentage(statusCounts.orange, measurements.length)}</strong>
              <span>Warning</span>
            </div>
            <div className="coverage-map-metric red">
              <strong>{percentage(statusCounts.red, measurements.length)}</strong>
              <span>Degraded</span>
            </div>
          </div>
          <div
            className="coverage-map-spectrum"
            role="img"
            aria-label={`Latency spectrum: ${percentage(statusCounts.green, measurements.length)} optimal, ${percentage(statusCounts.orange, measurements.length)} warning, ${percentage(statusCounts.red, measurements.length)} degraded`}
          >
            <span className="optimal" style={{ width: percentage(statusCounts.green, measurements.length) }} />
            <span className="warning" style={{ width: percentage(statusCounts.orange, measurements.length) }} />
            <span className="degraded" style={{ width: percentage(statusCounts.red, measurements.length) }} />
          </div>
          <div className="coverage-map-filters" role="group" aria-label="Filter network nodes">
            {filters.map((filter) => (
              <button
                key={filter.value}
                type="button"
                className={statusFilter === filter.value ? 'active' : ''}
                aria-pressed={statusFilter === filter.value}
                onClick={() => setStatusFilter(filter.value)}
              >
                {filter.label}
              </button>
            ))}
          </div>
          <div className="coverage-map-operator-filters" role="group" aria-label="Filter operators">
            {operatorFilters.map((filter) => (
              <button
                key={filter.value}
                type="button"
                className={operatorFilter === filter.value ? 'active' : ''}
                style={{ '--operator-filter-color': operatorColors[filter.value] }}
                aria-pressed={operatorFilter === filter.value}
                onClick={() => setOperatorFilter(filter.value)}
              >
                {filter.label}
              </button>
            ))}
          </div>
        </aside>
      </div>
    </section>
  )
}