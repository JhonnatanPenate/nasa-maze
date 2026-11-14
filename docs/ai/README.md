# IA en este repo

Configuración para Claude Code y Devin, pensada para gastar el mínimo de contexto.

## Cómo está armado

- `AGENTS.md` (raíz): contexto global corto. Lo leen Devin, Codex, Cursor, etc.
- `CLAUDE.md` (raíz): solo `@AGENTS.md`, para que Claude Code lea lo mismo sin duplicar.
- `<servicio>/AGENTS.md` + `<servicio>/CLAUDE.md` (`@AGENTS.md`): contexto de cada servicio.
  Claude Code lo carga solo cuando trabaja en esa carpeta. Plantilla: [plantilla-AGENTS-servicio.md](plantilla-AGENTS-servicio.md).
- `.claude/skills/`: skills. Claude Code las lee de ahí y Devin también escanea esa ruta, así
  que no hay copias en `.agents/` ni `.devin/`.

Una skill **model-invoked** deja su nombre y descripción en el contexto de cada sesión y el
agente la abre cuando aplica. Una **user-invoked** (`disable-model-invocation: true`, y
`triggers: ["user"]` para Devin) no cuesta nada hasta que alguien la llama con `/nombre`
(Claude Code) o `@skills:nombre` (Devin).

## Skills incluidas

| Skill | Tipo | Origen | Por qué |
|---|---|---|---|
| `ponytail` | model | skill de Alex (MIT) | Hackathon de 48 h: YAGNI, stdlib primero, diff más corto. |
| `mars-geodata` | model | propia | CRS IAU de Marte, metros por grado, pendientes, nodata, COG. Es donde más se equivoca un agente. |
| `codebase-design` | model | Matt Pocock | Vocabulario de módulos profundos y seams: clave para los contratos entre 6 servicios. |
| `tdd` | model | Matt Pocock | Test primero para la lógica que importa (costos de ruta, pendientes, riesgo). |
| `diagnosing-bugs` | model | Matt Pocock | Loop disciplinado de debug (reproducir, minimizar, hipótesis). |
| `grilling` | model | Matt Pocock | Entrevista para alinear un plan antes de codear. |
| `domain-modeling` | model | Matt Pocock | Mantiene `GLOSSARY.md` y ADRs: un vocabulario común para el equipo. |
| `grill-with-docs` | user | Matt Pocock | `/grill-with-docs`: grilling + glosario/ADRs en una sola llamada. |
| `handoff` | user | Matt Pocock | `/handoff`: pasar una sesión de Claude a Devin (o viceversa) sin perder el hilo. |
| `writing-for-agents` | user | Matt Pocock | `/writing-for-agents`: al escribir AGENTS.md o skills. Pasada a user-invoked para no gastar contexto. |
| `registrar-uso-ia` | user | propia | `/registrar-uso-ia`: agrega una fila a la declaración de uso de IA. |

Matt Pocock: https://github.com/mattpocock/skills (MIT), commit `5863806`. Copiadas sin cambios
salvo: se quitaron las carpetas `agents/` (metadatos de Codex) y se agregó `triggers`/`disable-model-invocation`
donde dice arriba. Para actualizar, vuelve a copiar la carpeta desde ese repo.

## Descartadas

- `to-spec`, `to-tickets`, `triage`, `wayfinder`, `implement`, `implement-spec`: necesitan `setup-matt-pocock-skills` y un flujo de issues; demasiado proceso para un fin de semana. Si el equipo empieza a usar GitHub Issues en serio, agregar `to-tickets` primero.
- `code-review`: Claude Code ya trae `/code-review` y chocaría el nombre.
- `improve-codebase-architecture`, `retro`, `prototype`, `research`, `wizard`, `pr`: útiles en proyectos largos, no en 48 h.
- `grill-me`, `teach`, `wait-what`, `to-questionnaire`, `ask-matt`: redundantes con las de arriba o fuera del alcance.
- Skills genéricas de FastAPI/Docker: los modelos ya lo hacen bien; solo sumarían descripciones al contexto.
- Plugin completo de Matt (`claude plugin install`): mete ~20 skills; preferimos elegir.

## Agregar una skill

Solo si resuelve un error que ya pasó dos veces. Descripción en una línea que diga **cuándo**
usarla. Si solo se usa a pedido, márcala user-invoked.
