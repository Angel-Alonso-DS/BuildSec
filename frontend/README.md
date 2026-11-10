# BuildSec dashboard

Interfaz independiente para la API HTTP v1 del monolito. No ejecuta el código generado ni implementa un sandbox.

```sh
cd frontend
npm ci
npm run dev
```

El servidor de desarrollo de Vite reenvía `/executions` a `http://127.0.0.1:8000`. Es necesario iniciar por separado una instancia del servicio HTTP existente en esa dirección y suministrar sus adaptadores; el repositorio no arranca ese servidor automáticamente. Para otra distribución, servir el frontend y la API bajo el mismo origen o configurar un proxy inverso para `/executions`. No incluir credenciales en el frontend.

El formulario envía `goal`, `requiredChecks`, `workspace` y `revision` a `POST /executions`. La respuesta se obtiene al terminar la llamada síncrona; se puede consultar por ID mediante `GET /executions/{id}`. La vista del pipeline usa el historial devuelto, no un progreso en tiempo real. La API no ofrece listado histórico, recuperación del código generado ni contenido de evidencias: el dashboard muestra únicamente la ejecución seleccionada y referencias de evidencia disponibles. El modo demo está identificado y no realiza solicitudes a la API.

Comprobaciones: `npm run lint`, `npm run build` y `npm test`.
