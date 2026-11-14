---
name: registrar-uso-ia
description: Registra en docs/ai/USO-DE-IA.md cómo se usó IA en el trabajo de esta sesión, para la declaración de uso de IA del hackathon.
disable-model-invocation: true
triggers: ["user"]
argument-hint: "[nota opcional]"
---

1. Resume lo que se hizo en esta sesión con ayuda de IA: herramienta (Claude Code, Devin, etc.), qué generó o modificó, y qué revisó o decidió una persona.
2. Agrega **una fila** a la tabla de `docs/ai/USO-DE-IA.md` con: fecha (AAAA-MM-DD), integrante, herramienta, área/servicio, qué hizo la IA, revisión humana. Usa el nombre del integrante que te diga el usuario; si no lo sabes, pregúntalo.
3. No inventes revisión humana: si nadie revisó aún, escribe "pendiente".
4. No pegues prompts completos, secretos ni datos personales. Una línea por columna.
5. Si el usuario pasó una nota, inclúyela en la columna "qué hizo la IA".
