import { afterEach, describe, expect, it, vi } from 'vitest'
import { executionApi, type Execution, type ExecutionResults, type ExecutionState } from '../src/api'
import { pollExecution } from '../src/polling'

const snapshot = (state: ExecutionState) => ({ id: 'run-1', state } as Execution)
const result = { executionId: 'run-1', state: 'GENERATING', validation: [], evidence: [], artifacts: [] } as ExecutionResults
describe('execution polling', () => {
  afterEach(() => { vi.useRealTimers(); vi.restoreAllMocks() })
  it.each<ExecutionState>(['COMPLETED', 'FAILED', 'BLOCKED', 'CANCELLED'])('stops at %s', async state => {
    vi.useFakeTimers()
    const get = vi.spyOn(executionApi, 'get').mockResolvedValue(snapshot(state))
    vi.spyOn(executionApi, 'results').mockResolvedValue({ ...result, state })
    const onUpdate = vi.fn()
    const stop = pollExecution('run-1', onUpdate, vi.fn(), 2000)
    await vi.advanceTimersByTimeAsync(10000)
    expect(onUpdate).toHaveBeenCalledOnce()
    expect(get).toHaveBeenCalledOnce()
    stop()
  })
  it('retries mismatched states before showing a terminal result', async () => {
    const failed = { ...result, state: 'FAILED' as const, validation: [{ requirement_id: 'F-01', status: 'skipped' as const, tool: '', exit_code: null, evidence_id: null }] }
    vi.spyOn(executionApi, 'get').mockResolvedValueOnce(snapshot('GENERATING')).mockResolvedValueOnce(snapshot('FAILED'))
    vi.spyOn(executionApi, 'results').mockResolvedValue(failed)
    const onUpdate = vi.fn()
    const stop = pollExecution('run-1', onUpdate, vi.fn())
    await vi.waitFor(() => expect(onUpdate).toHaveBeenCalledOnce())
    expect(onUpdate).toHaveBeenCalledWith(snapshot('FAILED'), failed)
    stop()
  })
  it('stops after a bounded number of inconsistent pairs', async () => {
    const get = vi.spyOn(executionApi, 'get').mockResolvedValue(snapshot('GENERATING'))
    vi.spyOn(executionApi, 'results').mockResolvedValue({ ...result, state: 'FAILED' })
    const onUpdate = vi.fn(), onError = vi.fn()
    const stop = pollExecution('run-1', onUpdate, onError)
    await vi.waitFor(() => expect(onError).toHaveBeenCalledOnce())
    expect(get).toHaveBeenCalledTimes(2)
    expect(onUpdate).not.toHaveBeenCalled()
    stop()
  })
  it('aborts a retry and ignores its late response', async () => {
    let resolve!: (value: Execution) => void
    const get = vi.spyOn(executionApi, 'get').mockResolvedValueOnce(snapshot('GENERATING')).mockReturnValueOnce(new Promise(r => { resolve = r }))
    vi.spyOn(executionApi, 'results').mockResolvedValue({ ...result, state: 'FAILED' })
    const onUpdate = vi.fn(), onError = vi.fn()
    const stop = pollExecution('run-1', onUpdate, onError)
    await vi.waitFor(() => expect(get).toHaveBeenCalledTimes(2))
    stop()
    resolve(snapshot('FAILED'))
    await Promise.resolve(); await Promise.resolve()
    expect(onUpdate).not.toHaveBeenCalled()
    expect(onError).not.toHaveBeenCalled()
  })
  it('polls sequentially and stops when the view is abandoned', async () => {
    vi.useFakeTimers()
    const get = vi.spyOn(executionApi, 'get').mockResolvedValue(snapshot('GENERATING'))
    vi.spyOn(executionApi, 'results').mockResolvedValue(result)
    const stop = pollExecution('run-1', vi.fn(), vi.fn(), 2000)
    await vi.advanceTimersByTimeAsync(2100)
    expect(get).toHaveBeenCalledTimes(2)
    const signal = get.mock.calls[0][1]!
    stop()
    expect(signal.aborted).toBe(true)
    await vi.advanceTimersByTimeAsync(10000)
    expect(get).toHaveBeenCalledTimes(2)
  })
  it('ignores a late response after cleanup', async () => {
    let resolve!: (value: Execution) => void
    vi.spyOn(executionApi, 'get').mockReturnValue(new Promise(r => { resolve = r }))
    const results = vi.spyOn(executionApi, 'results').mockResolvedValue(result)
    const onUpdate = vi.fn()
    const stop = pollExecution('run-1', onUpdate, vi.fn())
    stop(); resolve(snapshot('COMPLETED'))
    await Promise.resolve(); await Promise.resolve()
    expect(onUpdate).not.toHaveBeenCalled()
    expect(results).not.toHaveBeenCalled()
  })
  it('does not overlap slow requests and stops on an error', async () => {
    vi.useFakeTimers()
    let reject!: (error: Error) => void
    const get = vi.spyOn(executionApi, 'get').mockReturnValue(new Promise((_, r) => { reject = r }))
    const onError = vi.fn()
    const stop = pollExecution('run-1', vi.fn(), onError, 2000)
    await vi.advanceTimersByTimeAsync(10000)
    expect(get).toHaveBeenCalledOnce()
    reject(new Error('HTTP 503'))
    await vi.advanceTimersByTimeAsync(10000)
    expect(onError).toHaveBeenCalledOnce()
    expect(get).toHaveBeenCalledOnce()
    stop()
  })
})
