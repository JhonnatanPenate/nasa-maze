import { useEffect, useRef, useState } from 'react'
import { TileLayer } from 'react-leaflet'

export type BasemapMode = 'online' | 'offline'

export interface BasemapProps {
  tileUrl?: string
  mode?: BasemapMode
  probeTimeoutMs?: number
  onModeChange?: (mode: BasemapMode) => void
}

export const DEFAULT_MARS_TILE_URL =
  'https://cartocdn-gusc.global.ssl.fastly.net/opmbuilder/api/v1/map/named/opm-mars-basemap-v0-2/all/{z}/{x}/{y}.png'

function probeTile(url: string, timeoutMs: number): Promise<boolean> {
  return new Promise((resolve) => {
    const sample = url.replace('{z}', '0').replace('{x}', '0').replace('{y}', '0')
    const img = new Image()
    let settled = false
    const finish = (ok: boolean) => {
      if (settled) return
      settled = true
      resolve(ok)
    }
    const timer = setTimeout(() => finish(false), timeoutMs)
    img.onload = () => {
      clearTimeout(timer)
      finish(true)
    }
    img.onerror = () => {
      clearTimeout(timer)
      finish(false)
    }
    img.src = sample
  })
}

export function Basemap({
  tileUrl = import.meta.env.VITE_MARS_TILE_URL ?? DEFAULT_MARS_TILE_URL,
  mode,
  probeTimeoutMs = 4000,
  onModeChange,
}: BasemapProps) {
  const onModeChangeRef = useRef(onModeChange)
  useEffect(() => {
    onModeChangeRef.current = onModeChange
  })

  const [probedMode, setProbedMode] = useState<BasemapMode | null>(null)

  useEffect(() => {
    if (!tileUrl) {
      onModeChangeRef.current?.('offline')
      return
    }
    if (mode) {
      onModeChangeRef.current?.(mode)
      return
    }
    let cancelled = false
    probeTile(tileUrl, probeTimeoutMs).then((ok) => {
      if (cancelled) return
      const next: BasemapMode = ok ? 'online' : 'offline'
      setProbedMode(next)
      onModeChangeRef.current?.(next)
    })
    return () => {
      cancelled = true
    }
  }, [tileUrl, mode, probeTimeoutMs])

  const resolvedMode: BasemapMode = !tileUrl
    ? 'offline'
    : mode ?? probedMode ?? 'offline'

  if (resolvedMode === 'offline' || !tileUrl) {
    return (
      <div
        className="pointer-events-none absolute inset-0 z-0 bg-slate-950"
        data-testid="offline-basemap"
      />
    )
  }

  return <TileLayer url={tileUrl} attribution="OpenPlanetaryMap" />
}

export default Basemap
