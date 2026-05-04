import React from 'react'
import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { FrontendErrorBoundary } from '../app/FrontendErrorBoundary'
import {
  __resetErrorReportingForTests,
  installGlobalErrorReporting,
  reportFrontendError,
  reportHttpResponseError,
  reportNetworkError,
} from './errorReporting'

function reportCalls() {
  return vi.mocked(global.fetch).mock.calls.filter(([url]) => String(url).includes('/api/ops/frontend-error-logs'))
}

function reportBody(index = 0): Record<string, unknown> {
  const call = reportCalls()[index]
  return JSON.parse(String(call?.[1]?.body))
}

async function waitForReports(count: number): Promise<void> {
  await vi.waitFor(() => expect(reportCalls()).toHaveLength(count))
}

describe('frontend error reporting', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    sessionStorage.clear()
    __resetErrorReportingForTests()
    vi.mocked(global.fetch).mockResolvedValue(new Response(JSON.stringify({ ok: true }), { status: 201 }))
  })

  afterEach(() => {
    cleanup()
    __resetErrorReportingForTests()
  })

  it('reports HTTP 401, 500, and 503 failures with severity and safe excerpts', async () => {
    reportHttpResponseError({
      requestUrl: '/api/auth/me?code=123&email=alice@example.com',
      method: 'GET',
      response: new Response(JSON.stringify({ error: 'unauthorized', token: 'secret' }), {
        status: 401,
        statusText: 'Unauthorized',
        headers: { 'Content-Type': 'application/json' },
      }),
    })
    reportHttpResponseError({
      requestUrl: '/api/books/my',
      method: 'GET',
      response: new Response(JSON.stringify({ detail: 'server failed for bob@example.com' }), {
        status: 500,
        statusText: 'Server Error',
        headers: { 'Content-Type': 'application/json' },
      }),
    })
    reportHttpResponseError({
      requestUrl: '/api/ai/learner-profile',
      method: 'GET',
      response: new Response('service unavailable for ops@example.com', { status: 503 }),
    })

    await waitForReports(3)
    const bodies = [reportBody(0), reportBody(1), reportBody(2)]

    expect(bodies.map(body => body.status_code)).toEqual([401, 500, 503])
    expect(bodies.map(body => body.severity)).toEqual(['warning', 'error', 'error'])
    expect(String(bodies[0].request_url)).not.toContain('123')
    expect(String(bodies[0].request_url)).not.toContain('alice@example.com')
    expect(String(bodies[0].response_excerpt)).not.toContain('secret')
    expect(String(bodies[1].response_excerpt)).toContain('[redacted-email]')
    expect(String(bodies[2].response_excerpt)).toContain('[redacted-email]')
  })

  it('reports network exceptions and skips the logging endpoint itself', async () => {
    reportNetworkError({
      requestUrl: '/api/books/my?password=secret',
      method: 'GET',
      error: new TypeError('Failed to fetch for carol@example.com'),
    })
    reportNetworkError({
      requestUrl: '/api/ops/frontend-error-logs',
      method: 'POST',
      error: new TypeError('report failed'),
    })

    await waitForReports(1)
    const body = reportBody()

    expect(body.source).toBe('network')
    expect(body.severity).toBe('error')
    expect(String(body.message)).toContain('[redacted-email]')
    expect(String(body.request_url)).not.toContain('secret')
  })

  it('captures global error and unhandled rejection events', async () => {
    installGlobalErrorReporting(window)

    window.dispatchEvent(new ErrorEvent('error', {
      message: 'render failed for dana@example.com',
      filename: '/src/App.tsx?token=abc',
      error: new Error('render failed for dana@example.com'),
      lineno: 12,
      colno: 4,
    }))
    const rejection = new Event('unhandledrejection') as PromiseRejectionEvent
    Object.defineProperty(rejection, 'reason', { value: new Error('promise failed') })
    window.dispatchEvent(rejection)

    await waitForReports(2)

    expect(reportBody(0).source).toBe('window-error')
    expect(String(reportBody(0).message)).toContain('[redacted-email]')
    expect(String(reportBody(0).request_url)).not.toContain('abc')
    expect(reportBody(1).source).toBe('unhandledrejection')
  })

  it('captures React render errors through the boundary', async () => {
    const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
    const CrashingChild = () => {
      throw new Error('react render crash')
    }

    render(React.createElement(
      FrontendErrorBoundary,
      null,
      React.createElement(CrashingChild),
    ))

    await waitForReports(1)

    expect(screen.getByText('页面加载失败，请刷新重试')).toBeInTheDocument()
    expect(reportBody().source).toBe('react-error-boundary')
    expect(String(reportBody().component_stack)).toContain('CrashingChild')
    consoleErrorSpy.mockRestore()
  })

  it('redacts sensitive fields and deduplicates identical fingerprints for 60 seconds', async () => {
    const input = {
      source: 'manual' as const,
      severity: 'error' as const,
      requestUrl: '/api/auth/reset-password?token=abc&email=alice@example.com&safe=1',
      message: 'failed for alice@example.com',
      context: {
        password: 'secret',
        verificationCode: '123456',
        nested: { email: 'alice@example.com' },
      },
    }

    reportFrontendError(input)
    reportFrontendError(input)

    await waitForReports(1)
    const body = reportBody()
    const serialized = JSON.stringify(body)

    expect(serialized).not.toContain('abc')
    expect(serialized).not.toContain('alice@example.com')
    expect(serialized).not.toContain('secret')
    expect(serialized).not.toContain('123456')
    expect(serialized).toContain('[redacted]')
  })
})
