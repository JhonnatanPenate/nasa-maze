# Licencias de terceros

El código propio del proyecto está bajo Apache License 2.0 (`LICENSE`). Los datos tienen sus propios términos (`DATA_SOURCES.md`).

## Incluido en el repositorio

| Componente | Ubicación | Licencia | Autor |
|---|---|---|---|
| Skills de agentes (codebase-design, diagnosing-bugs, domain-modeling, grill-with-docs, grilling, handoff, tdd, writing-for-agents) | `.claude/skills/` | MIT (`.claude/skills/LICENSE-mattpocock-skills`) | Matt Pocock |
| Skill `ponytail` | `.claude/skills/ponytail/` | MIT (declarado en su `SKILL.md`) | Ver `SKILL.md` |

## Dependencias (se instalan, no se redistribuyen)

### Python
| Paquete | Licencia |
|---|---|
| fastapi | MIT |
| uvicorn | BSD-3-Clause |
| pydantic, pydantic-settings | MIT |
| numpy | BSD-3-Clause (y componentes 0BSD, MIT, Zlib, CC0-1.0) |
| pandas | BSD-3-Clause |
| scipy | BSD-3-Clause |
| rasterio (incluye GDAL en sus wheels) | BSD-3-Clause (GDAL: MIT) |
| openpyxl | MIT |
| matplotlib | Licencia de matplotlib (tipo PSF) |
| httpx | BSD-3-Clause |
| pytest | MIT |

### R (solo para `science/modelos_inclinacion_por_suelo.R`)
| Paquete | Licencia |
|---|---|
| dplyr, jsonlite, readxl | MIT |
| car, nlme | GPL (≥ 2) |
| lmtest, sandwich | GPL-2 \| GPL-3 |

Los paquetes R con GPL se cargan en tiempo de ejecución y no se incluyen en este repositorio.
