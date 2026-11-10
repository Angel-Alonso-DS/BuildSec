import { afterEach, describe, expect, it, vi } from 'vitest'
import { ApiError, executionApi } from '../src/api'

const input = { goal: 'API', requiredChecks: ['F-01'], workspace: 'workspace', revision: 'HEAD' }
function response(status: number, body: unknown, location: string | null = null) {
  return { ok: status >= 200 && status < 300, status, headers: { get: () => location }, json: async () => body }
}
describe('execution API v1', () => {
  afterEach(() => vi.unstubAllGlobals())
  it('requests async creation and checks the 202 Location', async () => {
    const fetchMock = vi.fn().mockResolvedValue(response(202, { id: 'run-1', state: 'CREATED' }, '/executions/run-1'))
    vi.stubGlobal('fetch', fetchMock)
    expect((await executionApi.create(input)).id).toBe('run-1')
    expect(fetchMock).toHaveBeenCalledWith('/executions', { method: 'POST', headers: { 'Content-Type': 'application/json', Prefer: 'respond-async' }, body: JSON.stringify(input), signal: undefined })
    fetchMock.mockResolvedValue(response(202, { id: 'run-1' }, 'https://other.example/'))
    await expect(executionApi.create(input)).rejects.toThrow('referencia de ejecución inválida')
  })
  it.each([400, 404, 503])('reports HTTP %i', async status => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response(status, {})))
    await expect(executionApi.create(input)).rejects.toMatchObject({ status, name: 'Error' })
    await expect(executionApi.create(input)).rejects.toBeInstanceOf(ApiError)
  })
  it('uses only the list, detail and results endpoints', async () => {
    const fetchMock = vi.fn().mockResolvedValueOnce(response(200, { executions: [{ id: 'a' }] })).mockResolvedValueOnce(response(200, { id: 'a/b' })).mockResolvedValueOnce(response(200, { executionId: 'a/b', evidence: [{ id: 'ev-1' }], validation: [{ status: 'skipped' }] }))
    vi.stubGlobal('fetch', fetchMock)
    expect(await executionApi.list()).toEqual([{ id: 'a' }])
    await executionApi.get('a/b')
    expect((await executionApi.results('a/b')).validation[0].status).toBe('skipped')
    expect(fetchMock.mock.calls.map(call => call[0])).toEqual(['/executions', '/executions/a%2Fb', '/executions/a%2Fb/results'])
  })
})
