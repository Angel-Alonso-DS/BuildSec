# BuildSys · Kit operativo para 2 equipos con Codex

**Objetivo**: Generar APIs REST pequeñas desde requisitos, probarlas, detectar/corregir fallos, conservar evidencia, y reutilizar lecciones verificadas (Golden Routes). La seguridad se guía por controles seleccionados de ISO/IEC 27001:2022. **No se afirma cumplimiento ni certificación ISO**.

## Arquitectura y gobernanza
- **Monolith-first**: priorizar un backend modular y una sola unidad desplegable; separar procesos solo si hay necesidad demostrada.
- Esta versión incorpora la skill original aportada por el equipo con `development` adaptado a `dev`.
- `main` es intocable para Codex por la propia skill; el release humano `dev → main` se gestiona externamente mediante PR/revisión humana.
- Para crear el repositorio fallback, inicializarlo manualmente con `main` y `dev`, sin delegar operaciones sobre `main` al agente.

## Requisitos
- Git, Python 3.11+, Codex CLI autenticado. `codex exec --help` debe funcionar.
- Docker disponible para ejecutar código generado o tests no confiables. NO ejecutar código generado por IA directamente sobre el host de trabajo.
- GitHub CLI (`gh`) opcional para PR. El repositorio ya tiene `main` y `dev`.

## Comienzo (no sobrescribir archivos existentes)
1. Revisar `AGENTS.md`, `TASKS.md`, `CONTRACTS.md` y los prompts.
2. Copiar el kit al repositorio conservando los archivos ya existentes. En colisiones, revisar diferencias y fusionar manualmente. No copiar carpetas ocultas a ciegas.
3. Crear PR de configuración: `feature/bootstrap-codex-kit` -> `dev`. No añadir el kit directamente a `main`.
4. Ambas personas sincronizan `dev` y crean su propia rama desde `origin/dev`:
   - A: `feature/core-orchestrator`
   - B: `feature/security-evidence`
5. A implementa contratos estables y mocks primero. B trabaja contra esos contratos. Cada PR modifica solamente su zona de propiedad.
6. Integración: A PR -> `dev`; B hace `git fetch origin && git merge origin/dev` (si su rama no está compartida), ejecuta pruebas y PR -> `dev`.
7. `dev` -> `main` solo mediante release PR ejecutado por humano, fuera de las autorizaciones de la skill para agentes.

## Ejecutar Codex
```bash
# Desde la raíz del repositorio; sesión interactiva, un equipo por rama
codex "Lee AGENTS.md y prompts/TEAM_A.md. Implementa la primera tarea pendiente del equipo A, prueba y resume. Respeta git-governance: push y PR permitidos, merge solo con aprobación humana."

# O ejecutar un intento no interactivo, en rama del equipo, con sandbox workspace-write:
python scripts/goal_loop.py --prompt prompts/TEAM_A.md --iterations 2 --run-codex --no-validate

# Cuando ya existan comandos de test del proyecto, configurar config/checks.json y ejecutar:
python scripts/goal_loop.py --prompt prompts/TEAM_A.md --iterations 2 --run-codex
```
**Importante**: `--no-validate` solo sirve para bootstrap; nunca se debe usar como evidencia de aceptación. El loop por defecto no ejecuta Codex sin `--run-codex`, y nunca hace commit, push ni merge.

## Documentos
- `AGENTS.md`: instrucciones globales para Codex.
- `TASKS.md`: reparto y dependencias.
- `CONTRACTS.md`: acuerdos de API y estados.
- `prompts/`: prompts de planificación, desarrollo, seguridad, integración y demo.
- `.agents/skills/git-governance/SKILL.md`: skill local de colaboración Git/GitHub.
- `scripts/goal_loop.py`: runner acotado Codex -> tests -> evidencia.
- `config/checks.json`: comandos de validación, a configurar tras detectar el stack.
- `.github/workflows/ci.yml`: CI base Python; adaptar a proyecto real.

**Alcance**: esto es un kit de coordinación y scaffold ejecutable, no el proyecto BuildSys implementado. Se necesita la URL/estado del repo para adaptar integraciones exactas.

## Seguridad del runner
`config/checks.json` es para verificar el kit y **código confiable**; si los checks importan o ejecutan código generado, reemplaza los comandos por comandos ejecutados dentro de Docker. Hay una plantilla `config/checks.sandbox.example.json` que debe adaptarse a tu ruta absoluta, imagen fijada por digest y dependencias. Usa límites de CPU/memoria/procesos; no garantizan aislamiento absoluto frente a ataques al kernel. Nunca introduzcas secretos en el runner. Los resultados de escáneres no prueban certificación ISO.
