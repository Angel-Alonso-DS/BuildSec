# Adaptación de la skill de Git aportada por el equipo

Este documento conserva el contexto histórico de la adaptación inicial. La política vigente es [git-governance](../.agents/skills/git-governance/SKILL.md): el agente puede publicar su rama de trabajo conforme a esa skill, pero nunca crea ni fusiona PR; esas acciones corresponden al humano. Ante diferencias, prevalece la skill vigente.

- Archivo fuente: `skill-work-git.md` (aportado por el integrante).
- Cambio inicial: referencias de rama `development` → `dev`; en esa adaptación no se alteraron las reglas de autonomía, commits, conflictos o seguridad.
- Contexto inicial: fallback independiente del repositorio principal. **La creación inicial de main y dev es operación humana**.
- Ramas: `feature/*` y `bugfix/*` creadas exclusivamente desde `dev`. Una tarea, una rama.
- Integración: el humano crea, revisa y fusiona el PR hacia `dev` mediante Squash and merge.
- Release: la skill bloquea todas las operaciones de agentes sobre `main`. Un humano gestiona el PR de release `dev` → `main` con controles y revisión, fuera de la skill de agentes.
- No se crea skill duplicada: la única skill Git del kit es `.agents/skills/git-governance/SKILL.md`.
- Riesgo residual: la publicación de ramas requiere permisos Git apropiados; revisar las protecciones del repositorio. La creación de PR corresponde al humano.
