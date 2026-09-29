import { useEffect, useState } from 'react'
import {
  getNetworkMeasurements,
  predictLatency,
} from '../../services/api'
import NetworkCoverageMap from '../../components/NetworkCoverageMap'
import { useAuth } from '../../AuthContext'

function NetworkInsights() {
  const { token } = useAuth()
  const [measurements, setMeasurements] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [prediction, setPrediction] = useState(null)
  const [predictionError, setPredictionError] = useState('')
  const [selectedOperator, setSelectedOperator] = useState('AT&T')

  useEffect(() => {
    async function loadMeasurements() {
      try {
        setLoading(true)
        setError('')

        // Load measurements for ALL operators
        const data = await getNetworkMeasurements(token)

        setMeasurements(data)
      } catch (err) {
        setError('Unable to load network measurements.')
      } finally {
        setLoading(false)
      }
    }

    loadMeasurements()
  }, [token])

  async function handlePrediction() {
    setPredictionError('')
    setPrediction(null)

    // Find real measurements for the selected operator
    const operatorMeasurements = measurements.filter(
      (measurement) =>
        measurement.operator === selectedOperator
    )

    if (operatorMeasurements.length === 0) {
      setPredictionError(
        `No ${selectedOperator} measurement available.`
      )
      return
    }

    // Use the latest measurement for that operator
    const measurement =
  operatorMeasurements[
    Math.floor(
      Math.random() * operatorMeasurements.length
    )
  ]

    const date = new Date(measurement.timestamp)

    try {
      const result = await predictLatency({
        operator: measurement.operator,
        hour: date.getHours(),
        day_of_week: date.getDay(),
        five_g_frequency_mhz:
          measurement['5g_frequency_mhz'],
        five_g_pci:
          measurement['5g_pci'],
        lte_earfcn:
          measurement.lte_earfcn,
      }, token)

      setPrediction({
        ...result,
        measurement,
      })
    } catch (err) {
      setPredictionError(
        'Unable to get ML prediction.'
      )
    }
  }

  return (
    <div className="complaints-page">

      {/* Page Header */}

      <div className="complaints-header">
        <div>
          <h1>Network Insights</h1>

          <p>
            Real network measurements from the telecom dataset.
          </p>
        </div>
      </div>

      <NetworkCoverageMap />

      {/* ML Prediction */}

      <div className="prediction-card">

        <h2>ML Latency Prediction</h2>

        <p>
          Select an operator to predict elevated latency
          using a real network measurement.
        </p>

        <div className="complaint-form-group">

          <label>Select Operator</label>

          <select
            value={selectedOperator}
            onChange={(e) => {
              setSelectedOperator(e.target.value)
              setPrediction(null)
              setPredictionError('')
            }}
          >
            <option value="AT&T">AT&T</option>
            <option value="T-Mobile">T-Mobile</option>
            <option value="Verizon">Verizon</option>
          </select>

        </div>

        <button onClick={handlePrediction}>
          Run Prediction
        </button>

        {prediction && (
          <div className="prediction-result">

            <p>
              Based on measurement:{' '}
              <strong>
                {prediction.measurement.operator}
              </strong>
            </p>

            <p>
              RTT:{' '}
              {prediction.measurement.rtt_ms} ms
            </p>

            <p>
              Download:{' '}
              {prediction.measurement.download_mbps} Mbps
            </p>

            <p>
              Upload:{' '}
              {prediction.measurement.upload_mbps} Mbps
            </p>

            <hr />

            <strong
  className={
    prediction.prediction === 'Elevated Latency'
      ? 'latency-elevated'
      : 'latency-normal'
  }
>
  Latency Status: {prediction.prediction}
</strong>

            <p>
              Probability:{' '}
              {(prediction.probability * 100).toFixed(2)}%
            </p>

            <p>
              Threshold:{' '}
              {prediction.threshold}
            </p>

          </div>
        )}

        {predictionError && (
          <p className="complaints-error">
            {predictionError}
          </p>
        )}

      </div>

      {/* ALL Network Measurements */}

      <div className="network-measurements-table">

        <table>

          <thead>
            <tr>
              <th>Operator</th>
              <th>Timestamp</th>
              <th>Download</th>
              <th>Upload</th>
              <th>RTT</th>
              <th>Latitude</th>
              <th>Longitude</th>
            </tr>
          </thead>

          <tbody>

            {measurements.map((measurement) => (
              <tr key={measurement.id}>

                <td>
                  {measurement.operator}
                </td>

                <td>
                  {new Date(
                    measurement.timestamp
                  ).toLocaleString()}
                </td>

                <td>
                  {measurement.download_mbps} Mbps
                </td>

                <td>
                  {measurement.upload_mbps} Mbps
                </td>

                <td>
                  {measurement.rtt_ms} ms
                </td>

                <td>
                  {measurement.latitude}
                </td>

                <td>
                  {measurement.longitude}
                </td>

              </tr>
            ))}

          </tbody>

        </table>

      </div>

    </div>
  )
}

export default NetworkInsights