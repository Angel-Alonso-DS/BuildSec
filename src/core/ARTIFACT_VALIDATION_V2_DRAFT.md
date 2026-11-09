# Validación de artefactos v2 — borrador para revisión A/B

**Estado:** propuesta técnica no aprobada, no sustituye `CONTRACTS.md` v1 y no autoriza ejecución de código. La propuesta de Equipo A está en `ARTIFACT_VALIDATION_PROPOSAL.md`, integrada en `origin/dev` en el PR #7; la integración de generación está en el PR #8. No se pudo obtener el dictamen técnico de B: no figura en el árbol ni en las ramas remotas visibles, y el conector de revisión del PR #7 devolvió repositorio no encontrado. Los valores y decisiones de este borrador son propuestas de arquitectura, no acuerdos ni afirmaciones del Equipo B. Deben confrontarse con su dictamen y aprobarse conjuntamente antes de modificar el contrato vigente.

## 1. Alcance, tipos y convenciones

Monolito modular: A posee orquestación, normalización y puertos compartidos; B implementa riesgos, validadores de seguridad y evidencia. Sandbox y almacenamiento son adaptadores internos con límites de confianza explícitos, no servicios obligatorios. `id` es un UUID v4 minúsculo; `sha256` es 64 caracteres hexadecimales minúsculos. `timestamp` es RFC 3339 UTC con sufijo `Z`; duraciones y límites son enteros positivos. IDs son opacos y no llevan claves, rutas, texto generado ni URLs. Campos sin `?` son obligatorios. Los ejemplos no representan código ejecutable ni pruebas de aislamiento.

```text
ArtifactRef { schema_version: "2.0", id: UUID, kind: "source-bundle-v1",
              sha256: Hash, size_bytes: uint64 }
CheckRef { id: string, version: string, config_sha256: Hash }
```

Una referencia identifica **exactamente** los bytes canónicos y su tipo; el ID, tipo, tamaño y hash no cambian. Dos IDs pueden apuntar a bytes iguales. El hash de esos bytes es diferente del hash del texto de una respuesta del proveedor si la representación cambia. El proveedor se normaliza antes de almacenar; ningún puerto de validación depende de OpenAI.

## 2. Canonicalización `source-bundle-v1`

La entrada es una lista de archivos regulares `(ruta, bytes)`; contenido binario se conserva byte por byte, sin transcodificar ni convertir saltos de línea. El conjunto debe contener entre 1 y 10 000 archivos, cada archivo como máximo 64 MiB, y como máximo 256 MiB de contenido total. Se rechazan enlaces simbólicos o duros, dispositivos, FIFOs, sockets, directorios como entradas, permisos ejecutables relevantes, metadatos y nombres duplicados; los directorios vacíos no se representan. Si un archivo tiene permisos ejecutables, se rechaza: v1 del bundle no los codifica.

Cada ruta es texto Unicode válido normalizado NFC; solo se acepta ruta relativa con `/` como separador, sin barra inicial/final, `\\`, NUL, componentes vacíos, `.` o `..`. Rechazar caracteres de control U+0000–U+001F y U+007F, y los componentes `secrets` y `.git` sin distinción de mayúsculas/minúsculas. Se rechazan colisiones después de NFC y casefold, independientemente del sistema operativo. Cada ruta UTF-8 tiene entre 1 y 4096 bytes; no se siguen enlaces al recopilar archivos. El lector debe verificar que las entradas siguen siendo archivos regulares durante la captura.

Ordenar por bytes UTF-8 de la ruta normalizada, ascendente. El stream canónico es la concatenación exacta de:

1. 8 bytes ASCII `BSBNDL01`.
2. Número de archivos `N` como uint64 big-endian.
3. Por cada archivo, `uint32be(len(path_utf8)) || path_utf8 || uint64be(len(content)) || content`.

`size_bytes` es el tamaño total del stream, incluidos prefijo y longitudes. `sha256` es SHA-256 del stream completo. No se añaden saltos de línea ni terminadores. `uint32be`/`uint64be` son enteros sin signo de 4/8 bytes, sin padding adicional. El parser debe rechazar longitudes fuera de rango, duplicados, orden incorrecto, datos truncados o bytes extra. El materializador debe usar creación segura relativa a un directorio aislado, sin seguir enlaces ni permitir colisiones; vuelve a verificar el hash de los bytes realmente usados antes de ejecutar cualquier check.

## 3. ArtifactStore: inmutabilidad e integridad

```text
ArtifactStore.put(kind, canonical_bytes, idempotency_key) -> ArtifactRef
ArtifactStore.get(ref: ArtifactRef) -> bytes
```

`put` valida formato y límites antes de persistir, calcula tamaño y hash en servidor y devuelve solo tras persistencia atómica de contenido y referencia. Un mismo `idempotency_key` en el mismo ámbito de proyecto y operación con idéntico `(kind, sha256, size_bytes)` devuelve exactamente la misma referencia; con datos diferentes devuelve `IDEMPOTENCY_CONFLICT`. Las claves se conservan al menos durante la retención del artefacto; caducidad y borrado se registran por política del proyecto. Sin un identificador de proyecto aislado no se implementa almacenamiento multiusuario.

`get` comprueba identidad, tipo, tamaño y SHA-256 de los bytes devueltos; no devuelve bytes parciales ante fallo. Contenido y metadatos son de solo lectura tras commit; no hay `update`. La retirada autorizada debe producir `ARTIFACT_NOT_FOUND` para futuras lecturas y preservar referencias de auditoría según política de retención, sin reutilizar IDs. Corrupción produce `INTEGRITY_ERROR` y bloquea validación; caída o límite de almacenamiento produce `STORE_UNAVAILABLE`/`LIMIT_EXCEEDED`, nunca éxito. Las implementaciones deben impedir lecturas cruzadas de proyecto y no registrar contenido ni credenciales.

## 4. Riesgos y checks obligatorios

```text
Risk { id, asset, threat, likelihood: 1..5, impact: 1..5, score: 1..25,
       treatment, owner, residual_risk, status, uncertainty: string? }
RiskAssessment { schema_version: "2.0", id: UUID, execution_id: UUID,
                 artifact: ArtifactRef, policy_id: string, policy_version: string,
                 policy_sha256: Hash, risks: list[Risk], required_checks: list[CheckRef],
                 created_at: timestamp }
```

`score = likelihood * impact`. `residual_risk` y aceptación siguen v1 y requieren revisión humana cuando corresponda; el score no implica cumplimiento ISO. Cada política de proyecto define umbrales, mapeos deterministas riesgo/requisito→check y checks mínimos obligatorios, versionados como bytes inmutables con SHA-256. La lista resultante es la unión exacta de los mínimos y los checks aplicables, deduplicada por ID y ordenada por UTF-8; dos definiciones con el mismo ID y distinta versión/configuración son `POLICY_CONFLICT`, no se elige una. Una política sin checks mínimos o un conjunto obligatorio vacío es `POLICY_INVALID`. Evaluación, requisito, política o implementación de check ausentes/desconocidos producen bloqueo o resultado `error`, nunca eliminan checks. Riesgos inciertos se conservan y la política decide de forma determinista los checks, sin aceptar el riesgo por inferencia.

El hash de política vincula el inventario de requisitos y las reglas que derivan checks; su formato canónico y catálogo inicial necesitan acuerdo de B. El orquestador no acepta como autoritativa una lista de checks procedente de una respuesta HTTP ni de código generado. Una valoración v2 debe referenciar exactamente el artefacto a validar; cambios de artefacto o política obligan a una nueva valoración.

## 5. Petición y resultado de validación

```text
ValidationRequest { schema_version: "2.0", id: UUID, execution_id: UUID,
                    attempt: uint32, artifact: ArtifactRef, assessment_id: UUID,
                    policy_sha256: Hash, required_checks: list[CheckRef],
                    deadline: timestamp, idempotency_key: string }
ValidationResult { schema_version: "2.0", request_id: UUID, artifact_id: UUID,
                   artifact_sha256: Hash, check: CheckRef, requirement_ids: list[string],
                   status: "passed" | "failed" | "skipped" | "error",
                   reason_code: string, evidence_ids: list[UUID] }
ArtifactValidator.validate_artifact(request: ValidationRequest) -> list[ValidationResult]
```

Los checks de la petición deben coincidir exactamente con los derivados de `RiskAssessment`, con igual ID, versión y hash; no se aceptan sustituciones. Se devuelve un único resultado por check, vinculado a petición y hash solicitado. Un `passed` exige evidencia íntegra y disponible de ejecución satisfactoria del check exacto sobre el artefacto; `failed` indica incumplimiento observado; `skipped` indica no ejecutado o no aplicable; `error` indica fallo de infraestructura, integridad o resultado incompleto. Ambos últimos impiden éxito para checks obligatorios, aunque `skipped` sea justificado. Un resultado adicional, ausente, duplicado, con versión o hash diferentes, o con evidencia inválida invalida el lote y produce bloqueo. Resultado y evidencia no contienen código, claves ni salida sin redacción.

| Condición de checks obligatorios | Decisión del orquestador |
| --- | --- |
| Todos `passed`, exactamente una vez y evidencia válida | `LEARNING`, después `COMPLETED` |
| Alguno `failed` y quedan intentos | `GENERATING`, con feedback sanitizado |
| Alguno `failed` y no quedan intentos | `FAILED` |
| `skipped`, `error`, lote inválido o imposibilidad de ejecutar | `BLOCKED` |
| Cancelación confirmada | `CANCELLED` |

`FAILED` y `BLOCKED` no implican validación satisfactoria. Un reintento de generación que cambia bytes crea una referencia y evaluación nuevas; nunca reutiliza resultados de otro hash. `reason_code` es un código estable sin detalles del proveedor; no se transmite el mensaje bruto de excepciones.

## 6. Sandbox: límites, estados y cancelación

```text
SandboxRequest { schema_version: "2.0", id: UUID, validation_request_id: UUID,
                 artifact: ArtifactRef, check: CheckRef, image_digest: "sha256:" + Hash,
                 argv: list[string], deadline: timestamp, limits: SandboxLimits,
                 idempotency_key: string }
SandboxLimits { wall_ms: uint32, cpu_ms: uint32, memory_bytes: uint64,
                pids: uint32, output_bytes: uint64, storage_bytes: uint64 }
SandboxResult { schema_version: "2.0", request_id: UUID, state: enum,
                artifact_sha256: Hash, exit_code: int32?, started_at: timestamp?,
                finished_at: timestamp, stdout_ref: string?, stderr_ref: string?,
                resource_usage: map, reason_code: string }
SandboxRunner.start(request) -> SandboxHandle
SandboxRunner.wait(handle, deadline) -> SandboxResult
SandboxRunner.cancel(handle, idempotency_key) -> SandboxResult
```

Política propuesta de máximos por check: `wall_ms <= 30000`, `cpu_ms <= 20000`, `memory_bytes <= 536870912`, `pids <= 64`, `output_bytes <= 1048576`, `storage_bytes <= 268435456`. El deadline efectivo es el mínimo del deadline de ejecución y `start + wall_ms`. Peticiones sin algún límite, con valores no positivos o por encima de los máximos se rechazan antes de iniciar. El ejecutable y argumentos proceden de un catálogo confiable de checks, no del artefacto; se usa `argv`, sin shell interpolado. La imagen se fija por digest permitido, verificado previamente; sin descarga durante la ejecución. El sandbox no recibe red por defecto, claves, secretos, sockets, dispositivos ni directorios del host distintos de lo estrictamente autorizado; ejecuta sin privilegios, con filesystem efímero y controles efectivos de recursos. No se monta el almacén de credenciales.

| Estado del sandbox | Transiciones permitidas | Significado |
| --- | --- | --- |
| `CREATED` | `RUNNING`, `CANCELLED`, `ERROR` | Preparado, sin proceso activo |
| `RUNNING` | `SUCCEEDED`, `FAILED`, `TIMED_OUT`, `CANCELLED`, `ERROR` | Proceso activo y sujeto a límites |
| `SUCCEEDED` | ninguna | Salida 0 y finalización confirmada |
| `FAILED` | ninguna | Finalizó con salida distinta de 0 |
| `TIMED_OUT` | ninguna | Deadline agotado y proceso aislado terminado |
| `CANCELLED` | ninguna | Cancelación y terminación confirmadas |
| `ERROR` | ninguna | Arranque, aislamiento, integridad o medición no verificables |

Los estados terminales son inmutables. `cancel` es idempotente y retorna el resultado terminal ya existente; para un proceso activo detiene todos los descendientes, espera confirmación, y solo entonces devuelve `CANCELLED`. Si no se puede confirmar la terminación devuelve `ERROR` y se bloquea la ejecución; nunca informa cancelación exitosa prematuramente. Al vencer límites, el runner mata todo el grupo y confirma su desaparición antes de `TIMED_OUT`; salida truncada se marca y no permite inferir `passed` si impide comprobar el check. `SUCCEEDED` del sandbox no implica por sí mismo `passed`: el validador interpreta el check y registra evidencia. La terminación del thread del orquestador no equivale a matar el sandbox. Un doble de pruebas no demuestra aislamiento real.

## 7. Evidencia y trazabilidad

```text
EvidenceRecord { schema_version: "2.0", id: UUID, execution_id: UUID,
                 validation_request_id: UUID, sandbox_request_id: UUID?,
                 artifact_id: UUID, artifact_sha256: Hash, assessment_id: UUID,
                 policy_sha256: Hash, check: CheckRef, requirement_ids: list[string],
                 control_refs: list[string], code_revision: string,
                 tool: string, tool_version: string, command: list[string],
                 started_at: timestamp, finished_at: timestamp, exit_code: int32?,
                 status: enum, reason_code: string, redacted: true,
                 redacted_log_sha256: Hash, redacted_log_ref: string,
                 record_sha256: Hash }
EvidenceStoreV2.save(record, redacted_log, idempotency_key) -> EvidenceRef
EvidenceStoreV2.get(ref) -> (EvidenceRecord, redacted_log)
```

El hash de log se calcula sobre los bytes UTF-8 **ya redactados**; el hash del registro usa la representación canónica definida a continuación sin `record_sha256`. Registro y log se guardan atómicamente y se comprueban al leer. `code_revision` identifica la revisión de la aplicación de evaluación, no el artefacto; el hash del artefacto identifica exactamente los bytes evaluados. `command` es el argv sanitizado de catálogo, no contiene credenciales, rutas sensibles ni contenido generado. La política de redacción B debe inspeccionar los logs antes de persistir; ante fallo o incertidumbre no se guarda salida cruda y el check queda `error`. Los refs son opacos sin credenciales; controles ISO son solo referencias, no certificación.

Canónico del registro: JSON UTF-8 sin BOM, sin espacios entre tokens, claves ordenadas lexicográficamente por sus bytes UTF-8, strings NFC, enteros decimales sin ceros iniciales, booleanos JSON, sin floats ni null, arrays con orden especificado por el emisor; claves opcionales ausentes se omiten. Dentro de strings se escapan `"` como `\"`, `\` como `\\` y cada carácter U+0000–U+001F como `\u00xx` con hex minúscula; los demás caracteres Unicode válidos se codifican directamente en UTF-8, incluido `/`. Se rechazan sustitutos Unicode no emparejados y colisiones de nombres tras NFC. `requirement_ids` y `control_refs` se ordenan y deduplican por UTF-8; `command` conserva orden. Los demás tipos y formato de números deben pasar un validador de esquema estricto antes de calcular el hash. No se incluyen campos desconocidos ni `record_sha256` en el cálculo. Las fechas usan UTC con exactamente 3 decimales y `Z` (p. ej. `2026-01-01T00:00:00.000Z`).

El almacén es append-only y scoped por proyecto. Misma clave idempotente y mismos hashes devuelve el mismo `EvidenceRef`; distinto contenido con la misma clave produce `IDEMPOTENCY_CONFLICT`. Ningún registro `passed` es válido sin evidencia y log verificados, incluso si el log está vacío. Un `error` previo al arranque usa `sandbox_request_id` y `exit_code` ausentes, con evidencia del motivo cuando sea posible; fallo de escritura de evidencia impide `COMPLETED`.

## 8. Versionado y migración del orquestador

1. Aprobar conjuntamente v2 y actualizar `CONTRACTS.md` mediante PR humano. v1 permanece disponible; cada mensaje v2 exige `schema_version: "2.0"` y rechaza versiones mayores desconocidas y campos desconocidos.
2. Implementar adaptadores y pruebas de contrato por ambos equipos sin reemplazar `Validator.validate` ni `EvidenceStore.save` v1. El almacén, evaluador de riesgo y validator v2 se inyectan en el monolito. No ejecutar generación en host.
3. Introducir una capacidad explícita `artifact-validation-v2` configurada al componer la aplicación; no detectar soporte por introspección o convertir silenciosamente resultados v1. Si falta cualquier puerto requerido, `BLOCKED` o `skipped` según fase; v1 puede seguir atendiendo sus casos antiguos, pero nunca certificar el artefacto v2.
4. En v2: generar → canonicalizar → guardar artefacto → evaluar riesgos y derivar checks → construir solicitud con deadline → validar en sandbox → verificar resultados/evidencias → transición. Todo intento conserva IDs, hashes, política y revisión. Si se interrumpe, reanudar con las mismas claves idempotentes; no iniciar ejecución duplicada.
5. Activar por proyecto tras pasar las pruebas de contrato y aislamiento real; retirar el wrapper temporal que devuelve `skipped` solo cuando B entregue validación y handoff verificados. Cualquier cambio incompatible requiere nueva versión y migración aprobada.

El contrato v1 de estados y el payload JSON siguen intactos; v2 no crea automáticamente una ruta de compatibilidad HTTP. La incorporación de nuevos campos al payload público requiere acuerdo explícito. El hash y el ID se verifican en cada límite, no se confía solo en nombres de archivo.

## 9. Errores e idempotencia

Todos los puertos devuelven errores tipados sanitizados: `INVALID_REQUEST`, `UNSUPPORTED_VERSION`, `LIMIT_EXCEEDED`, `ARTIFACT_NOT_FOUND`, `INTEGRITY_ERROR`, `STORE_UNAVAILABLE`, `POLICY_INVALID`, `POLICY_CONFLICT`, `CHECK_UNAVAILABLE`, `SANDBOX_UNAVAILABLE`, `TIMED_OUT`, `CANCELLED`, `EVIDENCE_ERROR`, `IDEMPOTENCY_CONFLICT`. Error no incluido se mapea a `INTERNAL_ERROR`; ningún mensaje incluye datos brutos, secretos, trazas o código.

Claves de idempotencia son UUID v4 entregados por el orquestador y separados por operación, proyecto e intento. En `start`, repetir la misma clave y misma solicitud devuelve el mismo handle o resultado terminal; la identidad de la solicitud es SHA-256 del JSON canónico de la sección 7 aplicado a todos sus campos, incluida la clave. En solicitudes, arrays de checks se ordenan por ID UTF-8 y argv conserva orden; las fechas usan el mismo formato fijo. Solicitud distinta con igual clave produce conflicto. Un runner que tras un fallo no pueda recuperar el estado previo debe retornar `ERROR`/indeterminado y no lanzar otra ejecución. La cancelación es repetible y no altera el resultado ya terminal. `put` y `save` solo confirman tras commit atómico; los reintentos y carreras simultáneas no generan dos IDs para la misma clave. Cambiar política, artefacto, check o intento requiere clave nueva.

## 10. Pruebas de contrato y criterios de aceptación

1. Vectores binarios publicados y compartidos A/B: orden de rutas, Unicode NFC/casefold, archivo vacío y binario, rutas inválidas, colisiones, enlaces, truncado, bytes extra, límites exactos y hash de bundle reproducible en plataformas distintas.
2. Store: persistencia, hash y tamaño alterados, referencia de otro proyecto, contenido ausente, escritura parcial, carreras idempotentes, conflicto de clave, eliminación y errores sin datos sensibles.
3. Riesgos: producto 1–5, umbrales en frontera, unión determinista de checks, política/versiones en conflicto, faltas e incertidumbre; conjunto requerido vacío falla cerrado.
4. Validador/orquestador con dobles: los cuatro estados, duplicados/ausentes/extras, hash o política cambiados, evidencia ausente/corrupta, retry con nuevo hash, v1 incompatible, cancelación y transición sin falso `COMPLETED`. Verificar que `passed` solo usa el artefacto de la petición.
5. Runner con dobles: rechazo de límites, idempotencia, deadline, condiciones de carrera terminación/cancelación, salida truncada y proceso indeterminado. Estas pruebas prueban el protocolo, **no** aislamiento.
6. En entorno controlado independiente y con autorización, pruebas reales de aislamiento: sin red ni credenciales, límites de CPU/memoria/PIDs/almacenamiento/salida y eliminación de descendientes tras timeout y cancelación. Registrar plataforma, versión de kernel/runtime, configuración, resultados y límites; no inferir garantías universales a partir de una sola plataforma.
7. Evidencia: vectores de canonicalización, integridad tras recuperación, redacción con secretos sintéticos, ausencia de logs crudos, correspondencia solicitud/artefacto/check/revisión y fallos al persistir. La aceptación requiere pruebas de contrato de A y B y revisión conjunta; no hay claim ISO.
