/**
 * Headless verification script using Chrome CDP + Node 22 built-in WebSocket.
 * Runs the full "Analyse dataset" query flow and checks every stage.
 */

import { spawn } from 'child_process'
import { execSync } from 'child_process'
import http from 'http'

const CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
const APP_URL = 'http://localhost:5173'
const DEBUG_PORT = 9223   // avoid conflict with any existing Chrome

const sleep = (ms) => new Promise(r => setTimeout(r, ms))

const results = []
function check(name, passed, detail = '') {
  results.push({ name, passed, detail })
  console.log(`  ${passed ? '✓' : '✗'} ${name}${detail ? ' — ' + detail : ''}`)
}

// ── Start Chrome headless ─────────────────────────────────────────────
const chrome = spawn(CHROME, [
  `--remote-debugging-port=${DEBUG_PORT}`,
  '--headless=new',
  '--no-sandbox',
  '--disable-gpu',
  '--disable-extensions',
  '--disable-dev-shm-usage',
  `--user-data-dir=/tmp/chrome-aml-verify`,
  '--window-size=1280,900',
], { stdio: 'pipe' })

chrome.stderr.on('data', () => {}) // suppress devtools output

// Wait for Chrome to be ready
async function waitForChrome() {
  for (let i = 0; i < 40; i++) {
    try {
      const json = await fetch(`http://localhost:${DEBUG_PORT}/json/version`)
      if (json.ok) return
    } catch { /* not ready yet */ }
    await sleep(250)
  }
  throw new Error('Chrome did not become ready')
}

// Get a page tab's WebSocket URL
async function getTabWsUrl() {
  for (let i = 0; i < 10; i++) {
    try {
      const res = await fetch(`http://localhost:${DEBUG_PORT}/json`)
      const tabs = await res.json()
      const page = tabs.find(t => t.type === 'page')
      if (page?.webSocketDebuggerUrl) return page.webSocketDebuggerUrl
    } catch { /* retry */ }
    await sleep(200)
  }
  throw new Error('No page tab found')
}

// Minimal CDP client using Node 22 built-in WebSocket
function makeCdp(wsUrl) {
  return new Promise((resolve) => {
    let msgId = 0
    const pending = new Map()
    const listeners = new Map()
    const ws = new WebSocket(wsUrl)

    ws.addEventListener('message', ({ data }) => {
      const msg = JSON.parse(data)
      if (msg.id !== undefined && pending.has(msg.id)) {
        const { res, rej } = pending.get(msg.id)
        pending.delete(msg.id)
        if (msg.error) rej(new Error(msg.error.message))
        else res(msg.result)
        return
      }
      if (msg.method) {
        const cbs = listeners.get(msg.method) ?? []
        cbs.forEach(cb => cb(msg.params))
      }
    })

    const client = {
      send: (method, params = {}) => new Promise((res, rej) => {
        const id = ++msgId
        pending.set(id, { res, rej })
        ws.send(JSON.stringify({ id, method, params }))
      }),
      on: (event, fn) => {
        const cbs = listeners.get(event) ?? []
        cbs.push(fn)
        listeners.set(event, cbs)
      },
      close: () => ws.close(),
    }

    ws.addEventListener('open', () => resolve(client))
    ws.addEventListener('error', (e) => { throw new Error('CDP WS error: ' + e.message) })
  })
}

// Evaluate JS in browser, return value
async function eval_(client, expr, returnByValue = true) {
  const r = await client.send('Runtime.evaluate', { expression: expr, returnByValue, awaitPromise: true })
  return r?.result?.value
}

// Poll until condition is true (expr returns truthy) or timeout
async function waitFor(client, expr, timeoutMs = 60000, intervalMs = 500) {
  const start = Date.now()
  while (Date.now() - start < timeoutMs) {
    const v = await eval_(client, expr)
    if (v) return true
    await sleep(intervalMs)
  }
  return false
}

const consoleErrors = []

async function main() {
  console.log('\n═══════════════════════════════════════')
  console.log('  AML Agent — Full Stack Verification')
  console.log('═══════════════════════════════════════\n')

  // ── Step 0: TypeScript check ──────────────────────────────────────
  console.log('Pre-flight: TypeScript')
  try {
    execSync('npx tsc --noEmit 2>&1', { cwd: '/Users/kritikavaryani/hackathon_project/frontend', encoding: 'utf8' })
    check('TypeScript: zero errors', true)
  } catch (e) {
    check('TypeScript: zero errors', false, e.stdout?.trim()?.slice(0, 120))
  }

  // ── Step 1: Start Chrome and navigate ─────────────────────────────
  console.log('\nBrowser automation:')
  await waitForChrome()
  const wsUrl = await getTabWsUrl()
  const client = await makeCdp(wsUrl)

  // Collect console errors
  await client.send('Console.enable')
  await client.send('Runtime.enable')
  await client.send('Page.enable')
  client.on('Console.messageAdded', ({ message }) => {
    if (message.level === 'error') {
      consoleErrors.push(message.text)
    }
  })

  // Navigate to app
  await client.send('Page.navigate', { url: APP_URL })
  await sleep(2500)

  // Clear any previous error state
  await eval_(client, `localStorage.removeItem('__aml_errors')`)

  const title = await eval_(client, `document.title`)
  check('App loaded', typeof title === 'string' && title.includes('AML'), title)

  const inputPresent = await eval_(client, `!!document.querySelector('textarea')`)
  check('Query Console rendered', inputPresent === true)

  // ── Step 2: Submit query ──────────────────────────────────────────
  // Set textarea value
  await eval_(client, `
    const ta = document.querySelector('textarea');
    if (ta) {
      const setter = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, 'value')?.set;
      setter?.call(ta, 'Analyse this dataset for suspicious activity');
      ta.dispatchEvent(new Event('input', { bubbles: true }));
    }
  `)
  await sleep(200)

  // Click Run Query button
  const btnClicked = await eval_(client, `
    const btn = [...document.querySelectorAll('button')].find(b => b.textContent.trim().includes('Run Query'));
    if (btn && !btn.disabled) { btn.click(); return true; }
    return false;
  `)
  check('Query submitted', btnClicked === true)
  if (!btnClicked) {
    // Try Enter key on textarea
    await client.send('Input.dispatchKeyEvent', { type: 'keyDown', key: 'Enter', code: 'Enter', windowsVirtualKeyCode: 13 })
  }

  // ── Step 3: Plan Visualizer ───────────────────────────────────────
  const planShown = await waitFor(client,
    `document.body.innerText.includes('Execution Pipeline') || document.body.innerText.includes('Building execution') || document.body.innerText.includes('Intent Parsed')`,
    15000
  )
  check('Plan Visualizer shown', planShown)

  // ── Step 4: Results Dashboard ─────────────────────────────────────
  // Backend may be slow — give it up to 90s
  const resultsShown = await waitFor(client,
    `document.body.innerText.includes('txns scanned') || document.body.innerText.includes('Flagged Entities')`,
    90000
  )

  if (!resultsShown) {
    // Capture what IS on screen
    const bodyText = await eval_(client, `document.body.innerText.slice(0, 500)`)
    const hasErrorBoundary = await eval_(client, `document.body.innerText.includes('Something went wrong')`)
    check('Results Dashboard rendered', false, `Screen shows: "${bodyText?.slice(0, 100)}"`)
    if (hasErrorBoundary) {
      const alertText = await eval_(client, `document.querySelector('[role="alert"]')?.innerText ?? ''`)
      check('No ErrorBoundary', false, alertText?.slice(0, 200))
    }
    await report(client)
    return
  }
  check('Results Dashboard rendered', true)

  // ── Step 5: KPI tiles ─────────────────────────────────────────────
  const kpiOk = await eval_(client, `document.body.innerText.includes('txns scanned')`)
  check('KPI tiles rendered', kpiOk === true)

  const tableOk = await eval_(client, `document.body.innerText.includes('Flagged Entities')`)
  check('Flagged Entities table rendered', tableOk === true)

  // ── Step 6: Charts ────────────────────────────────────────────────
  await sleep(3000) // allow Plotly/Recharts lazy load
  const chartsOk = await eval_(client,
    `document.querySelectorAll('canvas, svg.main-svg, [class*="recharts-wrapper"]').length > 0`
  )
  check('Risk charts rendered', chartsOk === true)

  // ── Step 7: Transaction Network ───────────────────────────────────
  const networkOk = await eval_(client,
    `document.body.innerText.includes('Entity Risk Network') || document.body.innerText.includes('nodes ·')`
  )
  check('Transaction Network rendered', networkOk === true)

  // ── Step 8: No ErrorBoundary visible ─────────────────────────────
  const noBoundary = await eval_(client, `!document.body.innerText.includes('Something went wrong')`)
  check('No ErrorBoundary shown', noBoundary === true)

  // ── Step 9: JSON Inspector ────────────────────────────────────────
  // The JSON toggle is only active on plan/results view
  const jsonBtnClicked = await eval_(client, `
    const btn = [...document.querySelectorAll('button')].find(b =>
      (b.getAttribute('aria-label') || '').toLowerCase().includes('json') ||
      b.textContent.trim() === 'JSON'
    );
    if (btn && !btn.disabled) { btn.click(); return true; }
    return false;
  `)
  await sleep(2000)
  const inspectorOpen = await eval_(client,
    `document.body.innerText.includes('Raw JSON Inspector') || document.body.innerText.includes('ExecutionReport') || document.body.innerText.includes('execution_plan')`
  )
  check('JSON Inspector opened', inspectorOpen === true,
    jsonBtnClicked ? '' : '(JSON button not found or disabled)')

  await report(client)
}

async function report(client) {
  // Collect stored errors
  const stored = await eval_(client, `
    (() => {
      try { return JSON.parse(localStorage.getItem('__aml_errors') ?? '[]') }
      catch { return [] }
    })()
  `)
  const hasStoredErrors = Array.isArray(stored) && stored.length > 0
  check('No captured browser errors', !hasStoredErrors,
    hasStoredErrors ? JSON.stringify(stored[0]).slice(0, 200) : '')

  if (consoleErrors.length > 0) {
    console.log('\nConsole errors collected:')
    consoleErrors.forEach((e, i) => console.log(`  [${i+1}] ${e.slice(0, 300)}`))
  } else {
    console.log('\nNo console errors.')
  }

  console.log('\n═══════════════════════════════════════')
  const passed = results.filter(r => r.passed).length
  const failed = results.filter(r => !r.passed)
  console.log(`  PASSED: ${passed}/${results.length}`)
  if (failed.length > 0) {
    console.log(`  FAILED: ${failed.length}`)
    failed.forEach(f => console.log(`    ✗ ${f.name}${f.detail ? ': ' + f.detail : ''}`))
  }
  console.log('═══════════════════════════════════════\n')

  client.close()
  chrome.kill()
  process.exit(failed.length > 0 ? 1 : 0)
}

main().catch(async (e) => {
  console.error('Fatal verification error:', e.message)
  chrome.kill()
  process.exit(1)
})
