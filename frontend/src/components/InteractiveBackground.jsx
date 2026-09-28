import { useEffect, useRef } from 'react'

const PARTICLE_COUNT = 280
const CONNECTION_RADIUS = 85
const CURSOR_TETHER_RADIUS = 130
const REPEL_RADIUS = 180
const PALETTE = ['#38bdf8', '#a855f7', '#f43f5e', '#10b981', '#fbbf24']

export default function InteractiveBackground() {
  const canvasRef = useRef(null)

  useEffect(() => {
    const canvas = canvasRef.current
    const context = canvas?.getContext('2d')
    if (!canvas || !context) return undefined

    let width = 0
    let height = 0
    let pixelRatio = 1
    let animationFrame = 0
    let previousFrame = 0
    const mouse = { x: -1000, y: -1000 }
    const particles = Array.from({ length: PARTICLE_COUNT }, () => {
      const x = Math.random() * window.innerWidth
      const y = Math.random() * window.innerHeight
      const colorIndex = Math.floor(Math.random() * PALETTE.length)
      const opacity = 0.25 + Math.random() * 0.45
      return {
        x,
        y,
        originX: x,
        originY: y,
        vx: 0,
        vy: 0,
        driftX: (Math.random() - 0.5) * 0.06,
        driftY: (Math.random() - 0.5) * 0.06,
        radius: 1.2 + Math.random() * 2,
        opacity,
        opacityBucket: Math.min(5, Math.round((opacity - 0.25) / 0.09)),
        colorIndex,
        color: PALETTE[colorIndex],
      }
    })

    function resizeCanvas() {
      const nextWidth = window.innerWidth
      const nextHeight = window.innerHeight
      if (width && height) {
        const scaleX = nextWidth / width
        const scaleY = nextHeight / height
        for (const particle of particles) {
          particle.x *= scaleX
          particle.originX *= scaleX
          particle.y *= scaleY
          particle.originY *= scaleY
        }
      }

      width = nextWidth
      height = nextHeight
      pixelRatio = Math.min(window.devicePixelRatio || 1, 1.25)
      canvas.width = Math.round(width * pixelRatio)
      canvas.height = Math.round(height * pixelRatio)
      context.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0)
    }

    function handleMouseMove(event) {
      mouse.x = event.clientX
      mouse.y = event.clientY
    }

    function clearMouse() {
      mouse.x = -1000
      mouse.y = -1000
    }

    function drawFrame(timestamp) {
      const frameScale = previousFrame
        ? Math.min((timestamp - previousFrame) / 16.67, 2)
        : 1
      previousFrame = timestamp
      context.clearRect(0, 0, width, height)

      const spatialGrid = new Map()
      for (let index = 0; index < particles.length; index += 1) {
        const particle = particles[index]
        const cellX = Math.floor(particle.x / CONNECTION_RADIUS)
        const cellY = Math.floor(particle.y / CONNECTION_RADIUS)
        const key = `${cellX},${cellY}`
        const cell = spatialGrid.get(key)
        if (cell) cell.push(index)
        else spatialGrid.set(key, [index])
      }

      context.beginPath()
      for (let first = 0; first < particles.length; first += 1) {
        const particle = particles[first]
        const cellX = Math.floor(particle.x / CONNECTION_RADIUS)
        const cellY = Math.floor(particle.y / CONNECTION_RADIUS)
        for (let offsetX = -1; offsetX <= 1; offsetX += 1) {
          for (let offsetY = -1; offsetY <= 1; offsetY += 1) {
            const neighbors = spatialGrid.get(`${cellX + offsetX},${cellY + offsetY}`)
            if (!neighbors) continue

            for (const second of neighbors) {
              if (second <= first) continue
              const other = particles[second]
              const deltaX = other.x - particle.x
              const deltaY = other.y - particle.y
              const distanceSquared = deltaX * deltaX + deltaY * deltaY
              if (distanceSquared < CONNECTION_RADIUS * CONNECTION_RADIUS) {
                context.moveTo(particle.x, particle.y)
                context.lineTo(other.x, other.y)
              }
            }
          }
        }
      }

      for (const particle of particles) {
        const deltaX = particle.x - mouse.x
        const deltaY = particle.y - mouse.y
        if (deltaX * deltaX + deltaY * deltaY < CURSOR_TETHER_RADIUS * CURSOR_TETHER_RADIUS) {
          context.moveTo(mouse.x, mouse.y)
          context.lineTo(particle.x, particle.y)
        }
      }

      context.globalAlpha = 0.05
      context.strokeStyle = '#7dd3fc'
      context.lineWidth = 0.5
      context.stroke()

      const dotBuckets = Array.from({ length: PALETTE.length * 6 }, () => [])
      for (const particle of particles) {
        const deltaX = particle.x - mouse.x
        const deltaY = particle.y - mouse.y
        const distance = Math.sqrt(deltaX * deltaX + deltaY * deltaY)

        if (distance < REPEL_RADIUS) {
          const safeDistance = Math.max(distance, 0.01)
          const force = Math.exp(-(distance / REPEL_RADIUS) * 4.5) * 0.7 * frameScale
          particle.vx += (deltaX / safeDistance) * force
          particle.vy += (deltaY / safeDistance) * force
        }

        particle.driftX = Math.max(-0.06, Math.min(0.06, particle.driftX + (Math.random() - 0.5) * 0.002 * frameScale))
        particle.driftY = Math.max(-0.06, Math.min(0.06, particle.driftY + (Math.random() - 0.5) * 0.002 * frameScale))
        particle.vx += particle.driftX * frameScale
        particle.vy += particle.driftY * frameScale
        particle.vx += (particle.originX - particle.x) * 0.00035 * frameScale
        particle.vy += (particle.originY - particle.y) * 0.00035 * frameScale
        const damping = Math.pow(0.92, frameScale)
        particle.vx *= damping
        particle.vy *= damping
        particle.x += particle.vx * frameScale
        particle.y += particle.vy * frameScale

        dotBuckets[particle.colorIndex * 4 + particle.opacityBucket].push(
          particle.x,
          particle.y,
          particle.radius
        )
      }

      for (let colorIndex = 0; colorIndex < PALETTE.length; colorIndex += 1) {
        for (let opacityBucket = 0; opacityBucket < 6; opacityBucket += 1) {
          const dots = dotBuckets[colorIndex * 6 + opacityBucket]
          if (!dots.length) continue
          context.globalAlpha = 0.25 + opacityBucket * 0.09
          context.fillStyle = PALETTE[colorIndex]
          context.shadowBlur = 0
          context.beginPath()
          for (let index = 0; index < dots.length; index += 3) {
            context.moveTo(dots[index] + dots[index + 2], dots[index + 1])
            context.arc(dots[index], dots[index + 1], dots[index + 2], 0, Math.PI * 2)
          }
          context.fill()
        }
      }

      context.globalAlpha = 1
      context.shadowBlur = 0
      animationFrame = window.requestAnimationFrame(drawFrame)
    }

    resizeCanvas()
    window.addEventListener('mousemove', handleMouseMove, { passive: true })
    window.addEventListener('blur', clearMouse)
    window.addEventListener('resize', resizeCanvas, { passive: true })
    animationFrame = window.requestAnimationFrame(drawFrame)

    return () => {
      window.removeEventListener('mousemove', handleMouseMove)
      window.removeEventListener('blur', clearMouse)
      window.removeEventListener('resize', resizeCanvas)
      window.cancelAnimationFrame(animationFrame)
    }
  }, [])

  return <canvas ref={canvasRef} className="interactive-background-canvas" aria-hidden="true" />
}