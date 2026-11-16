import { mineralLabel, riskLevelColor, riskLevelLabel, sourceLabel } from '../../domain/labels'
import type { RouteView } from '../../domain/routeView'

export interface RouteSummaryProps {
  view: RouteView
  onNewRoute: () => void
  showAlternative?: boolean
  onToggleAlternative?: (selected: boolean) => void
}

function Kpi({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded bg-slate-800 p-2">
      <div className="text-[10px] text-slate-400 uppercase">{label}</div>
      <div className="text-sm font-semibold">{value}</div>
    </div>
  )
}

export function RouteSummary({ view, onNewRoute, showAlternative = false, onToggleAlternative }: RouteSummaryProps) {
  const { kpis } = view
  const cmp = kpis.comparativa
  return (
    <div
      aria-label="Route summary"
      data-testid="route-summary"
      className="w-full max-w-sm rounded-xl border border-slate-800 bg-slate-900/95 p-4 text-slate-100 shadow-xl backdrop-blur-md sm:w-90"
    >
      <div className="mb-3 flex items-center justify-between gap-2 border-b border-slate-800 pb-2">
        <h2 className="text-sm font-semibold text-slate-200">
          {kpis.objetivo} · {mineralLabel(kpis.material)}
        </h2>
        <div className="flex gap-1 text-[10px] font-semibold">
          <span className="rounded bg-slate-700 px-2 py-0.5">{sourceLabel(kpis.fuente)}</span>
          {view.riskLevel && (
            <span className="rounded px-2 py-0.5 text-slate-900" style={{ background: riskLevelColor(view.riskLevel) }}>
              Risk: {riskLevelLabel(view.riskLevel)}
            </span>
          )}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-2">
        <Kpi label="Distance" value={`${kpis.distanciaKm} km`} />
        <Kpi label="Arrival" value={kpis.horaLlegada} />
        <Kpi label="Radiation dose" value={`${kpis.dosisRadAcumUgy} µGy`} />
        <Kpi label="Night wait" value={`${kpis.horasEsperaNocturna} h`} />
      </div>

      {cmp && (
        <div className="mt-3 rounded bg-slate-800 p-2 text-xs text-slate-300">
          <div className="font-semibold text-slate-200">Bagnold dune comparison</div>
          <div>Dune cells: {cmp.celdas_duna_ruta_optima} vs {cmp.celdas_duna_contrafactual} (alternative)</div>
          <div>Hours saved on sand: {cmp.horas_ahorradas_en_arena}</div>
          <div>Closest dune: {cmp.distancia_minima_a_duna_m} m</div>
        </div>
      )}

      {view.warnings.length > 0 && (
        <ul className="mt-3 list-disc pl-4 text-xs text-amber-300">
          {view.warnings.map((w, i) => (
            <li key={`${i}-${w}`}>{w}</li>
          ))}
        </ul>
      )}

      <div className="mt-3 flex gap-2">
        {view.alternative && onToggleAlternative && (
          <button
            type="button"
            onClick={() => onToggleAlternative(!showAlternative)}
            className="flex-1 rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-xs font-medium hover:bg-slate-700"
          >
            {showAlternative ? 'Show optimal route' : 'Compare alternative'}
          </button>
        )}
        <button
          type="button"
          onClick={onNewRoute}
          className="flex-1 rounded-lg bg-cyan-600 px-3 py-2 text-xs font-semibold text-white hover:bg-cyan-500"
        >
          New route
        </button>
      </div>
    </div>
  )
}

export default RouteSummary
