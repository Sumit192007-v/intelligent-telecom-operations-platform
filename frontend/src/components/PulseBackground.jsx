import React, { useEffect } from 'react'

const EMITTERS = [
  { x: '10%', y: '18%', c: '#22d3ee', d: '0s' },
  { x: '88%', y: '12%', c: '#a78bfa', d: '-2s' },
  { x: '72%', y: '80%', c: '#f472b6', d: '-4s' },
  { x: '20%', y: '88%', c: '#fbbf24', d: '-1s' },
  { x: '52%', y: '46%', c: '#34d399', d: '-5s' },
]
const RIPPLE_COLORS = ['#22d3ee', '#a78bfa', '#f472b6', '#fbbf24', '#34d399']

export default function PulseBackground() {
  useEffect(() => {
    let n = 0
    function ripple(event) {
      const el = document.createElement('span')
      el.className = 'click-ripple'
      el.style.left = `${event.clientX}px`
      el.style.top = `${event.clientY}px`
      el.style.setProperty('--c', RIPPLE_COLORS[n++ % RIPPLE_COLORS.length])
      el.addEventListener('animationend', () => el.remove())
      document.body.appendChild(el)
    }
    window.addEventListener('pointerdown', ripple)
    return () => window.removeEventListener('pointerdown', ripple)
  }, [])

  return (
    <div className="pulse-bg" aria-hidden="true">
      {EMITTERS.map((e) => (
        <div
          key={e.x + e.y}
          className="pulse-emitter"
          style={{ left: e.x, top: e.y, '--c': e.c, '--d': e.d }}
        >
          <span className="pulse-ring" />
          <span className="pulse-ring" />
          <span className="pulse-ring" />
        </div>
      ))}
    </div>
  )
}
