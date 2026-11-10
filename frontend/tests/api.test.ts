import { afterEach, describe, expect, it, vi } from 'vitest'
import { executionApi } from '../src/api'

describe('execution API v1', () => {
  afterEach(() => vi.unstubAllGlobals())
  it('sends the existing create payload to POST /executions', async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ id: 'run-1', state: 'BLOCKED' }) })
    vi.stubGlobal('fetch', fetchMock)
    const input = { goal: 'API', requiredChecks: ['F-01'], workspace: 'workspace', revision: 'HEAD' }
    expect(await executionApi.create(input)).toEqual({ id: 'run-1', state: 'BLOCKED' })
    expect(fetchMock).toHaveBeenCalledWith('/executions', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(input) })
  })
  it('encodes the ID and exposes HTTP errors', async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: false, status: 404 })
    vi.stubGlobal('fetch', fetchMock)
    await expect(executionApi.get('run/a')).rejects.toThrow('HTTP 404')
    expect(fetchMock).toHaveBeenCalledWith('/executions/run%2Fa', undefined)
  })
})
