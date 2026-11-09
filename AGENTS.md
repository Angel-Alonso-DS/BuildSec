# Instrucciones para agentes Codex — BuildSys

## Misión
Construir un MVP que genere APIs REST pequeñas desde requisitos, las valide mediante tests, repare fallos de forma acotada, registre evidencia y reutilice Golden Routes verificadas. ISO/IEC 27001:2022 es un marco de referencia de prácticas seguras, NO una certificación.

## Prioridad
1. No romper código existente. Inspecciona stack y pruebas antes de crear archivos.
2. Seguir `TASKS.md` y `CONTRACTS.md`. Nunca cambiar contratos sin PR acordado por ambos equipos.
3. No afirmar tests aprobados si no se ejecutaron. Distingue `passed`, `failed`, `skipped`, `error`.
4. Crear tests junto con el código. Entregar cada tarea pequeña con criterios verificables.
5. No leer, imprimir ni commitear tokens, `.env`, secretos o datos sensibles.
6. Código generado se ejecuta solo dentro de sandbox aislado, con límites de recursos y, por defecto, sin red. No montar socket Docker ni credenciales del host.
7. Nunca hacer `git push --force` a ramas compartidas; nunca commits directos a `dev`/`main`.
8. No usar `--dangerously-bypass-approvals-and-sandbox` ni `--yolo`.
9. No introducir frameworks o dependencias nuevas si las existentes cumplen el objetivo.
10. Trabajar exclusivamente en los paths propios; pedir acuerdo vía PR/issue para cambios cruzados.

## Flujo de cada tarea
Inspeccionar -> plan mínimo -> cambios -> tests -> revisar diff -> resumen (archivos, tests, riesgos y siguiente paso). Si hay bloqueo, emitir una descripción concreta.

## Cierre
Sin merge automático. Reportar comando exacto, exit code, paths de evidencia y riesgos residuales. No inferir certificación ISO.

## Arquitectura y skill obligatoria
- Monolith-first: una sola aplicación modular salvo justificación técnica documentada. Los agentes son módulos, no microservicios por defecto.
- Antes de cualquier operación Git leer `.agents/skills/git-governance/SKILL.md`. Esa skill prevalece sobre ejemplos antiguos del kit.
- `main` y `dev` están protegidas; todas las tareas nacen de `dev` con `feature/*` o `bugfix/*`.
- No realizar operaciones sobre `main` con agentes. El humano coordina releases fuera del protocolo del agente.
- `git push` normal y creación de PR pueden hacerse sin aprobación, conforme a la matriz de la skill. `Squash and merge` a `dev` requiere autorización humana explícita por PR.
- No ejecutar un loop automático que realice cambios Git sin respetar la skill. El runner incluido NO hace commits, pushes ni merges.
