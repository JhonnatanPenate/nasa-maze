import type { Feature, LineString, MultiLineString, Point } from 'geojson'

export type ServiceStatus = 'ok' | 'down' | 'no_configurado'

export interface HealthResponse {
  status: 'ok' | 'degraded'
  servicios: {
    ms6: ServiceStatus
    ms5: ServiceStatus
    ms4: ServiceStatus
    ms1: ServiceStatus
  }
  fallback_precalculado: boolean
  aoi: [number, number, number, number]
  sols: number[]
  bounds_rejilla: [number, number, number, number] | null
}

export type Material = 'hematita' | 'esmectitas' | 'tridimita' | 'sulfatos'

export interface RouteRequest {
  lon: number
  lat: number
  material: Material
  sol: number
  hora: number
  vmax: number
}

export interface PuntoQuimicaProperties {
  capa: 'puntos_quimica'
  nombre: string
  sol?: number | null
  elevacion_m?: number | null
  hematita_pct?: number | null
  esmectitas_pct?: number | null
  tridimita_pct?: number | null
  sulfatos_pct?: number | null
  [key: string]: unknown
}

export interface TrazaMslProperties {
  capa: 'traza_msl'
  nombre?: string
}

export interface OrigenProperties {
  capa: 'origen'
  nombre: string
}

export type BaseLayerFeature =
  | Feature<Point, PuntoQuimicaProperties>
  | Feature<MultiLineString, TrazaMslProperties>
  | Feature<Point, OrigenProperties>

export interface BaseLayersResponse {
  type: 'FeatureCollection'
  crs?: { type: 'name'; properties: { name: string } }
  features: BaseLayerFeature[]
}

export interface RutaOptimaProperties {
  capa: 'ruta_optima'
  tipo_suelo: string
  modelo_usado: string
  inclinacion_grados: number
}

export interface ContrafactualProperties {
  capa: 'contrafactual'
  nombre: string
}

export interface ObjetivoProperties {
  capa: 'objetivo'
  nombre: string
  material: string
}

export type RouteFeature =
  | Feature<LineString, RutaOptimaProperties>
  | Feature<LineString, ContrafactualProperties>
  | Feature<Point, ObjetivoProperties>
  | Feature<Point, OrigenProperties>

export interface RouteGeoJson {
  type: 'FeatureCollection'
  crs?: { type: 'name'; properties: { name: string } }
  features: RouteFeature[]
}

export interface ComparativaBagnold {
  celdas_duna_ruta_optima: number
  celdas_duna_contrafactual: number
  horas_ahorradas_en_arena: number
  distancia_minima_a_duna_m: number
}

export interface Resumen {
  distancia_km: number
  hora_llegada: string
  dosis_rad_acum_uGy: number
  horas_espera_nocturna: number
  costo_objetivo: number
  nodos_expandidos: number
  objetivo: string
  material: Material | string
  comparativa_bagnold: ComparativaBagnold
}

export interface Tramo {
  tramo: number
  hora_lmst_inicio: string
  hora_lmst_fin: string
  tipo_suelo: string
  modelo_usado: string
  r2_ajustado: number | null
  distancia_m: number
  inclinacion_media_grados: number
  inclinacion_max_grados: number
  dosis_tramo_uGy: number
  dosis_acumulada_uGy: number
  temp_suelo_K: string
}

export interface ControlCalidad {
  celdas_totales: number
  celdas_validas: number
  pct_celdas_validas: number
  pct_validas?: number
  umbral_pct_celdas_validas?: number
  umbral_pct_validas?: number
  cobertura_ok: boolean
  margen_seguridad?: string
  celdas_bloqueadas_por_margen?: number
  conteo_tipos_suelo?: Record<string, number>
  suelos?: Record<string, number>
  [key: string]: unknown
}

export interface RiskFactorScore {
  score: number | null
  available: boolean
}

export interface RiskSegment {
  from: { lat: number; lon: number }
  to: { lat: number; lon: number }
  distance_m: number
  risk: number | null
  factor_scores: Record<string, RiskFactorScore>
  warnings: string[]
  local_time_hour?: number
}

export interface RiskRestriction {
  segment: number
  code: string
  blocking: boolean
  message: string
  factor: string
  value: number
  limit: number
}

export interface RiskHotspot {
  segment: number
  risk: number
  level: string
  distance_m: number
}

export interface Riesgo {
  overall_risk: number | null
  risk_level: string
  segments: RiskSegment[]
  warnings_summary: string[]
  dominant_factor?: string | null
  restrictions?: RiskRestriction[]
  hotspots?: RiskHotspot[]
  blocking_segments?: number[]
  confidence?: string
  [key: string]: unknown
}

export type RouteSource = 'ms6' | 'precalculada'

export interface RouteResponse {
  geojson: RouteGeoJson
  resumen: Resumen
  tramos: Tramo[]
  control_calidad: ControlCalidad | null
  fuente: RouteSource
  riesgo: Riesgo | null
}

export type RasterBand =
  | 'pendiente_grados'
  | 'rugosidad_m'
  | 'fraccion_oscura'
  | 'inercia_termica_tiu'
  | 'albedo'
  | 'distancia_duna_m'

export type RasterCmap = 'viridis' | 'gray'

export interface RasterBandResult {
  url: string
  bounds: [number, number, number, number]
}

export interface CoordinateSystem {
  body: 'mars'
  crs: 'IAU_2015:49900'
  lat_type: 'planetocentric'
  lon_convention: 'east_positive_0_360'
  radius_m: 3396190
}

export interface Place {
  id: string
  name: string
  body?: string
  kind?: 'feature' | 'poi' | 'landing_site' | string
  feature_type?: string
  source?: string
  center: { lat: number; lon: number }
  bbox?: { west: number; south: number; east: number; north: number } | null
  diameter_km?: number | null
  elevation_m?: number | null
  approval_status?: string | null
  aliases?: string[]
  tags?: string[]
  properties?: Record<string, unknown>
  in_regions?: string[]
}

export interface PlaceSearchResult {
  score: number
  match_type: 'exact_name' | 'exact_alias' | 'prefix' | 'tokens' | 'fuzzy' | string
  place: Place
}

export interface PlaceSearchResponse {
  query: string
  normalized_query: string
  total: number
  results: PlaceSearchResult[]
  catalog_version: string
  coordinate_system: CoordinateSystem
}
