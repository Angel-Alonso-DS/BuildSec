# API de ejecuciones v1

- `POST /executions` acepta `goal` (texto), `requiredChecks` (lista de IDs no vacía), `workspace` y `revision` (texto). Sin cabecera especial conserva el comportamiento existente: espera el resultado y responde `201`.
- Con `Prefer: respond-async`, el mismo POST responde `202`, la ejecución inicial `CREATED` y `Location: /executions/{id}`. Cuando la cola está llena responde `503`; una solicitud inválida responde `400`. La petición nunca ejecuta código generado por sí misma.
- `GET /executions` devuelve `{"executions": [...]}`; `GET /executions/{id}` devuelve la instantánea, o `404`.
- `GET /executions/{id}/results` devuelve `executionId`, `state`, `validation`, `artifacts` y `evidence`; ID inexistente responde `404`. `evidence` solo contiene IDs presentes en resultados v1 y `artifacts` está vacío mientras no exista un almacén/contrato integrado que suministre metadatos. Un check `skipped` no es `passed` ni indica éxito global.

Las ejecuciones y resultados son volátiles y se pierden al reiniciar; el listado no es paginado ni hay cancelación de ejecución. La opción asíncrona limita el número de trabajos en ejecución y pendientes dentro de este proceso; no ofrece persistencia, ni detiene un adaptador que siga activo tras timeout. El llamador debe consultar hasta un estado terminal y administrar la vida del servicio con `close()`. Las validaciones reales y el manejo seguro de artefactos siguen pendientes de los adaptadores correspondientes.
