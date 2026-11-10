import type { Execution } from './api'

export const demoExecution: Execution = {
  id: 'demo-7e42a1', goal: { description: 'API REST para gestionar tareas con autenticación y un endpoint de salud.', required_checks: ['F-01', 'S-01'] }, state: 'COMPLETED', attempts: 1,
  history: ['CREATED', 'PLANNING', 'RISK_ASSESSMENT', 'GENERATING', 'VALIDATING', 'LEARNING', 'COMPLETED'], error: null,
  validation: [{ requirement_id: 'F-01', status: 'passed', tool: 'pytest (demo)', exit_code: 0, evidence_id: 'demo-ev-01' }, { requirement_id: 'S-01', status: 'passed', tool: 'security check (demo)', exit_code: 0, evidence_id: 'demo-ev-02' }],
}
export const demoCode = `from fastapi import FastAPI\n\napp = FastAPI(title="Tasks API")\n\n@app.get("/health")\ndef health():\n    return {"status": "ok"}\n\n# Ejemplo ilustrativo; no ejecutado por BuildSec.`
