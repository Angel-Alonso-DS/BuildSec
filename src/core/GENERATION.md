# Composición de generación

`AppConfig.from_env()` lee `OPENAI_MODEL` (obligatorio), `BUILDSYS_MAX_ATTEMPTS` (2), `BUILDSYS_EXECUTION_TIMEOUT` (30 segundos), `BUILDSYS_OPENAI_TIMEOUT` (20 segundos) y `BUILDSYS_MAX_OUTPUT_TOKENS` (2048). El timeout del proveedor no puede superar el timeout de ejecución. El cliente oficial desactiva sus reintentos implícitos; el orquestador conserva su límite de intentos de validación.

`build_goal_service` recibe explícitamente `validator`, `evidence_store` y `memory_store`; opcionalmente recibe un cliente simulado. No pasa credenciales a estos puertos. El resultado de generación es texto inerte, entregado al almacén de evidencia para cada resultado de validación; su persistencia depende de ese adaptador.

El contrato actual del validador no admite el artefacto de generación. Por ello la composición mantiene el validador inactivo y registra los checks como `skipped`: la ejecución termina `FAILED` al agotarse los intentos. No conectar un validador a código generado hasta disponer de un traspaso de artefactos y un sandbox aislado, sin red ni credenciales. El timeout del orquestador no cancela hilos que siguen ejecutándose; el timeout del cliente limita la solicitud al proveedor, pero no es un mecanismo de aislamiento.
