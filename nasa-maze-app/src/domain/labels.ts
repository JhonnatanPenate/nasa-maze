const NEUTRAL_COLOR = '#9ca3af'

const MINERAL_LABELS: Record<string, string> = {
  hematita: 'Hematite',
  esmectitas: 'Smectites',
  tridimita: 'Tridymite',
  sulfatos: 'Sulfates',
}

const SOIL_LABELS: Record<string, string> = {
  arena_dunas: 'Dune sand',
  lecho_rocoso_firme: 'Firm bedrock',
  regolito_compacto: 'Compact regolith',
  rocoso_fracturado: 'Fractured rock',
}

const SOIL_COLORS: Record<string, string> = {
  arena_dunas: '#fbbf24',
  lecho_rocoso_firme: '#38bdf8',
  regolito_compacto: '#4ade80',
  rocoso_fracturado: '#f472b6',
}

const BAND_LABELS: Record<string, string> = {
  pendiente_grados: 'Slope (°)',
  rugosidad_m: 'Roughness (m)',
  fraccion_oscura: 'Dark fraction',
  inercia_termica_tiu: 'Thermal inertia (TIU)',
  albedo: 'Albedo',
  distancia_duna_m: 'Distance to dunes (m)',
}

const RISK_LEVEL_LABELS: Record<string, string> = {
  low: 'Low',
  medium: 'Medium',
  high: 'High',
  unknown: 'Unknown',
}

const RISK_LEVEL_COLORS: Record<string, string> = {
  low: '#22c55e',
  medium: '#eab308',
  high: '#ef4444',
  unknown: NEUTRAL_COLOR,
}

const SOURCE_LABELS: Record<string, string> = {
  ms6: 'Live',
  precalculada: 'Precalculated',
}

function humanize(key: string): string {
  const words = key.replace(/_/g, ' ').trim()
  return words.length === 0 ? key : words[0].toUpperCase() + words.slice(1)
}

function lookup(table: Record<string, string>, key: string): string {
  return table[key] ?? humanize(key)
}

export function mineralLabel(material: string): string {
  return lookup(MINERAL_LABELS, material)
}

export function soilLabel(tipoSuelo: string): string {
  return lookup(SOIL_LABELS, tipoSuelo)
}

export function soilColor(tipoSuelo: string): string {
  return SOIL_COLORS[tipoSuelo] ?? NEUTRAL_COLOR
}

export function bandLabel(banda: string): string {
  return lookup(BAND_LABELS, banda)
}

export function riskLevelLabel(level: string): string {
  return lookup(RISK_LEVEL_LABELS, level)
}

export function riskLevelColor(level: string): string {
  return RISK_LEVEL_COLORS[level] ?? NEUTRAL_COLOR
}

export function sourceLabel(fuente: string): string {
  return lookup(SOURCE_LABELS, fuente)
}
