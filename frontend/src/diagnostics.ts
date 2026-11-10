// Only recognize backend-owned categories; never render arbitrary provider text.
export function blockedMessage(error: string | null): string {
  if (error === 'GenerationAuthenticationError: adapter error') return 'No fue posible autenticar con el proveedor de IA. Revisa las credenciales del backend.'
  if (error === 'GenerationTimeoutError: adapter error' || error === 'timeout') return 'La ejecución agotó el tiempo disponible. Inténtalo de nuevo.'
  if (error === 'GenerationRateLimitError: adapter error') return 'El proveedor limitó las solicitudes. Espera y vuelve a intentarlo.'
  if (error === 'AdapterCapacityError: adapter error') return 'La capacidad de ejecución está ocupada. Espera a que terminen los trabajos anteriores o reinicia el backend.'
  if (error === 'GenerationAPIError: adapter error' || error === 'GenerationError: adapter error') return 'El proveedor de IA no pudo completar la solicitud. Revisa su disponibilidad.'
  return 'La ejecución se bloqueó. Revisa la configuración y los registros sanitizados del backend.'
}
