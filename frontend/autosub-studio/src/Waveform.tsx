import { useEffect, useRef, useState } from 'react'

export function Waveform({ src, duration, currentTime, onSeek }: {
  src: string; duration: number; currentTime: number; onSeek: (seconds: number) => void
}) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [samples, setSamples] = useState<number[]>([])

  useEffect(() => {
    if (!src) { setSamples([]); return }
    const controller = new AbortController(); let context: AudioContext | undefined
    void (async () => {
      try {
        const response = await fetch(src, { signal: controller.signal })
        if (!response.ok) return
        context = new AudioContext()
        const buffer = await context.decodeAudioData(await response.arrayBuffer())
        const channel = buffer.getChannelData(0); const bins = 360
        const block = Math.max(1, Math.floor(channel.length / bins)); const next:number[] = []
        for (let i=0; i<bins; i += 1) {
          let peak = 0; const start = i * block; const end = Math.min(channel.length, start + block)
          for (let j=start; j<end; j += 1) peak = Math.max(peak, Math.abs(channel[j]))
          next.push(peak)
        }
        if (!controller.signal.aborted) setSamples(next)
      } catch { /* Some browser codecs cannot be decoded by WebAudio; cue lane remains usable. */ }
      finally { void context?.close() }
    })()
    return () => controller.abort()
  }, [src])

  useEffect(() => {
    const canvas = canvasRef.current; if (!canvas) return
    const scale = window.devicePixelRatio || 1; const rect = canvas.getBoundingClientRect()
    canvas.width = Math.max(1, Math.round(rect.width * scale)); canvas.height = Math.max(1, Math.round(rect.height * scale))
    const context = canvas.getContext('2d'); if (!context) return
    context.scale(scale, scale); context.clearRect(0, 0, rect.width, rect.height)
    context.fillStyle = '#11151a'; context.fillRect(0, 0, rect.width, rect.height)
    const values = samples.length ? samples : Array.from({length:180}, (_, index) => .12 + ((index * 17) % 13) / 65)
    const step = rect.width / values.length; context.fillStyle = samples.length ? '#8f353b' : '#333941'
    values.forEach((value, index) => { const height = Math.max(2, value * rect.height * .9)
      context.fillRect(index * step, (rect.height - height) / 2, Math.max(1, step - .5), height) })
    const x = duration > 0 ? Math.min(rect.width, currentTime / duration * rect.width) : 0
    context.fillStyle = '#ef2b2d'; context.fillRect(x, 0, 1.5, rect.height)
  }, [samples, currentTime, duration])

  return <canvas ref={canvasRef} className="waveform" aria-label="Dạng sóng âm thanh"
    onPointerDown={event => { if (!duration) return; const rect=event.currentTarget.getBoundingClientRect()
      onSeek(Math.max(0, Math.min(duration, (event.clientX-rect.left)/rect.width*duration))) }}/>
}
