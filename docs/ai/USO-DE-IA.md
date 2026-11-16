# Declaración de uso de IA

Las reglas de NASA Space Apps piden declarar el uso de herramientas de IA en el proyecto.
Este archivo es el registro del equipo. Para agregar una entrada desde Claude Code o Devin:
`/registrar-uso-ia` (o `@skills:registrar-uso-ia`).

## Herramientas usadas

- Claude Code (Anthropic): asistente de código y documentación.
- Devin (Cognition): agente de código.
- Haiku: consultas a papers y datos de NASA con fuentes citadas.
- Bobby (agente propio de Alex, basado en Hermes): recibe pedidos por WhatsApp y los pasa como issues.

## Configuración de los agentes

Ver [README.md](README.md): qué skills se instalaron y por qué.

## Registro

| Fecha | Integrante | Herramienta | Área / servicio | Qué hizo la IA | Revisión humana |
|---|---|---|---|---|---|
| 2026-11-14 | Alex | Claude Code | Repo / docs | Configuró AGENTS.md, CLAUDE.md, skills en `.claude/skills` y estos docs | Pendiente (PR) |
| 2026-11-14 | Alex | Claude Code | Repo / docs | Definió el buzón de issues `bobby`, `docs/ai/agentes.md` y la plantilla de issue | Pendiente (PR) |
| 2026-11-15 | Jhonnatan | Claude Code | MS6 routing-engine | Extrajo POST /api/ruta del backend de Javier a `routing-engine/` (FastAPI, /health y /route), con validación de sol/AOI, lock global, tests, Dockerfile y AGENTS.md | Pendiente (PR) |
| 2026-11-15 | Jhonnatan | Devin | CI / MS6 routing-engine | Job `docker` en el CI (build + smoke de las 4 imágenes) y MS6 listo para la demo: datos dentro de la imagen, caché y precalentamiento de rutas, README y mensajes en inglés | Pendiente (PR) |
| 2026-11-16 | (frontend) | Devin | Frontend `nasa-maze-app/` | Implementó WP6-WP8: render de rutas (RouteLayer/RouteSummary), Dockerfile + nginx + servicio `app` en compose, smoke Playwright y docs | Pendiente (PR) |
