import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { CircleMarker, MapContainer, Popup, TileLayer, Tooltip, useMap } from 'react-leaflet'
import { useAuth } from '../AuthContext'
import { getNetworkMapData, predictLatency } from '../services/api'

const statusStyles = {
  green: { fill: '#10b98188', stroke: '#059669' },
  orange: { fill: '#f59e0b88', stroke: '#d97706' },
  red: { fill: '#f43f5e99', stroke: '#e11d48' },
}

const operatorColors = {
  all: '#64748b',
  'AT&T': '#2563eb',
  'T-Mobile': '#db2777',
  Verizon: '#dc2626',
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

export default function NetworkCoverageMap() {
  const { token } = useAuth()
  const [measurements, setMeasurements] = useState([])
  const [statusFilter, setStatusFilter] = useState('all')
  const [operatorFilter, setOperatorFilter] = useState('all')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [predictions, setPredictions] = useState({})
  const [predictingId, setPredictingId] = useState(null)

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
      })
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

  useEffect(() => {
    let active = true

    async function loadMapData() {
      if (!token) {
        setError('Sign in to view network coverage.')
        setLoading(false)
        return
      }

      try {
        const data = await getNetworkMapData(token)
        if (active) setMeasurements(data)
      } catch {
        if (active) setError('Unable to load network map data.')
      } finally {
        if (active) setLoading(false)
      }
    }

    loadMapData()
    return () => {
      active = false
    }
  }, [token])

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

      {error && (
        <p className="coverage-map-error">
          {error} {!token && <Link to="/login">Staff sign in</Link>}
        </p>
      )}

      <div className="coverage-map-stage">
        <MapContainer
          className="coverage-map"
          center={[39.8, -98.5]}
          zoom={4}
          scrollWheelZoom
          preferCanvas={true}
        >
          <FitMeasurementBounds measurements={measurements} />
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          {visibleMeasurements.map((measurement) => {
            const style = statusStyles[measurement.status]
            const prediction = predictions[measurement.id]
            const elevated = prediction?.result?.prediction === 'Elevated Latency'

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
              >
                <Tooltip direction="top" offset={[0, -6]} sticky>
                  {measurement.operator} • Latency {measurement.latency.toFixed(1)} ms • {measurement.status}
                </Tooltip>
                <Popup>
                  <div className="coverage-map-popup">
                    <div className="coverage-map-popup-heading">
                      <span
                        className="coverage-map-operator"
                        style={{ '--operator-color': operatorColors[measurement.operator] || '#475569' }}
                      >
                        {measurement.operator}
                      </span>
                      <span className={`coverage-map-status status-${measurement.status}`}>
                        {measurement.status}
                      </span>
                    </div>
                    <table className="coverage-map-popup-table">
                      <tbody>
                        <tr><th>RTT latency</th><td>{measurement.latency.toFixed(1)} ms</td></tr>
                        <tr><th>Open sector complaints</th><td>{measurement.complaints}</td></tr>
                      </tbody>
                    </table>
                    <button
                      type="button"
                      className="coverage-map-predict-button"
                      disabled={predictingId === measurement.id}
                      onClick={() => handlePredict(measurement)}
                    >
                      {predictingId === measurement.id ? 'Forecasting...' : 'Run ML Latency Forecast'}
                    </button>
                    {prediction?.result && (
                      <span className={`coverage-map-prediction ${elevated ? 'elevated' : 'normal'}`}>
                        {elevated ? 'Elevated (>= 75 ms)' : 'Normal (< 75 ms)'}
                      </span>
                    )}
                    {prediction?.error && (
                      <span className="coverage-map-prediction-error">{prediction.error}</span>
                    )}
                  </div>
                </Popup>
              </CircleMarker>
            )
          })}
        </MapContainer>

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