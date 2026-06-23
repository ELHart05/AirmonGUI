import { describe, it, expect } from 'vitest'
import { escapeHtml, buildHtmlReport } from './report.js'

describe('escapeHtml', () => {
  it('escapes the five HTML entities', () => {
    expect(escapeHtml('<img src=x onerror="alert(1)">')).toBe(
      '&lt;img src=x onerror=&quot;alert(1)&quot;&gt;',
    )
    expect(escapeHtml("a&b'c")).toBe('a&amp;b&#39;c')
  })

  it('coerces nullish and numbers', () => {
    expect(escapeHtml(null)).toBe('')
    expect(escapeHtml(undefined)).toBe('')
    expect(escapeHtml(42)).toBe('42')
  })
})

describe('buildHtmlReport', () => {
  const hostileSsid = '<img src=x onerror=alert(1)>'
  const data = {
    config: {
      title: 'Audit',
      author: '"me"',
      scope: '',
      notes: '<script>bad()</script>',
    },
    generatedAt: '2026-06-23 10:00',
    networks: [
      { bssid: 'AA:BB:CC:DD:EE:FF', essid: hostileSsid, channel: '6', dbm: -40, privacy: 'WPA2', clientCount: 1 },
    ],
    summary: { interfaces: 1, networks: 1, clients: 0, captures: 0 },
    captureFiles: [{ filename: '<b>f</b>.cap', size_human: '1 KB' }],
    interfaces: [{ interface: 'wlan0', driver: 'iwlwifi', monitor_mode: true }],
  }

  it('escapes a hostile SSID so it cannot execute', () => {
    const html = buildHtmlReport(data)
    expect(html).not.toContain('<img src=x onerror')
    expect(html).toContain('&lt;img src=x onerror=alert(1)&gt;')
  })

  it('escapes report form fields', () => {
    const html = buildHtmlReport(data)
    expect(html).not.toContain('<script>bad()</script>')
    expect(html).toContain('&lt;script&gt;bad()&lt;/script&gt;')
  })

  it('escapes capture filenames', () => {
    const html = buildHtmlReport(data)
    expect(html).not.toContain('<b>f</b>.cap')
    expect(html).toContain('&lt;b&gt;f&lt;/b&gt;.cap')
  })

  it('includes a CSP that blocks inline script', () => {
    const html = buildHtmlReport(data)
    expect(html).toContain('Content-Security-Policy')
    expect(html).toContain("default-src 'none'")
  })

  it('keeps the hidden-ESSID fallback as trusted markup', () => {
    const html = buildHtmlReport({
      ...data,
      networks: [{ bssid: 'AA', essid: '', channel: '1', dbm: -1, privacy: 'OPN', clientCount: 0 }],
    })
    expect(html).toContain('<i>hidden</i>')
  })
})
