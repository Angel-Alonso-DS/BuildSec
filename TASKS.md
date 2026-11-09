# División de trabajo — 2 equipos Codex

## Equipo A — Núcleo y orquestación
**Rama**: `feature/core-orchestrator`
**Propiedad**: `src/core/`, `src/api/`, `src/generation/`, `tests/core/`, `tests/api/` (ajustar al stack real).
1. Inventariar repositorio; detectar stack, scripts y estado de tests. No reescribir sin razón.
2. Estabilizar contratos `Project`, `Goal`, `Execution`, `Requirement`, `ValidationResult` en `CONTRACTS.md`.
3. Implementar Goal Mode y máquina de estados, reintentos con límite y timeout.
4. Crear interfaces adaptadoras `Generator`, `Validator`, `EvidenceStore`, `MemoryStore` y sus dobles de prueba.
5. Integrar generación de una API REST pequeña con resultados reproducibles.
6. Integrar Lesson Manager y recuperación de Golden Routes solo si superaron tests.
7. Crear API/backend y/o CLI mínimo para ejecutar un goal y consultar estado.
8. Tests unitarios, de integración y flujo end-to-end en entorno controlado.
**Entrega**: PR A1 contratos+orquestador, PR A2 generación+memoria.

## Equipo B — ISO 27001, seguridad y evidencia
**Rama**: `feature/security-evidence`
**Propiedad**: `src/security/`, `src/evidence/`, `tests/security/`, `tests/evidence/`, `docs/security/`.
1. Declarar alcance normativo: referencias ISO/IEC 27001:2022 A.8.25, A.8.26, A.8.28, A.8.29; sin textos normativos extensos ni claim de conformidad.
2. Construir esquema `Risk`, `SecurityControl`, `SecurityRequirement`, `Evidence` y mapeo requisito-prueba-control.
3. Implementar identificador de riesgos con regla reproducible para prioridad; registrar incertidumbre y aprobación humana para aceptar riesgos.
4. Implementar validadores técnicos acotados: comprobación de dependencias, detección de secretos de prueba, SAST si está disponible, y test de autorización para API de ejemplo.
5. Estados de validación `passed|failed|skipped|error`; falla cerrada si el check obligatorio no pudo ejecutarse.
6. Implementar Evidence Manager con hashes, versión de código, herramientas, command, exit code y logs sin secretos.
7. Tests de falsos positivos, controles no aplicables y evidencia íntegra.
8. Reporte técnico (no certificado ISO).
**Entrega**: PR B1 riesgos+controles, PR B2 security validation+evidencia.

## Integración y demo (ambos)
1. A define adapters y mocks primero; B implementa interfaces sin editar núcleo.
2. Ambos integran mediante PR hacia dev; ambos revisan los cambios y CI.
3. Demo: API REST con ruta vulnerable de prueba -> fallo -> corrección -> tests -> lección -> tarea similar recupera Golden Route.
4. Comparar escenarios con/sin memoria bajo misma tarea y presupuesto; reportar números reales, no promesas.

## Política de dependencias
B puede comenzar con mocks locales del contrato estable, no esperar al backend. No compartir una sola working tree simultáneamente; usar clones separados o git worktrees. Toda modificación de CONTRACTS.md requiere PR y revisión de ambos.
