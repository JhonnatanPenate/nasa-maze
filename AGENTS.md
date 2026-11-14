# Planetary Explorer (nasa-maze)

NASA Space Apps Challenge 2026, reto **Interplanetary Survival Guide: Martian Map**
(https://www.spaceappschallenge.org/2026/challenges/interplanetary-survival-guide-martian-map/).
Un "Waze para Marte": el usuario elige origen y destino y recibe una ruta segura según
terreno (elevación, pendiente, cráteres) y riesgos ambientales, sobre un mapa interactivo
que funciona offline con los datos ya descargados. MVP: Marte, una sola región.

## Arquitectura

Monorepo de microservicios Python/FastAPI que hablan por REST, orquestados por un servicio
Core y levantados con Docker Compose: Location, Data Management, Raster, Terrain Analysis,
Risk Assessment, Routing Engine. Rasterio/GDAL para rásters, SQLite para el catálogo,
GeoTIFF/GeoPackage en almacenamiento local compartido (`data/`, nunca en git).
Cada integrante es dueño de un servicio.

## Reglas

- Antes de trabajar dentro de un servicio, lee su `AGENTS.md`. No cambies el contrato REST
  de otro servicio sin avisar a su dueño.
- Hackathon: la solución más simple que funcione (skill `ponytail`).
- Datos de Marte: skill `mars-geodata` (CRS, unidades y pendientes no son terrestres).
- Si existe `GLOSSARY.md`, usa sus términos en código y docs.
- Trabaja en rama y abre PR; nada directo a `main`.

## Más contexto (leer solo si hace falta)

- Skills del repo y por qué están: `docs/ai/README.md`
- Declaración de uso de IA: `docs/ai/USO-DE-IA.md` (registrar con `/registrar-uso-ia`)
