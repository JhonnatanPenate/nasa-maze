import { describe, expect, it } from 'vitest'
import {
  bandLabel,
  mineralLabel,
  riskLevelColor,
  riskLevelLabel,
  soilColor,
  soilLabel,
  sourceLabel,
} from './labels'

describe('mineralLabel', () => {
  it('maps every contract mineral to an English label', () => {
    expect(mineralLabel('hematita')).toBe('Hematite')
    expect(mineralLabel('esmectitas')).toBe('Smectites')
    expect(mineralLabel('tridimita')).toBe('Tridymite')
    expect(mineralLabel('sulfatos')).toBe('Sulfates')
  })

  it('humanizes unknown mineral keys instead of crashing', () => {
    expect(mineralLabel('olivina_rara')).toBe('Olivina rara')
  })
})

describe('soilLabel / soilColor', () => {
  it('maps known soils to English labels', () => {
    expect(soilLabel('arena_dunas')).toBe('Dune sand')
    expect(soilLabel('lecho_rocoso_firme')).toBe('Firm bedrock')
    expect(soilLabel('regolito_compacto')).toBe('Compact regolith')
    expect(soilLabel('rocoso_fracturado')).toBe('Fractured rock')
  })

  it('returns a stable color for each known soil', () => {
    expect(soilColor('arena_dunas')).toMatch(/^#[0-9a-f]{6}$/i)
    expect(soilColor('lecho_rocoso_firme')).not.toBe(soilColor('arena_dunas'))
  })

  it('falls back to a neutral color and humanized label for unknown soils', () => {
    expect(soilColor('suelo_desconocido')).toBe(soilColor('otro_suelo'))
    expect(soilLabel('polvo_fino')).toBe('Polvo fino')
  })
})

describe('bandLabel', () => {
  it('maps raster band keys to English labels', () => {
    expect(bandLabel('pendiente_grados')).toBe('Slope (°)')
    expect(bandLabel('distancia_duna_m')).toBe('Distance to dunes (m)')
  })

  it('humanizes unknown band keys', () => {
    expect(bandLabel('banda_nueva')).toBe('Banda nueva')
  })
})

describe('riskLevelLabel / riskLevelColor', () => {
  it('maps known risk levels', () => {
    expect(riskLevelLabel('low')).toBe('Low')
    expect(riskLevelLabel('medium')).toBe('Medium')
    expect(riskLevelLabel('high')).toBe('High')
    expect(riskLevelLabel('unknown')).toBe('Unknown')
  })

  it('returns neutral color for unknown levels', () => {
    expect(riskLevelColor('nivel_raro')).toBe(riskLevelColor('unknown'))
  })
})

describe('sourceLabel', () => {
  it('maps route sources to badge text', () => {
    expect(sourceLabel('ms6')).toBe('Live')
    expect(sourceLabel('precalculada')).toBe('Precalculated')
  })

  it('humanizes unknown sources', () => {
    expect(sourceLabel('otra_fuente')).toBe('Otra fuente')
  })
})
