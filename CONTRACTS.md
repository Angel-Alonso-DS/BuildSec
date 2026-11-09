# Contratos mínimos v1 — BuildSys

## Estados de Execution
`CREATED -> PLANNING -> RISK_ASSESSMENT -> GENERATING -> VALIDATING -> LEARNING -> COMPLETED`
Desde `VALIDATING`, si falla y quedan intentos -> `GENERATING`; si se agotan -> `FAILED`; bloqueos requieren `BLOCKED`. `CANCELLED` terminal. `COMPLETED` requiere validaciones obligatorias `passed`.

## API interna de adapters
- `Generator.generate(goal, workspace, previous_feedback) -> GenerationResult`
- `Validator.validate(workspace, required_checks) -> list[ValidationResult]`
- `EvidenceStore.save(result, revision, artifacts) -> EvidenceRef`
- `MemoryStore.find(goal, constraints) -> list[GoldenRoute]`
- `MemoryStore.promote(lesson, evidence_refs) -> GoldenRoute` SOLO si tests reproducibles pasan.

## Payload JSON mínimo
```json
{
  "schemaVersion": "1.0",
  "executionId": "run-001",
  "goal": "API REST con endpoint /health y CRUD de items",
  "requirements": [{"id": "F-01", "kind": "functional", "acceptance": "GET /health retorna 200"}, {"id": "S-01", "kind": "security", "acceptance": "Ruta admin rechaza usuario no autorizado", "controlRefs": ["A.8.26", "A.8.29"]}],
  "validation": [{"requirementId": "S-01", "status": "passed", "tool": "pytest", "exitCode": 0, "evidenceId": "ev-01"}]
}
```

## Reglas de integración
- `status`: exclusivamente `passed|failed|skipped|error`. Un check omitido jamás pasa implícitamente.
- `Risk`: `id`, `asset`, `threat`, `likelihood` (1-5), `impact` (1-5), `treatment`, `owner`, `residualRisk`, `status`.
- `Evidence`: `id`, `executionId`, `codeRevision`, `sha256`, `timestamp`, `command`, `toolVersion`, `exitCode`, `logPath`, `redacted`.
- El número de control ISO es una referencia de trazabilidad, NO una prueba automática de cumplimiento.
- API HTTP externa y stack de frontend: a definir tras inspección del repo. No imponer endpoints ficticios como existentes.
