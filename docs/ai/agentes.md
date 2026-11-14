# Agentes y cómo se hablan

Un rol = una fila. Cambiar de proveedor es editar la fila, no el resto del sistema.

| Rol | Hoy lo hace | Cómo se invoca |
|---|---|---|
| Ventanilla (WhatsApp ↔ repo) | Bobby (basado en Hermes, homelab de Alex) | Abre issues `bobby`, lee sus comentarios |
| Orquestación y docs | Claude (proyecto en claude.ai) | Tarea programada que revisa issues `bobby` |
| Código | Devin | API, ver abajo; responde con un PR |
| Ciencia con fuentes (papers/datos NASA) | Haiku | MCP, ver abajo |

## El contrato (el único "adapter")

1. **Entrada:** issue con etiqueta `bobby` (plantilla `.github/ISSUE_TEMPLATE/bobby.md`).
2. **Salida:** comentarios en el issue que empiezan con una etiqueta. Bobby solo reenvía a WhatsApp estos:
   - `[necesito-info]` pregunta concreta; la respuesta del chat vuelve como comentario.
   - `[PR-listo]` link al PR para revisar.
   - `[bloqueado]` qué falta y quién lo destraba.
   - `[listo]` resumen de 1-3 líneas; se cierra el issue.
   Cualquier otro comentario es bitácora y no se reenvía.
3. Merge a `main` siempre lo hace un humano.

Cualquier agente que lea y escriba issues de GitHub se puede enchufar en cualquier lado.

## Invocar delegados

Secretos solo en variables de entorno, nunca en el repo.

```bash
# Devin: crea una sesión; pon el link del issue en el prompt y pide que abra PR
curl -s https://api.devin.ai/v1/sessions -H "Authorization: Bearer $DEVIN_API_KEY" \
  -H 'Content-Type: application/json' -d '{"prompt":"Resuelve <issue URL>. Abre PR a main y menciona el issue."}'

# Haiku: servidor MCP por HTTP (URL y token de Haiku > Opciones > Conexiones)
curl -s "$HAIKU_MCP_URL" -H "Authorization: Bearer $HAIKU_TOKEN" \
  -H 'Content-Type: application/json' -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
```

Cada encargo terminado agrega una línea en `USO-DE-IA.md` (`/registrar-uso-ia`).
