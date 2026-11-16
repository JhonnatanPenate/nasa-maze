import type { Feature, MultiLineString, Point } from 'geojson'
import type {
  BaseLayerFeature,
  BaseLayersResponse,
  Material,
  OrigenProperties,
  PuntoQuimicaProperties,
  TrazaMslProperties,
} from '../api/types'

export interface NamedPoint {
  nombre: string
  lon: number
  lat: number
}

export interface ChemSite extends NamedPoint {
  sol: number | null
  elevacion_m: number | null
  pct: Record<Material, number | null>
}

const MATERIAL_FIELDS: Record<Material, keyof PuntoQuimicaProperties> = {
  hematita: 'hematita_pct',
  esmectitas: 'esmectitas_pct',
  tridimita: 'tridimita_pct',
  sulfatos: 'sulfatos_pct',
}

function isChemSite(f: BaseLayerFeature): f is Feature<Point, PuntoQuimicaProperties> {
  return f.properties?.capa === 'puntos_quimica' && f.geometry?.type === 'Point'
}

function isTraverse(f: BaseLayerFeature): f is Feature<MultiLineString, TrazaMslProperties> {
  return f.properties?.capa === 'traza_msl' && f.geometry?.type === 'MultiLineString'
}

function isOrigen(f: BaseLayerFeature): f is Feature<Point, OrigenProperties> {
  return f.properties?.capa === 'origen' && f.geometry?.type === 'Point'
}

function toNumberOrNull(v: unknown): number | null {
  return typeof v === 'number' && Number.isFinite(v) ? v : null
}

export function chemSites(layers: BaseLayersResponse): ChemSite[] {
  return layers.features.filter(isChemSite).map((f) => {
    const p = f.properties
    const pct = {} as Record<Material, number | null>
    for (const material of Object.keys(MATERIAL_FIELDS) as Material[]) {
      pct[material] = toNumberOrNull(p[MATERIAL_FIELDS[material]])
    }
    return {
      nombre: p.nombre,
      lon: f.geometry.coordinates[0],
      lat: f.geometry.coordinates[1],
      sol: toNumberOrNull(p.sol),
      elevacion_m: toNumberOrNull(p.elevacion_m),
      pct,
    }
  })
}

export function candidateSites(sites: ChemSite[], material: Material): ChemSite[] {
  return sites.filter((s) => (s.pct[material] ?? 0) > 0)
}

export function bradburyOrigin(layers: BaseLayersResponse): NamedPoint | null {
  const f = layers.features.find(isOrigen)
  if (!f) return null
  return {
    nombre: f.properties.nombre,
    lon: f.geometry.coordinates[0],
    lat: f.geometry.coordinates[1],
  }
}

export function mslTraverse(layers: BaseLayersResponse): [number, number][][] {
  const f = layers.features.find(isTraverse)
  return f ? (f.geometry.coordinates as [number, number][][]) : []
}

export function originOptions(layers: BaseLayersResponse): NamedPoint[] {
  const options: NamedPoint[] = []
  const seen = new Set<string>()
  const push = (p: NamedPoint) => {
    const key = `${p.lon.toFixed(4)},${p.lat.toFixed(4)}`
    if (!seen.has(key)) {
      seen.add(key)
      options.push(p)
    }
  }
  const bradbury = bradburyOrigin(layers)
  if (bradbury) push(bradbury)
  for (const site of chemSites(layers)) {
    push({ nombre: site.nombre, lon: site.lon, lat: site.lat })
  }
  return options
}
