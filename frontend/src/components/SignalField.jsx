import { useEffect, useRef } from 'react'
import { startSignalField } from './signalField.js'

export default function SignalField() {
  const canvasRef = useRef(null)
  const readoutRef = useRef(null)

  useEffect(() => startSignalField(canvasRef.current, readoutRef.current), [])

  return (
    <figure className="signal-field">
      <canvas ref={canvasRef} aria-hidden="true" />
      <figcaption ref={readoutRef} className="signal-readout" />
    </figure>
  )
}
