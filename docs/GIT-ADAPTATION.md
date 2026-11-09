# Adaptación de la skill de Git aportada por el equipo

- Archivo fuente: `skill-work-git.md` (aportado por el integrante).
- Cambio efectuado: referencias de rama `development` → `dev`; no se han alterado sus reglas de autonomía, commits, conflictos o seguridad.
- Repositorio: nuevo fallback independiente del repositorio principal. **Creación inicial de main y dev es operación humana**.
- Ramas: `feature/*` y `bugfix/*` creadas exclusivamente desde `dev`. Una tarea, una rama.
- Integración: PR + Squash and merge hacia `dev` con autorización humana individual.
- Release: la skill bloquea todas las operaciones de agentes sobre `main`. Un humano gestiona el PR de release `dev` → `main` con controles y revisión, fuera de la skill de agentes.
- No se crea skill duplicada: la única skill Git del kit es `.agents/skills/git-governance/SKILL.md`.
- Riesgo residual: la skill permite push y creación de PR autónomos; revisar permisos de tokens GitHub y reglas de protección de ramas.
