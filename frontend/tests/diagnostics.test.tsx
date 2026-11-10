import { describe, expect, it } from 'vitest'
import { renderToStaticMarkup } from 'react-dom/server'
import { BlockedDiagnostic } from '../src/App'
import { blockedMessage } from '../src/diagnostics'

describe('blocked diagnostics', () => {
  it('renders a safe authentication explanation', () => {
    const html = renderToStaticMarkup(<BlockedDiagnostic error="GenerationAuthenticationError: adapter error" />)
    expect(html).toContain('autenticar')
    expect(html).toContain('role="alert"')
  })
  it('classifies timeouts and limits and hides unknown details', () => {
    expect(blockedMessage('timeout')).toContain('tiempo')
    expect(blockedMessage('GenerationRateLimitError: adapter error')).toContain('limitó')
    expect(blockedMessage('secret provider detail')).not.toContain('secret provider detail')
  })
})
