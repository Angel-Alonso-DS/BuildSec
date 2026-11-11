# Dashboard de BuildSys (repositorio BuildSec)

Interfaz independiente para la API HTTP v1 del monolito. No ejecuta el código generado ni implementa un sandbox.

```sh
cd frontend
npm ci
npm run dev
```

El servidor de desarrollo de Vite reenvía `/executions` y `/runtime` a `http://127.0.0.1:8000`. Desde la raíz se pueden iniciar ambos servicios con `./scripts/init.sh` y `./scripts/run.sh demo`. Para otra distribución, servir frontend y API bajo el mismo origen o configurar un proxy inverso para ambas rutas. No incluir credenciales en el frontend.

El formulario envía `goal`, `requiredChecks`, `workspace` y `revision` a `POST /executions` con `Prefer: respond-async`. Ante `202` se comprueba `Location` y se consulta la ejecución y sus resultados cada dos segundos, sin peticiones superpuestas. El polling se detiene al alcanzar un estado terminal, al cambiar de ejecución, al entrar en modo demo o al abandonar la vista; detenerlo no cancela la ejecución del servidor. Si falla una consulta, se puede reintentar buscando el ID.

El historial procede de `GET /executions` y es volátil: se pierde al reiniciar el proceso del backend. `GET /executions/{id}/results` proporciona los estados de validación y referencias de evidencia; estas referencias no acreditan que exista un archivo verificado. Un `skipped` nunca cuenta como aprobado. La API no ofrece recuperación del código generado ni contenido de evidencias. El ejemplo local activado con «Probar demo» está identificado y no consulta la API; es distinto de una ejecución enviada a un backend en modo demo.

Comprobaciones: `npm run lint`, `npm run build` y `npm test`.

El indicador consulta `/runtime/info`: una conexión HTTP a un backend demo no implica generación OpenAI. OpenAI configurado tampoco garantiza que el proveedor acepte las credenciales. El botón de ejemplo local muestra datos simulados y no consulta la API. Para una prueba integral sin proveedor, ejecuta desde la raíz `.venv/bin/python scripts/smoke_demo.py`; usa procesos demo propios y puertos temporales.

En la auditoría npm del 10 de noviembre de 2026 se reportaron 13 vulnerabilidades en dependencias de desarrollo (10 moderadas, una alta y dos críticas); `npm audit --omit=dev` no reportó vulnerabilidades de producción. Las críticas afectan a Vitest y su dependencia transitiva tinypool; npm propone una actualización mayor de Vitest. No ejecutar la interfaz de Vitest ni exponer herramientas de desarrollo a redes no confiables. Revisar y actualizar dependencias con pruebas de compatibilidad antes de usarlas en otros entornos.
