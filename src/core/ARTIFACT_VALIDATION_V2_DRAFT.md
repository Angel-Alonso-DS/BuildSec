# Contrato propuesto v2: validación de artefactos del MVP

**Estado: candidato para revisión conjunta A/B; no aprobado ni implementado.** El contrato vigente sigue siendo `CONTRACTS.md` v1. Este documento sustituye el borrador `898422b` para revisión, sin modificar v1 ni atribuir aprobación al Equipo B. El dictamen anterior con siete observaciones no está disponible; la matriz del §12 se refiere únicamente a la revisión técnica disponible en esta conversación. Se mantienen el monolito modular y los puertos internos; no se introducen servicios. Los controles ISO/IEC 27001:2022 son referencias, no certificación ni declaración de conformidad.

## 1. Convenciones, contexto y autorización

Los modelos son esquemas lógicos internos; se prohíben campos desconocidos y valores `null`: un campo `?` ausente se omite. Versiones de mensajes: `schema_version = "2.0"`; versiones no soportadas se rechazan antes de efectos. `Hash` es SHA-256 en hex minúsculo de 64 caracteres; `UUID` es UUID v4 en formato canónico minúsculo. Los IDs semánticos de requisito, riesgo, política y check son ASCII `[A-Za-z0-9][A-Za-z0-9._-]{0,127}`; no se normalizan por mayúsculas. Listas definidas como conjuntos son únicas y ordenadas por bytes UTF-8. Timestamps son UTC RFC 3339 con exactamente tres decimales y `Z`. Límites y duraciones son enteros positivos; un deadline vencido falla antes de iniciar.

```text
AuthContext { project_id: UUID, principal_id: UUID, auth_session_id: UUID,
              permissions: set[Permission] }
Permission = ARTIFACT_READ | ARTIFACT_WRITE | RISK_ASSESS | VALIDATE |
             SANDBOX_RUN | EVIDENCE_READ | EVIDENCE_WRITE | POLICY_ADMIN
CheckRef { id: ID, version: ID, config_sha256: Hash }
ArtifactRef { schema_version: "2.0", id: UUID, kind: "source-bundle-v1",
              sha256: Hash, size_bytes: uint64 }
```

`AuthContext` lo crea el borde confiable tras autenticación y autorización; nunca se construye desde un payload, artefacto, modelo o sandbox. En todos los puertos se pasa `ctx` explícitamente. El adaptador vuelve a autorizar permiso y pertenencia al proyecto en cada operación; referencias, handles, claves y registros pertenecen a un único proyecto y no son capacidades por sí solos. Lecturas cruzadas y recursos inexistentes devuelven indistintamente `NOT_FOUND`; acciones no autorizadas sin referencia devuelven `FORBIDDEN`. No se pasan tokens ni `AuthContext` a procesos no confiables: el supervisor realiza las operaciones autorizadas fuera del sandbox. Ejemplo: `ARTIFACT_READ` del proyecto A no permite recuperar un ID del proyecto B. Pruebas: falsificación de contexto, revocación y acceso cruzado por cada puerto.

## 2. Artefacto y canonicalización reproducible

`ArtifactRef` es inmutable: `(project_id, id)` se asigna una sola vez y siempre denota el mismo tipo, tamaño y hash de stream canónico. Dos IDs pueden referir al mismo contenido. No contiene texto, credenciales ni rutas locales.

**Captura.** Las entradas son archivos regulares tomados de una fuente ya abierta y controlada: `CapturedFile { path: string, bytes: byte[], capture: CaptureMeta }`; `CaptureMeta` contiene `entry_type`, `link_count`, `executable`, `stable_snapshot`. El adaptador de captura confiable determina estos campos, no el artefacto. En filesystem usa apertura relativa al directorio raíz con `no-follow`, inspección por descriptor antes y después de leer y snapshot inmutable, o rechaza la captura si no puede garantizar estabilidad. Se aceptan solo `entry_type=regular`, `link_count=1`, `executable=false`, `stable_snapshot=true`; se rechazan enlaces, directorios como entradas y tipos especiales. Una fuente de bytes en memoria suministra una prueba de origen equivalente por el adaptador confiable; no inventa metadatos de filesystem. Los metadatos de captura son controles previos, no forman parte del stream.

**Formato `source-bundle-v1`.** Usar Unicode **15.0.0** para NFC y casefold completo por defecto, con tablas fijadas; si la implementación no dispone exactamente de esa versión, rechazar la petición. Cada ruta NFC es relativa, UTF-8 válida, 1–4096 bytes, separada por `/`, sin componentes vacíos, `.` o `..`, barra inicial/final, `\\`, NUL ni controles U+0000–001F/U+007F. Rechazar componentes `secrets` y `.git` por casefold, colisiones tras NFC+casefold y conflictos archivo/directorio como `a` y `a/b`. Se rechazan nombres no representables sin pérdida en la plataforma de materialización. No se representan directorios vacíos ni metadatos; cada bundle contiene 1–10000 archivos, máximo 64 MiB por archivo y 256 MiB de contenido total.

El contenido son bytes exactos, sin conversión de codificación o saltos de línea. Ordenar por bytes UTF-8 de rutas NFC. El stream es `ASCII("BSBNDL01") || uint64be(N) || entries`; cada entry es `uint32be(len(path_utf8)) || path_utf8 || uint64be(len(bytes)) || bytes`. `size_bytes` mide todo el stream; `sha256` cubre exactamente ese stream. Rechazar orden incorrecto, límites excedidos, duplicados, longitudes inconsistentes, truncamiento o bytes extra. El generador se normaliza antes de guardar, sin vincular el validador a un proveedor.

**Vector normativo 1:** un archivo `a.txt` con bytes hex `616263`: stream hex `4253424e444c3031000000000000000100000005612e7478740000000000000003616263`, longitud `36`, SHA-256 `5cdf8792ce2b452b492bdbaff42781ae28eee9f122dc085dcd71e095209842b7`. **Vector 2:** rutas `é.txt` y `e\u0301.txt` en el mismo bundle se rechazan tras NFC; `A` y `a` se rechazan tras casefold; `a` y `a/b` se rechazan por conflicto de tipo. Pruebas: vector 1 en dos implementaciones, binario y archivo vacío, límites exactos y +1, Unicode distinto a 15.0.0, carreras de captura, enlaces, truncado y bytes extra.

## 3. Almacenamiento, materialización e integridad

```text
ArtifactStore.put(ctx, kind, canonical_bytes, idempotency_key: UUID) -> ArtifactRef
ArtifactStore.get(ctx, ref: ArtifactRef) -> bytes
```

`put` requiere `ARTIFACT_WRITE`, valida formato, calcula tamaño/hash y confirma solo después de commit atómico durable de bytes y metadatos. `get` requiere `ARTIFACT_READ`, comprueba proyecto, ID, tipo, tamaño y SHA-256 antes de entregar bytes; nunca entrega lectura parcial. Sin `update`; la eliminación autorizada por política no reutiliza IDs, devuelve posteriormente `NOT_FOUND` y conserva el registro de auditoría. `INTEGRITY_ERROR` o fallo de almacenamiento bloquea validación. El contenido generado se mantiene privado y no se incluye por defecto en logs o respuestas HTTP.

El supervisor obtiene los bytes verificados, los parsea y materializa usando apertura relativa segura y no-follow en un directorio nuevo controlado solo por el supervisor. Recalcula el stream a partir de los archivos materializados y compara tamaño/hash; cualquier diferencia produce `INTEGRITY_ERROR`. Antes de lanzar checks los presenta en un montaje de solo lectura, inmutable para el proceso aislado y sus descendientes, sin referencias mutables a la fuente original; comprueba que el runtime aplica efectivamente ese montaje. Los archivos de salida se escriben en un directorio efímero separado y no pueden reemplazar las entradas. El runner informa el hash verificado y `ValidationResult`/evidencia lo vinculan; fallos de aislamiento o integridad impiden `passed`. El almacén no comparte credenciales, socket ni filesystem con el sandbox. Pruebas: alteración de bytes, symlink de destino, sustitución entre captura/materialización/ejecución y escritura en montaje de entrada; los dobles solo comprueban el protocolo, no el aislamiento.

## 4. RiskAnalyzer y derivación de checks

```text
Requirement { id: ID, kind: "functional" | "security", acceptance: string,
              control_refs: set[ID], tags: set[ID] }
RequirementsSnapshot { id: UUID, requirements: list[Requirement], sha256: Hash }
Risk { id: ID, requirement_ids: set[ID], asset: string, threat: string,
       likelihood: 1..5, impact: 1..5, score: 1..25,
       treatment: string, owner: string, residual_risk: string,
       status: string, uncertainty: string? }
CheckDefinition { check: CheckRef, requirement_kinds: set[string],
                  requirement_tags_any: set[ID], min_risk_score: int?,
                  finding_rule_ids_any: set[ID], mandatory: bool }
CheckCatalog { id: ID, version: ID, sha256: Hash, definitions: list[CheckDefinition] }
RiskPolicy { id: ID, version: ID, sha256: Hash, low_max: 1..23,
             medium_max: 2..24, baseline_checks: set[ID], risk_rules: list[RiskRule] }
RiskRule { id: ID, kind: "functional" | "security", tag: ID?,
           asset: string, threat: string, likelihood: 1..5, impact: 1..5,
           treatment: string, owner: string }
Finding { id: ID, requirement_id: ID, rule_id: ID, artifact_sha256: Hash }
RiskAssessment { id: UUID, execution_id: UUID, phase: "pre" | "post",
                 artifact: ArtifactRef?, requirements_sha256: Hash,
                 policy_sha256: Hash, catalog_sha256: Hash,
                 risks: list[Risk], required_checks: list[CheckRef], created_at: timestamp }
RiskAnalyzer.assess_pre(ctx, execution_id, requirements, policy, catalog, idempotency_key) -> RiskAssessment
RiskAnalyzer.assess_post(ctx, pre_assessment_id, artifact, findings, policy, catalog, idempotency_key) -> RiskAssessment
FindingProvider.inspect(ctx, artifact) -> list[Finding]
```

Requiere `RISK_ASSESS`. Todos los inputs deben pertenecer al mismo proyecto y ser snapshots inmutables autorizados. El snapshot de requisitos contiene al menos uno, IDs únicos y lista ordenada por ID. Sus bytes canónicos son el JSON §8 de sus campos `id` y `requirements`, excluido `sha256`; sus sets se ordenan por bytes UTF-8. Política y catálogo se serializan igual excluyendo sus respectivos campos `sha256`; `baseline_checks` y los sets de cada definición se ordenan, `risk_rules` por `id` y `definitions` por `check.id`; se comprueban sus hashes antes de usarlos. El hash de requisitos es distinto del hash de política. El catálogo tiene IDs únicos; misma ID con distinta versión/configuración es `POLICY_CONFLICT`. La política exige `1 <= low_max < medium_max < 25`, al menos un baseline y que todas sus IDs existan en catálogo.

El analizador B aplica exactamente las reglas del snapshot sin llamar a un modelo ni inferir controles. Para cada requisito y `RiskRule` cuyo `kind` coincida y cuyo `tag` esté ausente o figure en los tags del requisito, crea un riesgo con ID `<rule.id>.<requirement.id>`; si supera 128 caracteres o dos pares producen el mismo ID se rechaza la política. Copia `asset`, `threat`, probabilidad, impacto, tratamiento y owner de la regla; `requirement_ids` contiene solo ese requisito, `residual_risk="unassessed"`, `status="open"` y `uncertainty` se omite. Cada requisito debe coincidir con al menos una regla, de lo contrario `POLICY_INVALID`. IDs de regla y de hallazgo son únicos; riesgos se ordenan por ID. En post se parte exactamente de los riesgos pre y de las reglas/snapshots pre; cada `Finding` debe vincular el hash del artefacto actual y una combinación requisito/regla que ya coincida, y solo señala el riesgo correspondiente; no modifica puntaje ni elimina riesgo. Los hallazgos provienen del `FindingProvider` confiable inyectado por B que inspecciona datos sin ejecutar código; si un check del catálogo requiere hallazgos y el proveedor falta, falla o no puede verificar su procedencia, post falla cerrado. Si ningún check requiere hallazgos, se usa la lista vacía. Hallazgos inválidos u origen no confiable bloquean. Como MVP no interpreta contenido con IA. Para cada riesgo `score = likelihood * impact`; banda baja `1..low_max`, media `low_max+1..medium_max`, alta `medium_max+1..25`. Aceptar riesgo o tratamiento/residual corresponde a humano; no desactiva checks automáticamente. ID y fecha de evaluación no afectan el contenido determinista. Regla desconocida, motor no disponible o requisito sin regla producen `error`/`BLOCKED`.

Derivación exacta: iniciar con baseline; para cada `CheckDefinition`, incluir su ID si existe un requisito cuyo `kind` pertenece a `requirement_kinds` y (`requirement_tags_any` es vacío o intersecta sus tags), y además (`min_risk_score` ausente o existe un riesgo asociado a ese requisito con score al menos ese mínimo), y además (`finding_rule_ids_any` vacío o existe un hallazgo validado de ese requisito cuyo `rule_id` está en ese set). En pre no hay hallazgos, así que las reglas que los requieren solo pueden agregar checks en post. Cada `finding_rule_ids_any` debe referenciar reglas de riesgo existentes. La unión se deduplica por ID y devuelve su `CheckRef` exacto, ordenada por ID. `mandatory` debe ser `true` para todos los checks incluidos en MVP; no hay exenciones automáticas. Post conserva riesgos pre y puede añadir checks por hallazgos, nunca retirar checks pre; reutiliza los hashes de requisitos/política/catálogo pre y añade la referencia de artefacto exacta. Si cambia un snapshot se inicia nueva evaluación pre. Un conjunto vacío o check no implementado bloquea.

**Ejemplo:** baseline `health`, catálogo `auth` para kind `security`, tag `admin` y score mínimo 12; requisito `S1` security con tag admin y riesgo 3×4=12 implica checks ordenados `[auth, health]`. Con score 11, solo `[health]`; si `auth` es baseline, siempre incluye ambos. Pruebas: orden de entrada, score 1/25 y fronteras 11/12, falta de regla, ID duplicado, cambio de hash, incertidumbre, derivación post monótona y acceso cruzado.

## 5. ValidationRequest, resultados y máquina v1

```text
ValidationRequest { schema_version: "2.0", id: UUID, execution_id: UUID,
                    attempt: uint32, artifact: ArtifactRef, post_assessment_id: UUID,
                    requirements_sha256: Hash, policy_sha256: Hash, catalog_sha256: Hash,
                    required_checks: list[CheckRef], deadline: timestamp, idempotency_key: UUID }
ValidationResult { schema_version: "2.0", request_id: UUID, artifact_id: UUID,
                   artifact_sha256: Hash, check: CheckRef, requirement_ids: set[ID],
                   status: "passed" | "failed" | "skipped" | "error",
                   reason_code: ID, evidence_ids: set[UUID] }
ArtifactValidator.validate_artifact(ctx, request) -> list[ValidationResult]
```

Requiere `VALIDATE`. El servidor reconstruye los checks desde evaluación post autorizada y compara exactamente request, checks, referencias y todos los hashes; no confía en listas del cliente. Devuelve exactamente un resultado por check: `passed` solo con evidencia persistida, íntegra, autenticada y ligada al mismo artefacto/check/solicitud; `failed` incumplimiento comprobado; `skipped` no ejecutado/no aplicable; `error` fallo de ejecución, aislamiento o infraestructura. Ausentes, extras, duplicados, hash/check/evidencia incorrectos invalidan el lote.

| Prioridad | Condición comprobada | Transición |
|---|---|---|
| 1 | cancelación confirmada antes de decisión terminal | `CANCELLED` |
| 2 | cancelación no confirmada, lote inválido, cualquier `error` o `skipped`, check no disponible | `BLOCKED` |
| 3 | algún `failed`, intentos restantes | `GENERATING` |
| 4 | algún `failed`, intentos agotados | `FAILED` |
| 5 | todos los checks obligatorios `passed` con evidencia verificada | `LEARNING` → `COMPLETED` |

La cancelación solicitada no es confirmación: si no se acredita terminación, prioridad 2. `FAILED`+`error` → `BLOCKED`, incluso si quedan intentos; `failed`+`passed` → prioridad 3/4. Se preserva la máquina externa v1 `CREATED → PLANNING → RISK_ASSESSMENT → GENERATING → VALIDATING → LEARNING → COMPLETED`: pre ocurre en `RISK_ASSESSMENT`; en `GENERATING`, después de producir y guardar el artefacto, post ocurre como subpaso interno antes de entrar en `VALIDATING`. Si post falla, transición a `BLOCKED`. En retry `VALIDATING → GENERATING`, se guarda nuevo artefacto y se repite post sobre él y pre vigente; nunca se reutiliza evidencia de otro hash. No se agregan estados externos ni se altera el payload v1. Pruebas: cinco prioridades, estados mixtos, v1 exacta, retry con artefacto diferente, política modificada y checks no solicitados.

## 6. Sandbox: snapshots, terminales y cancelación

```text
SandboxLimits { wall_ms: uint32, cpu_ms: uint32, memory_bytes: uint64,
                pids: uint32, output_bytes: uint64, storage_bytes: uint64 }
SandboxRequest { schema_version: "2.0", id: UUID, validation_request_id: UUID,
                 artifact: ArtifactRef, check: CheckRef, image_digest: "sha256:"+Hash,
                 argv: list[string], deadline: timestamp, limits: SandboxLimits,
                 idempotency_key: UUID }
SandboxSnapshot { request_id: UUID, state: "CREATED" | "RUNNING", started_at: timestamp? }
SandboxResult { request_id: UUID, state: "SUCCEEDED" | "FAILED" | "TIMED_OUT" |
                "CANCELLED" | "ERROR", artifact_sha256: Hash, exit_code: int32?,
                started_at: timestamp?, finished_at: timestamp, output_truncated: bool,
                reason_code: ID, redacted_output_ref: string? }
SandboxRunner.start(ctx, request) -> SandboxHandle
SandboxRunner.poll(ctx, handle) -> SandboxSnapshot | SandboxResult
SandboxRunner.wait(ctx, handle, wait_deadline) -> SandboxSnapshot | SandboxResult
SandboxRunner.cancel(ctx, handle, idempotency_key: UUID) -> SandboxSnapshot | SandboxResult
```

Requiere `SANDBOX_RUN`; handle opaco ligado a proyecto y request. `wait` hasta deadline de espera retorna snapshot si aún no es terminal; no cancela el proceso. `cancel` solicita la terminación y puede devolver snapshot mientras está pendiente; `CANCELLED` solo cuando no quedan descendientes vivos y la terminación se confirmó. El orquestador espera confirmación hasta el deadline global y si no la obtiene se bloquea con `ERROR` operacional, sin etiquetar el proceso como terminado. Si el runner pierde el estado, retorna terminal `ERROR` con terminación **no confirmada**, marca el entorno en cuarentena y no reutiliza ni vuelve a lanzar la misma clave. Un resultado terminal es inmutable; cancelación de uno ya terminal devuelve ese mismo resultado.

| Estado | Transiciones permitidas |
|---|---|
| `CREATED` | `RUNNING`, `CANCELLED`, `ERROR` |
| `RUNNING` | `SUCCEEDED`, `FAILED`, `TIMED_OUT`, `CANCELLED`, `ERROR` |
| terminales | ninguna |

`SUCCEEDED` requiere exit 0; `FAILED`, exit no cero; `TIMED_OUT` y `CANCELLED` requieren terminación de todos los descendientes confirmada; `ERROR` no implica terminación confirmada. `started_at` y `exit_code` solo están presentes si ocurrieron; `finished_at` identifica la emisión terminal, no garantiza terminación en `ERROR`. El deadline efectivo es mínimo entre deadline global y el tiempo monotónico de inicio + `wall_ms`; deadline UTC se traduce a un presupuesto monotónico al inicio, sin extenderlo al ajustar el reloj. Al agotar límite, matar y confirmar antes de `TIMED_OUT`; sin confirmación, cuarentena y `ERROR`. `SUCCEEDED` no es `passed`; el validator interpreta el check. Salida truncada no permite `passed` si se pierde información necesaria.

Límites máximos propuestos por check: wall 30000 ms, CPU acumulada 20000 ms, memoria 536870912 bytes, 64 procesos, salida 1048576 bytes y almacenamiento 268435456 bytes; todos se exigen y comprueban antes de arrancar. El runner rechaza un límite que el backend no pueda imponer o medir de modo verificable. Pruebas de protocolo: límites 0/máximo/máximo+1, espera no terminal, cancelación concurrente con salida, error de terminación, reinicio y clave repetida.

## 7. Entorno confiable y aislamiento

El catálogo de checks aprobado por el proyecto fija el digest de imagen, herramienta y versión, ejecutable con ruta absoluta y argv exacto; el request no puede sustituirlos. La imagen debe estar previamente disponible, verificada contra digest de una lista aprobada; no se descarga en ejecución. El proceso arranca sin shell de host ni interpolación, bajo UID no privilegiado, sin capacidades elevadas, con controles de sistema y recursos efectivos, filesystem efímero y entradas montadas solo lectura. No hay red, credenciales, socket Docker, dispositivos del host ni directorios del host, salvo el montaje de entrada verificado de §3; no hay excepción de red en MVP.

`cwd` del proceso es `/work/output`, directorio efímero vacío; entradas en `/work/input` de solo lectura; herramientas en `/opt/buildsec-tools` de solo lectura, con rutas absolutas. El entorno se crea desde cero: solo `PATH=/opt/buildsec-tools/bin`, `LANG=C.UTF-8`, `LC_ALL=C.UTF-8`, `HOME=/work/output`, `TMPDIR=/work/output/tmp`; sin heredar `OPENAI_*`, `PYTHONPATH`, `LD_*`, proxies ni variables del host. La configuración de herramienta proviene exclusivamente del catálogo confiable; desactivar descubrimiento de plugins/config desde artefacto y auto-descarga. Si el check necesita cargar código del artefacto, ese código se ejecuta solo dentro del sandbox y no puede modificar ni sustituir el arnés confiable; dependencias se fijan previamente en la imagen, sin instalar en runtime. Si el runtime no puede cumplir una garantía, `SANDBOX_UNAVAILABLE`/`BLOCKED`.

Pruebas reales, no mocks: negar red, leer credenciales/socket, sustituir herramientas, inyectar variables/plugins, escribir entradas, agotar CPU/memoria/PIDs/disco/salida y verificar descendientes tras cancelación/timeout. Registrar runtime/kernel/configuración y resultados; una prueba en una plataforma no certifica otras. Elegir y habilitar un backend real requiere decisión humana y validación específica de plataforma.

## 8. EvidenceWriteRequest y EvidenceRecord

```text
EvidenceWriteRequest { schema_version: "2.0", execution_id: UUID,
  validation_request_id: UUID, sandbox_request_id: UUID?, artifact: ArtifactRef,
  assessment_id: UUID, requirements_sha256: Hash, policy_sha256: Hash,
  catalog_sha256: Hash, check: CheckRef, requirement_ids: set[ID], control_refs: set[ID],
  code_revision: string, tool: ID, tool_version: ID, command: list[string],
  started_at: timestamp?, finished_at: timestamp, exit_code: int32?,
  status: "passed" | "failed" | "skipped" | "error", reason_code: ID }
EvidenceRecord { request: EvidenceWriteRequest, id: UUID, redacted: true,
                 redacted_log_ref: string, redacted_log_sha256: Hash,
                 record_sha256: Hash }
EvidenceStoreV2.save(ctx, write_request, redacted_log: bytes, idempotency_key: UUID) -> EvidenceRecord
EvidenceStoreV2.get(ctx, id: UUID) -> (EvidenceRecord, redacted_log: bytes)
```

`save` requiere `EVIDENCE_WRITE`, `get` requiere `EVIDENCE_READ`. El escritor no suministra ID del registro, referencia de log ni hashes persistidos: el almacén los asigna/calcula. El supervisor verifica en transacción o contra snapshots inmutables autorizados que execution, request, assessment post, proyecto, artifact ID/hash, check/config, requisito, sandbox y status coinciden; para `passed`, existe `SandboxResult` terminal verificable y evidencia de ejecución del check sobre ese hash. Un `error` anterior al arranque omite `sandbox_request_id`, `started_at` y `exit_code`; `finished_at` es tiempo de observación. `SUCCEEDED` no sustituye la interpretación del validador. No se acepta `passed` si falta evidencia o si falla su persistencia.

Los logs son bytes UTF-8 ya redactados por una política versionada de B antes de `save`; el proceso supervisor impide que una salida cruda se persista o registre. Si la redacción falla o no puede verificar ausencia de secreto conocido, descartar salida y devolver `EVIDENCE_ERROR`; ningún sistema genérico garantiza detectar todos los secretos, por eso no se inyectan credenciales al sandbox. El registro solo contiene argv sanitizado del catálogo; no guarda código ni secretos. `redacted_log_sha256 = SHA256(redacted_log)`; el log vacío es válido. El almacén asigna referencia opaca e ID y calcula `record_sha256` sobre JSON canónico del registro completo excluyendo solo `record_sha256`. Guarda registro y log atómicamente; `get` recalcula ambos hashes y verifica relaciones. Los hashes detectan alteraciones, no sustituyen autorización ni prueban autenticidad por sí solos.

**JSON canónico:** UTF-8 sin BOM, sin espacios; claves ordenadas por bytes UTF-8 tras NFC Unicode 15.0.0; enteros decimales sin ceros iniciales, booleanos JSON, sin floats ni null; listas ordenadas solo donde el modelo dice `set`, argv conserva orden. En strings, el carácter U+0022 se representa con bytes hex `5c22`, U+005C con `5c5c`, y U+0000–001F con seis bytes ASCII `5c753030` más dos dígitos hex minúsculos; el resto Unicode válido va en UTF-8 directo, incluido `/`. Rechazar surrogates y claves duplicadas/colisiones NFC. El hash nunca incluye su propio campo. Este mismo JSON se usa para snapshots, política, catálogo y solicitudes; campos desconocidos se rechazan.

Pruebas: error previo sin tiempos inválidos; log vacío; alteración de registro/log; referencias cruzadas, `passed` sin resultado o con hash distinto; fallo de redacción con secreto sintético, acceso cruzado, recuperación tras fallo de commit y concurrencia idempotente.

## 9. Idempotencia, concurrencia y errores

Cada puerto mutador recibe `ctx` y `idempotency_key: UUID`; ámbito `(project_id, operation, key)`, no `principal_id`, para permitir recuperación autorizada por otro operador del mismo proyecto. El almacén exige autorización antes de consultar/crear la clave. `request_hash` es SHA-256 de JSON canónico §8 de todos los argumentos lógicos de la operación salvo `ctx` y `idempotency_key`; para `put`, argumentos son `{kind, sha256, size_bytes}` calculados de bytes validados; para `save`, `{write_request, redacted_log_sha256}` calculado del log; para `start`, `SandboxRequest` sin su clave; para `cancel`, `{handle_id}`. `assessment` usa snapshots y phase; su puerto admite la misma clave como parámetro final obligatorio. Diferente solicitud con la misma clave → `IDEMPOTENCY_CONFLICT`.

Se registra atómicamente una reserva durable de clave y hash antes del efecto; transiciones `IN_PROGRESS → COMMITTED | INDETERMINATE`. Solicitudes concurrentes iguales esperan o reciben `IN_PROGRESS` y consultan con la misma clave; una vez confirmada retornan el mismo ID/handle/resultado, no crean otro. Tras caída, el adaptador recupera por la reserva y el ID del efecto; si no puede determinarlo, conserva `INDETERMINATE`, bloquea y no relanza. Se retienen clave y resultado al menos el máximo de retención del recurso y política de auditoría; tras expirar el resultado se conserva una tumba permanente por ámbito/clave que impide reutilizarla y responde `IDEMPOTENCY_EXPIRED`. Nueva generación, política o intento requiere clave nueva; reintento de la misma operación conserva clave.

Errores sanitizados: `INVALID_REQUEST`, `UNSUPPORTED_VERSION`, `FORBIDDEN`, `NOT_FOUND`, `LIMIT_EXCEEDED`, `INTEGRITY_ERROR`, `STORE_UNAVAILABLE`, `POLICY_INVALID`, `POLICY_CONFLICT`, `CHECK_UNAVAILABLE`, `SANDBOX_UNAVAILABLE`, `EVIDENCE_ERROR`, `IDEMPOTENCY_CONFLICT`, `IDEMPOTENCY_EXPIRED`, `IN_PROGRESS`, `INDETERMINATE`, `TIMED_OUT`, `CANCELLED`, `INTERNAL_ERROR`. No incluyen contenido, claves, rutas sensibles, respuesta cruda o trazas. Ejemplo: dos `put` simultáneos con igual clave y bytes reciben la misma `ArtifactRef`; bytes diferentes con igual clave reciben conflicto. Pruebas: caídas antes/después de reserva y commit, requests paralelas, revocación antes de replay, conflicto y estado indeterminado.

## 10. Migración y límites de compatibilidad

`Generator.generate`, `Validator.validate`, `EvidenceStore.save`, payload y estados v1 no cambian. Tras acuerdo A/B y modificación de `CONTRACTS.md` mediante PR humano, se agregan puertos v2 nuevos, con activación explícita por proyecto y adaptadores independientes. Un puente v1 puede devolver `skipped`/`error` para artefactos v2, pero no traducir `passed` v1 a `passed` de un hash no verificado. No se usa introspección ni fallback silencioso. El wrapper que actualmente devuelve `skipped` solo se retira al disponer de almacén, RiskAnalyzer, validator, evidencia y sandbox reales que superen pruebas de contrato y aislamiento. Faltantes → `BLOCKED`; no hay Sandbox simulado que se presente como real.

Despliegue propuesto: (1) acordar y aprobar contrato; (2) A/B implementan modelos y vectores compartidos sin tocar v1; (3) integrar puertos en monolito con flag desactivado; (4) ejecutar pruebas de contrato con dobles y pruebas reales de aislamiento en entorno controlado; (5) humano habilita por proyecto tras revisar evidencia. Reversión desactiva el flag; no borra evidencia ni reinterpreta datos v2 como v1. Compatibilidad y efectividad no se consideran verificadas hasta ejecutar esas pruebas.

## 11. Pruebas de aceptación y ejemplos mínimos

1. Canonicalización: vector de §2 con hash exacto; NFC/casefold Unicode 15.0.0, colisión de carpetas, tipo/symlink/hardlink, mutación de captura, límites, truncamiento y orden. Verificar salida idéntica en dos implementaciones independientes.
2. Riesgos: ejemplo §4 y fronteras de bandas, reordenado de listas, snapshots/hashes, riesgos desconocidos, post monótono, política sin baseline y catálogo conflictivo.
3. Integridad: alteración en store, materialización y antes de ejecución; reemplazo de archivos, enlaces, escritura sobre entrada, evidencia ligada a hash anterior; ninguno puede producir `passed`.
4. Validación: todos los estados y precedencias §5, checks adicionales/ausentes/duplicados, `passed` sin evidencia, cancelación sin confirmación y retry con nuevo hash; verificar estados externos v1.
5. Sandbox: snapshots y terminales, límites, tiempo monotónico, carreras cancelación/finalización, fallo de terminación con cuarentena e idempotencia. Dobles verifican protocolo; aislamiento exige pruebas reales §7.
6. Evidencia/autorización: persistencia atómica, hashes de log y registro, error sin arranque, `passed` falsificado, credenciales sintéticas en salida, aislamiento entre proyectos, revocación y caídas concurrentes en §9.
7. La aceptación para implementación exige acuerdo A/B de este texto y vectores; la aceptación operativa exige resultados reales de pruebas de integración y aislamiento. No inferir certificación ISO.

## 12. Matriz de observaciones y decisiones humanas

| Observación de revisión disponible | Resolución propuesta | Secciones |
|---|---|---|
| Riesgos y derivación no reproducibles | puerto pre/post, snapshots, catálogo, algoritmo y ejemplo | 4, 11 |
| Conflicto de orden con estados v1 | pre en `RISK_ASSESSMENT`, post interno en `GENERATING` | 5, 10 |
| Unicode, metadatos y vectores insuficientes | Unicode 15.0.0, captura por descriptor y vector de bytes/hash | 2, 11 |
| Carrera entre hash y ejecución | materialización verificada y entrada inmutable de solo lectura | 3, 7 |
| Registro circular y error sin arranque | `EvidenceWriteRequest` separado de `EvidenceRecord`, campos condicionales | 8 |
| Proyecto e idempotencia implícitos | `AuthContext`, permisos, ámbito y reserva durable | 1, 9 |
| Sandbox no terminal/terminal mezclados | `SandboxSnapshot` separado de `SandboxResult`, espera/cancelación | 6 |
| Resultados mixtos sin precedencia | tabla total, `error`/`skipped` antes de `failed` | 5 |
| Herramientas y entorno no confiables | catálogo fijado, rutas, variables, cwd y prohibición de descubrimiento | 7 |
| Dobles confundibles con aislamiento | pruebas de protocolo separadas de pruebas reales | 6, 7, 11 |

Estas filas describen cómo el texto aborda las observaciones; no son una aprobación del Equipo B ni una prueba de implementación. Decisiones que requieren autorización o aceptación humana: (1) acuerdo técnico A/B y aprobación del contrato antes de modificar `CONTRACTS.md`; (2) responsables del proyecto aprueban política/catálogo concretos, controles aplicables y aceptación de riesgos residuales; (3) responsables de infraestructura eligen y autorizan backend de sandbox/imagen y evalúan pruebas reales de su plataforma antes de activar la capacidad; (4) responsables de datos fijan retención y eliminación de artefactos/evidencia conforme al proyecto; (5) humano crea, revisa y fusiona el PR de contrato conforme a git-governance. Los límites numéricos del MVP propuestos en §2 y §6 entran en la revisión técnica conjunta; no representan garantías ya probadas.
