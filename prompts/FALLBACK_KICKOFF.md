# Prompt inicial: BuildSys fallback, dos equipos Codex

Eres un agente de implementación del proyecto BuildSys en el repositorio fallback. Lee `AGENTS.md`, `CONTRACTS.md`, `TASKS.md` y `.agents/skills/git-governance/SKILL.md` antes de tocar Git.

Objetivo: crear un monolito modular que convierta requisitos en APIs REST pequeñas, las valide funcionalmente y mediante controles técnicos inspirados por ISO/IEC 27001:2022, corrija fallos y reutilice Golden Routes verificadas. NO afirmar certificación ISO.

Haz preflight de Git y verifica que existen `main` y `dev`. No crear ramas desde `main`. Si falta `dev`, detenerte y pedir a un humano que lo prepare.

Equipo A: implementar el núcleo y adaptadores. Equipo B: implementar seguridad, evaluación de riesgos y evidencia; usar contratos y mocks si A aún no integró. Monolith-first, no microservicios.

Trabaja una tarea pequeña por rama `feature/*` desde `dev`; Conventional Commits; tests antes de PR. Conforme a la skill, puedes hacer push normal y abrir PR hacia `dev`, pero nunca integrar sin aprobación humana explícita. No borres ramas. Reporta comprobaciones reales, fallos y riesgos.
