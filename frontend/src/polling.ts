import { executionApi, terminal, type Execution, type ExecutionResults } from './api'

// Schedule the next request only after the previous pair finishes; cleanup aborts both.
export function pollExecution(id: string, onUpdate: (execution: Execution, results: ExecutionResults) => void, onError: (error: unknown) => void, interval = 2000): () => void {
  const controller = new AbortController()
  let timer: ReturnType<typeof setTimeout> | undefined
  async function poll() {
    try {
      for (let attempt = 0; attempt < 2; attempt++) {
        const execution = await executionApi.get(id, controller.signal)
        if (controller.signal.aborted) return
        const results = await executionApi.results(id, controller.signal)
        if (controller.signal.aborted) return
        if (execution.id !== id || results.executionId !== id) throw new Error('La API devolvió resultados de otra ejecución.')
        if (execution.state !== results.state) continue
        onUpdate(execution, results)
        if (!terminal.has(execution.state)) timer = setTimeout(poll, interval)
        return
      }
      throw new Error('No fue posible obtener un estado consistente. Consulta el ID para reintentar.')
    } catch (error) {
      if (!controller.signal.aborted) onError(error)
    }
  }
  void poll()
  return () => { controller.abort(); if (timer !== undefined) clearTimeout(timer) }
}
