import type { RoutingMode } from '../../domain/capabilities'

export interface StatusBadgeProps {
  routingMode: RoutingMode
  basemapOnline: boolean
  className?: string
}

export function StatusBadge({ routingMode, basemapOnline, className = '' }: StatusBadgeProps) {
  const routingConfig = {
    live: { label: 'Routing: Live', dot: 'bg-emerald-400', badge: 'border-emerald-500/40 text-emerald-200' },
    fallback: { label: 'Routing: Fallback', dot: 'bg-amber-400', badge: 'border-amber-500/40 text-amber-200' },
    none: { label: 'Routing: Unavailable', dot: 'bg-rose-400', badge: 'border-rose-500/40 text-rose-200' },
  }[routingMode]

  const basemapConfig = basemapOnline
    ? { label: 'Basemap: Online', dot: 'bg-emerald-400', badge: 'border-emerald-500/40 text-emerald-200' }
    : { label: 'Basemap: Offline', dot: 'bg-amber-400', badge: 'border-amber-500/40 text-amber-200' }

  return (
    <div
      aria-label="System status"
      data-testid="status-badges"
      className={`flex items-center gap-2 ${className}`}
    >
      <div
        className={`flex items-center gap-1.5 rounded-full border bg-slate-900/90 px-2.5 py-1 text-xs shadow ${routingConfig.badge}`}
      >
        <span className={`inline-block h-2 w-2 rounded-full ${routingConfig.dot}`} />
        <span>{routingConfig.label}</span>
      </div>

      <div
        className={`flex items-center gap-1.5 rounded-full border bg-slate-900/90 px-2.5 py-1 text-xs shadow ${basemapConfig.badge}`}
      >
        <span className={`inline-block h-2 w-2 rounded-full ${basemapConfig.dot}`} />
        <span>{basemapConfig.label}</span>
      </div>
    </div>
  )
}

export default StatusBadge
