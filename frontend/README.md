# BuildSec dashboard

Interfaz independiente para la API HTTP v1 del monolito. No ejecuta el código generado ni implementa un sandbox.

```sh
cd frontend
npm ci
npm run dev
```

El servidor de desarrollo de Vite reenvía `/executions` a `http://127.0.0.1:8000`. Es necesario iniciar por separado una instancia del servicio HTTP existente en esa dirección y suministrar sus adaptadores; el repositorio no arranca ese servidor automáticamente. Para otra distribución, servir el frontend y la API bajo el mismo origen o configurar un proxy inverso para `/executions`. No incluir credenciales en el frontend.

El formulario envía `goal`, `requiredChecks`, `workspace` y `revision` a `POST /executions` con `Prefer: respond-async`. Ante `202` se comprueba `Location` y se consulta la ejecución y sus resultados cada dos segundos, sin peticiones superpuestas. El polling se detiene al alcanzar un estado terminal, al cambiar de ejecución, al entrar en modo demo o al abandonar la vista; detenerlo no cancela la ejecución del servidor. Si falla una consulta, se puede reintentar buscando el ID.

El historial procede de `GET /executions` y es volátil: se pierde al reiniciar el proceso del backend. `GET /executions/{id}/results` proporciona los estados de validación y referencias de evidencia; estas referencias no acreditan que exista un archivo verificado. Un `skipped` nunca cuenta como aprobado. La API no ofrece recuperación del código generado ni contenido de evidencias. El modo demo está identificado y no realiza solicitudes a la API.

Comprobaciones: `npm run lint`, `npm run build` y `npm test`.
