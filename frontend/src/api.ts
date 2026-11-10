export type ExecutionState = 'CREATED' | 'PLANNING' | 'RISK_ASSESSMENT' | 'GENERATING' | 'VALIDATING' | 'LEARNING' | 'COMPLETED' | 'FAILED' | 'BLOCKED' | 'CANCELLED'
export type CheckStatus = 'passed' | 'failed' | 'skipped' | 'error'
export interface ValidationResult { requirement_id: string; status: CheckStatus; tool: string; exit_code: number | null; evidence_id: string | null }
export interface Execution { id: string; goal: { description: string; required_checks: string[] }; state: ExecutionState; attempts: number; validation: ValidationResult[]; history: ExecutionState[]; error: string | null }
export interface CreateExecution { goal: string; requiredChecks: string[]; workspace: string; revision: string }

async function request(path: string, init?: RequestInit): Promise<Execution> {
  const response = await fetch(path, init)
  if (!response.ok) throw new Error(`La API respondió con HTTP ${response.status}.`)
  return response.json() as Promise<Execution>
}

export const executionApi = {
  create: (input: CreateExecution) => request('/executions', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(input) }),
  get: (id: string) => request(`/executions/${encodeURIComponent(id)}`),
}
