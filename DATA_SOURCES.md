# Fuentes de datos (DATA_SOURCES)

Datos usados en `data/gale/` y por los scripts de `science/`. Paquete preparado por Javier Galdámez (ciencia/datos).
Los **términos de uso de los datos son independientes de la licencia del código**.

> Estado: borrador. Las filas marcadas **⚠ confirmar** necesitan que Javi indique el producto/ID exacto (PDS DATA_SET_ID o DOI) antes de la entrega.

## Fuentes externas

| # | Recurso | Procedencia | Uso en el proyecto | Términos / atribución | Estado |
|---|---|---|---|---|---|
| 1 | DEM HiRISE (Gale), vía Mars Trek | NASA/JPL-Caltech/University of Arizona | Pendiente y rugosidad de `rejilla_ruta_90m.tif` | Datos PDS de dominio público; citar producto. Crédito: NASA/JPL-Caltech/UArizona | ⚠ confirmar producto |
| 2 | DTM HRSC 30 m (respaldo si HiRISE no cubre) | ESA/DLR/FU Berlin (Mars Express) | Respaldo de pendiente | Imágenes HRSC: CC BY-SA 3.0 IGO, crédito "ESA/DLR/FU Berlin". Si se usó, la capa derivada hereda *share-alike* | ⚠ confirmar si se usó |
| 3 | DEM MOLA/HRSC 200 m (respaldo) | NASA/ESA (vía USGS Astrogeology) | Respaldo de pendiente | Citar producto USGS | ⚠ confirmar si se usó |
| 4 | Inercia térmica y albedo TES | NASA PDS, `mgs-m-tes` (Mars Global Surveyor) | Bandas `inercia_termica_tiu` y `albedo` | PDS dominio público; citar data set | ⚠ confirmar ID |
| 5 | MSL RAD RDR (sols 1360/2140/3290/4710) | NASA PDS (Curiosity, RAD) | `raw/ambiental/rad_dosis_observaciones.xlsx` | PDS dominio público; citar data set | ⚠ confirmar ID |
| 6 | MSL REMS MODRDR | NASA PDS (instrumento REMS, Centro de Astrobiología, España) | `raw/ambiental/rems_resumen_horario.xlsx` | PDS; citar data set y equipo REMS | ⚠ confirmar ID |
| 7 | CheMin RDR (minerales) | NASA PDS (Curiosity, CheMin) | `processed/gale_puntos_quimica.xlsx` | PDS dominio público; citar data set | ⚠ confirmar ID |
| 8 | APXS / ChemCam (óxidos) | NASA PDS (APXS: CSA; ChemCam: LANL/CNES) | Calibración (`gale_matriz_calibracion.xlsx`) si se incluyeron | PDS; citar data sets | ⚠ confirmar si se usó |
| 9 | Traza y waypoints de Curiosity | NASA/JPL (MSL) | `raw/pe_msl_vectores.json` | Citar fuente exacta (PDS Geosciences / MMGIS) | ⚠ confirmar origen |
| 10 | Incidentes de movilidad de Curiosity | Publicaciones NASA/JPL | Etiquetas de riesgo en calibración | Citar notas/artículos usados | ⚠ confirmar referencias |
| 11 | Gazetteer de nomenclatura de Marte (`data/gale/raw/gazzeter/MARS_nomenclature_center_pts.shp`) | International Astronomical Union (IAU) y U.S. Geological Survey (USGS) | Nombres y ubicaciones de accidentes geográficos marcianos | Dominio público. Atribución: IAU/USGS. Fuente: [USGS Gazetteer of Planetary Nomenclature](https://planetarynames.wr.usgs.gov/Page/MARS/target); metadatos del archivo indican publicación 2012-10-02 | — |

## Datos derivados por el equipo

`rejilla_ruta_90m.tif`, `gale_matriz_calibracion.xlsx`, `modelos_por_suelo.json`, `ruta_*` (geojson/xlsx/json),
`Bitacora_Calidad_Marte.xlsx`, `mapa_rutas_gale.png`: generados por los scripts de `science/` a partir de las fuentes de arriba.
Se publican con la licencia de datos que apruebe el equipo, respetando la atribución (y *share-alike* si aplica la fila 2).

## Notas

- Los datos del PDS están clasificados como TSPA (publicamente disponibles) y pueden exportarse como literatura abierta: https://pds-geosciences.wustl.edu/faq.html
- Cómo citar datos PDS: https://pds.nasa.gov/datastandards/citing/
- Licencia HRSC: https://www.dlr.de/en/blog/archive/2014/simpler-usage-rights-as-of-today-mars-express-hrsc-images-licensed-under-creative-commons-licence
- Términos NASA Space Apps 2026 (citar toda fuente; licencias de materiales no-NASA en la documentación): https://www.spaceappschallenge.org/legal/
