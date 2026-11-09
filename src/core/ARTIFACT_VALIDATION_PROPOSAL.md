# Propuesta para revisión conjunta: artefactos y validación

**Estado: propuesta, no contrato aprobado ni implementación.** Requiere revisión de los equipos A y B y un PR acordado para modificar `CONTRACTS.md`. Depende también de la integración en `dev` de `feature/generation-integration`.

## Situación actual

`Generator.generate` devuelve `GenerationResult`; el generador OpenAI actual devuelve texto inerte. `Validator.validate(workspace, required_checks)` no recibe ni identifica ese resultado. `EvidenceStore.save(result, revision, artifacts)` acepta artefactos sin un tipo común. El orquestador llama al validador solo con el workspace y guarda el resultado generado en evidencia después de validar. Por tanto, un `passed` del validador v1 no prueba que haya examinado el texto generado.

El Equipo B es responsable de los validadores de seguridad, evidencia, hashes, logs redactados y validación de autorización. No hay módulos `src/security/` ni `src/evidence/` en `origin/dev` ni una rama remota del Equipo B disponible al preparar esta propuesta. No se presupone un backend de almacenamiento o sandbox existente.

## Contrato propuesto

- `ArtifactRef`: `id` opaco no sensible, `kind` acordado (por ejemplo, `source-bundle`) y `sha256` hexadecimal de los bytes exactos inmutables. El algoritmo y la codificación/canonización de cada tipo deben fijarse antes de interoperar; un hash del texto no equivale al hash de un árbol materializado.
- Un puerto de almacén de artefactos conserva y recupera bytes por referencia. Al recuperar, comprueba el hash antes de entregar contenido al validador; ausencia, corrupción o acceso denegado producen `error`, nunca `passed`. La referencia no contiene credenciales, texto, rutas arbitrarias ni URL con credenciales.
- `Generator` mantiene su firma v1. Una capa del Equipo A normaliza el resultado del proveedor a bytes y conserva el artefacto, creando la referencia sin acoplar el validador a OpenAI.
- Añadir un puerto versionado separado: `ArtifactValidator.validate_artifact(artifact_ref, workspace, required_checks) -> list[ValidationResult]`. El validador obtiene los bytes mediante el almacén autorizado; ejecuta código únicamente en aislamiento real, sin red por defecto, credenciales ni socket del host. La integridad debe comprobarse sobre los mismos bytes usados por el check.
- Mantener `Validator.validate(workspace, required_checks)` sin cambio para consumidores v1. Un adaptador v1 que no pueda demostrar que validó exactamente el hash solicitado devuelve `skipped` o `error` para cada check requerido; jamás convierte un `passed` anterior en validación del artefacto.
- Los resultados usan exclusivamente `passed`, `failed`, `skipped` o `error`, y deben vincularse al identificador y hash validados mediante un contrato de trazabilidad acordado con B. `COMPLETED` requiere un resultado `passed` único para cada check obligatorio del mismo artefacto. Resultado ausente, duplicado, omitido, erróneo o ligado a otro hash falla cerrado.
- La evidencia debe vincular ejecución, requisito, referencia/hash exacto, revisión de código, herramienta, versión, comando, salida y logs redactados conforme a `CONTRACTS.md`. Los IDs de evidencia y de artefacto tienen funciones distintas; ninguna respuesta o log debe contener secretos o texto generado por defecto.

## Decisiones requeridas a A y B

1. Formato canónico de `kind`, bytes, codificación y hash, incluido el caso de múltiples archivos.
2. Propiedad, ciclo de vida, acceso y persistencia del almacén de artefactos; límites de tamaño y limpieza.
3. Forma exacta de vincular `ValidationResult` y `Evidence` con la referencia sin romper consumidores v1.
4. Interfaz y garantías verificables del sandbox real, así como clasificación de checks no disponibles y validaciones no aplicables.
5. Plan de migración del validador v1, tratamiento de reintentos y forma de evitar diferencias entre el artefacto validado y el publicado.

## Verificación propuesta tras el acuerdo

Pruebas unitarias e integración con dobles de almacén y validador: referencia estable, alteración de bytes, artefacto ausente, referencia equivocada, resultados duplicados o incompletos, cada estado y fallo cerrado de v1. Un doble nunca debe presentarse como sandbox. Las pruebas que ejecuten código generado requerirán un sandbox real independiente y están fuera de esta propuesta.
