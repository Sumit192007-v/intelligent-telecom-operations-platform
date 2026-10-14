// Animated tower network for the home page. Plain canvas, no dependencies.
const RGB = { ok: '62,224,207', slow: '255,181,71', down: '255,93,93' }

export function startSignalField(canvas, readout) {
  const ctx = canvas.getContext('2d')
  const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches
  let w = 0, h = 0, raf = 0, last = performance.now(), clock = 0
  let towers = [], links = [], packets = [], rings = []
  let nextPulse = 0.6, nextTrouble = 2.5, lastHover = 0

  function say(text) {
    if (readout) readout.textContent = text
  }

  function layout() {
    const dpr = Math.min(window.devicePixelRatio || 1, 2)
    const box = canvas.getBoundingClientRect()
    w = box.width
    h = box.height
    canvas.width = Math.round(w * dpr)
    canvas.height = Math.round(h * dpr)
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0)

    let seed = 11
    const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647
    const cols = w < 420 ? 4 : 6
    const rows = 5
    towers = []
    for (let j = 0; j < rows; j++) {
      for (let i = 0; i < cols; i++) {
        const shift = j % 2 ? 0.5 : 0
        towers.push({
          id: towers.length + 1,
          x: ((i + shift + 0.5 + (rnd() - 0.5) * 0.35) / (cols + 0.5)) * w,
          y: 22 + ((j + 0.5 + (rnd() - 0.5) * 0.35) / rows) * (h - 22 - 66),
          state: 'ok',
          until: 0,
          ms: 24 + Math.round(rnd() * 18),
        })
      }
    }
    const reach = Math.max(w, h) / (cols + 0.5) * 1.35
    links = []
    towers.forEach((a, i) => {
      towers.slice(i + 1).forEach((b) => {
        if (Math.hypot(a.x - b.x, a.y - b.y) < reach) links.push({ a, b })
      })
    })
    packets = []
    rings = []
  }

  function ring(tower, rgb, size = 1) {
    rings.push({ x: tower.x, y: tower.y, r: 4, max: 70 * size + Math.min(w, h) * 0.08, rgb })
  }

  function step(dt) {
    clock += dt
    if (clock > nextPulse) {
      nextPulse = clock + 1.4 + Math.random() * 1.6
      const t = towers[Math.floor(Math.random() * towers.length)]
      ring(t, RGB[t.state])
    }
    if (clock > nextTrouble) {
      nextTrouble = clock + 5 + Math.random() * 3
      const t = towers[Math.floor(Math.random() * towers.length)]
      if (t.state === 'ok') {
        t.state = Math.random() < 0.3 ? 'down' : 'slow'
        t.until = clock + 4.5
        t.ms = t.state === 'down' ? 0 : 78 + Math.round(Math.random() * 40)
        ring(t, RGB[t.state], 1.6)
        say(
          t.state === 'down'
            ? `Tower T-${t.id} is down. Nearby complaints are flagged.`
            : `Tower T-${t.id} slowed to ${t.ms} ms. Latency model marks it high risk.`
        )
      }
    }
    towers.forEach((t) => {
      if (t.state !== 'ok' && clock > t.until) {
        t.state = 'ok'
        t.ms = 24 + Math.round(Math.random() * 18)
        ring(t, RGB.ok, 1.2)
        say(`Tower T-${t.id} recovered at ${t.ms} ms.`)
      }
      if (t.state !== 'ok' && Math.random() < dt * 1.2) ring(t, RGB[t.state], 0.7)
    })
    if (packets.length < 16 && Math.random() < dt * 7 && links.length) {
      const link = links[Math.floor(Math.random() * links.length)]
      packets.push({ link, t: 0, dir: Math.random() < 0.5 ? 1 : -1, speed: 0.35 + Math.random() * 0.4 })
    }
    packets = packets.filter((p) => (p.t += p.speed * dt) < 1)
    rings = rings.filter((r) => (r.r += dt * (28 + r.max * 0.55)) < r.max)
  }

  function draw() {
    ctx.clearRect(0, 0, w, h)
    ctx.lineWidth = 1
    links.forEach(({ a, b }) => {
      const bad = a.state !== 'ok' || b.state !== 'ok'
      ctx.strokeStyle = bad ? 'rgba(255,181,71,0.18)' : 'rgba(120,170,200,0.12)'
      ctx.beginPath()
      ctx.moveTo(a.x, a.y)
      ctx.lineTo(b.x, b.y)
      ctx.stroke()
    })
    rings.forEach((r) => {
      const alpha = 0.55 * (1 - r.r / r.max)
      ctx.strokeStyle = `rgba(${r.rgb},${alpha.toFixed(3)})`
      ctx.lineWidth = 1.5
      ctx.beginPath()
      ctx.arc(r.x, r.y, r.r, 0, Math.PI * 2)
      ctx.stroke()
    })
    packets.forEach((p) => {
      const from = p.dir > 0 ? p.link.a : p.link.b
      const to = p.dir > 0 ? p.link.b : p.link.a
      const slow = from.state !== 'ok' || to.state !== 'ok'
      const k = slow ? p.t * 0.9 : p.t
      ctx.fillStyle = `rgba(${slow ? RGB.slow : RGB.ok},0.95)`
      ctx.beginPath()
      ctx.arc(from.x + (to.x - from.x) * k, from.y + (to.y - from.y) * k, 2.2, 0, Math.PI * 2)
      ctx.fill()
    })
    towers.forEach((t) => {
      const rgb = RGB[t.state]
      ctx.fillStyle = `rgba(${rgb},0.16)`
      ctx.beginPath()
      ctx.arc(t.x, t.y, 11, 0, Math.PI * 2)
      ctx.fill()
      ctx.fillStyle = `rgb(${rgb})`
      ctx.beginPath()
      ctx.arc(t.x, t.y, 3.6, 0, Math.PI * 2)
      ctx.fill()
    })
  }

  function frame(now) {
    const dt = Math.min(0.05, (now - last) / 1000)
    last = now
    step(dt)
    draw()
    raf = requestAnimationFrame(frame)
  }

  function onMove(event) {
    const now = performance.now()
    if (now - lastHover < 350) return
    const box = canvas.getBoundingClientRect()
    const x = event.clientX - box.left
    const y = event.clientY - box.top
    let best = null
    let bestDistance = 70
    towers.forEach((t) => {
      const d = Math.hypot(t.x - x, t.y - y)
      if (d < bestDistance) {
        best = t
        bestDistance = d
      }
    })
    if (best) {
      lastHover = now
      ring(best, RGB[best.state], 1.3)
      say(
        best.state === 'down'
          ? `Tower T-${best.id} is down.`
          : `Tower T-${best.id}: ${best.ms} ms round trip.`
      )
    }
  }

  layout()
  say('Live view of a sample tower network. Move over a tower to read it.')
  if (reduce) {
    towers.slice(0, 6).forEach((t) => ring(t, RGB.ok))
    rings.forEach((r) => (r.r = r.max * 0.45))
    draw()
  } else {
    raf = requestAnimationFrame(frame)
    canvas.addEventListener('pointermove', onMove)
  }
  const observer = new ResizeObserver(() => {
    layout()
    if (reduce) draw()
  })
  observer.observe(canvas)

  return () => {
    cancelAnimationFrame(raf)
    observer.disconnect()
    canvas.removeEventListener('pointermove', onMove)
  }
}
