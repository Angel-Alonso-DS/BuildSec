export type ExecutionState = 'CREATED' | 'PLANNING' | 'RISK_ASSESSMENT' | 'GENERATING' | 'VALIDATING' | 'LEARNING' | 'COMPLETED' | 'FAILED' | 'BLOCKED' | 'CANCELLED'
export type CheckStatus = 'passed' | 'failed' | 'skipped' | 'error'
export interface ValidationResult { requirement_id: string; status: CheckStatus; tool: string; exit_code: number | null; evidence_id: string | null }
export interface Execution { id: string; goal: { description: string; required_checks: string[] }; state: ExecutionState; attempts: number; validation: ValidationResult[]; history: ExecutionState[]; error: string | null }
export interface ExecutionResults { executionId: string; state: ExecutionState; validation: ValidationResult[]; artifacts: unknown[]; evidence: { id: string }[] }
export interface CreateExecution { goal: string; requiredChecks: string[]; workspace: string; revision: string }
export const terminal = new Set<ExecutionState>(['COMPLETED', 'FAILED', 'BLOCKED', 'CANCELLED'])

export class ApiError extends Error {
  constructor(public status: number) {
    super(({ 400: 'Solicitud inválida (HTTP 400). Revisa los campos.', 404: 'Ejecución no encontrada (HTTP 404).', 503: 'Capacidad de ejecución no disponible (HTTP 503). Inténtalo más tarde.' } as Record<number, string>)[status] ?? `La API respondió con HTTP ${status}.`)
  }
}
async function json<T>(response: Response): Promise<T> {
  if (!response.ok) throw new ApiError(response.status)
  return response.json() as Promise<T>
}
const pathFor = (id: string) => `/executions/${encodeURIComponent(id)}`

export const executionApi = {
  async create(input: CreateExecution, signal?: AbortSignal): Promise<Execution> {
    const response = await fetch('/executions', { method: 'POST', headers: { 'Content-Type': 'application/json', Prefer: 'respond-async' }, body: JSON.stringify(input), signal })
    if (!response.ok) throw new ApiError(response.status)
    if (response.status !== 202) throw new Error(`Respuesta inesperada de la API: HTTP ${response.status}.`)
    const execution = await json<Execution>(response)
    if (response.headers.get('Location') !== pathFor(execution.id)) throw new Error('La API devolvió una referencia de ejecución inválida.')
    return execution
  },
  get: async (id: string, signal?: AbortSignal) => json<Execution>(await fetch(pathFor(id), { signal })),
  list: async (signal?: AbortSignal) => (await json<{ executions: Execution[] }>(await fetch('/executions', { signal }))).executions,
  results: async (id: string, signal?: AbortSignal) => json<ExecutionResults>(await fetch(`${pathFor(id)}/results`, { signal })),
}
