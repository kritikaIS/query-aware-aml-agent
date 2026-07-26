/**
 * Focused verification — checks actual content of the running app.
 * The app starts on the Results Dashboard (because mock data seeded on load).
 * We verify all dashboard components are present, then open JSON Inspector.
 */

import { spawn } from 'child_process'
import { execSync } from 'child_process'

const CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
const APP_URL = 'http://localhost:5173'
const DEBUG_PORT = 9224

const sleep = (ms) => new Promise(r => setTimeout(r, ms))

const results = []
function check(name, passed, detail = '') {
  results.push({ name, passed, detail })
  console.log(`  ${passed ? '✓' : '✗'} ${name}${detail ? ' — ' + detail : ''}`)
}

const chrome = spawn(CHROME, [
  `--remote-debugging-port=${DEBUG_PORT}`,
  '--headless=new',
  '--no-sandbox',
  '--disable-gpu',
  '--disable-extensions',
  '--disable-dev-shm-usage',
  `--user-data-dir=/tmp/chrome-aml-v2`,
  '--window-size=1280,900',
], { stdio: 'pipe' })
chrome.stderr.on('data', () => {})

async function waitForChrome() {
  for (let i = 0; i < 40; i++) {
    try {
      const r = await fetch(`http://localhost:${DEBUG_PORT}/json/version`)
      if (r.ok) return
    } catch {}
    await sleep(250)
  }
  throw new Error('Chrome not ready')
}

async function getWsUrl() {
  for (let i = 0; i < 10; i++) {
    try {
      const r = await fetch(`http://localhost:${DEBUG_PORT}/json`)
      const tabs = await r.json()
      const page = tabs.find(t => t.type === 'page')
      if (page?.webSocketDebuggerUrl) return page.webSocketDebuggerUrl
    } catch {}
    await sleep(200)
  }
  throw new Error('No page tab')
}

function makeCdp(wsUrl) {
  return new Promise((res) => {
    let id = 0
    const pending = new Map()
    const listeners = new Map()
    const ws = new WebSocket(wsUrl)
    ws.addEventListener('message', ({ data }) => {
      const msg = JSON.parse(data)
      if (msg.id !== undefined && pending.has(msg.id)) {
        const { res, rej } = pending.get(msg.id)
        pending.delete(msg.id)
        msg.error ? rej(new Error(msg.error.message)) : res(msg.result)
        return
      }
      if (msg.method) {
        ;(listeners.get(msg.method) ?? []).forEach(cb => cb(msg.params))
      }
    })
    const client = {
      send: (method, params = {}) => new Promise((res, rej) => {
        const i = ++id
        pending.set(i, { res, rej })
        ws.send(JSON.stringify({ id: i, method, params }))
      }),
      on: (event, fn) => {
        const cbs = listeners.get(event) ?? []
        cbs.push(fn)
        listeners.set(event, cbs)
      },
      close: () => ws.close(),
    }
    ws.addEventListener('open', () => res(client))
  })
}

const ev = async (client, expr) => {
  const r = await client.send('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true })
  return r?.result?.value
}

const waitFor = async (client, expr, ms = 30000) => {
  const start = Date.now()
  while (Date.now() - start < ms) {
    if (await ev(client, expr)) return true
    await sleep(400)
  }
  return false
}

const consoleErrors = []

async function main() {
  console.log('\n═══════════════════════════════════════')
  console.log('  AML Agent — Full Stack Verification')
  console.log('═══════════════════════════════════════\n')

  // Pre-flight TypeScript check
  console.log('Pre-flight:')
  try {
    execSync('npx tsc --noEmit', { cwd: '/Users/kritikavaryani/hackathon_project/frontend', stdio: 'pipe' })
    check('TypeScript zero errors', true)
  } catch (e) {
    check('TypeScript zero errors', false, e.stdout?.toString()?.slice(0, 100))
    process.exit(1)
  }

  console.log('\nBrowser:')
  await waitForChrome()
  const client = await makeCdp(await getWsUrl())
  await client.send('Console.enable')
  await client.send('Runtime.enable')
  await client.send('Page.enable')

  client.on('Console.messageAdded', ({ message }) => {
    if (message.level === 'error') consoleErrors.push(message.text)
  })

  // Clear storage and navigate
  await client.send('Page.navigate', { url: APP_URL })
  await sleep(3000)
  await ev(client, `localStorage.removeItem('__aml_errors')`)
  await ev(client, `localStorage.removeItem('__aml_query_done')`)

  const title = await ev(client, `document.title`)
  check('App loads', title?.includes('AML'), title)

  // Dump body text for diagnosis
  const bodyText = await ev(client, `document.body.innerText.slice(0, 800)`)
  console.log('\n  [Body snapshot]:', bodyText?.replace(/\n/g, ' / ').slice(0, 200))

  // Check current view
  const isOnQuery  = await ev(client, `document.body.innerText.includes('Ask the agent')`)
  const isOnResult = await ev(client, `document.body.innerText.includes('Flagged Entities') || document.body.innerText.includes('Risk split') || document.body.innerText.includes('Amount Distribution')`)

  check('Query Console or Results visible', isOnQuery || isOnResult, isOnQuery ? 'query' : isOnResult ? 'results' : 'other')

  // ── If on Query Console, submit a query ──────────────────────────
  if (isOnQuery) {
    console.log('\n  Submitting query...')
    // Type into textarea
    await ev(client, `
      const ta = document.querySelector('textarea');
      if (ta) {
        const s = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, 'value')?.set;
        s?.call(ta, 'Analyse this dataset for suspicious activity');
        ta.dispatchEvent(new Event('input', { bubbles: true }));
        ta.dispatchEvent(new Event('change', { bubbles: true }));
      }
    `)
    await sleep(500)

    // Click the chip directly — more reliable than the Run button
    const chipClicked = await ev(client, `
      const chips = [...document.querySelectorAll('[aria-label*="Run query"]')];
      const chip = chips.find(c => c.textContent.includes('Analyse dataset'));
      if (chip) { chip.click(); return 'chip'; }
      const btn = [...document.querySelectorAll('button')].find(b => /run query/i.test(b.textContent));
      if (btn && !btn.disabled) { btn.click(); return 'btn'; }
      // Press Enter on textarea
      const ta = document.querySelector('textarea');
      if (ta) {
        ta.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true }));
        return 'enter';
      }
      return 'none';
    `)
    console.log('  Query trigger method:', chipClicked)

    // Wait for plan or results
    const planOrResults = await waitFor(client,
      `document.body.innerText.includes('Building execution') || document.body.innerText.includes('Flagged Entities') || document.body.innerText.includes('Execution Pipeline')`,
      20000
    )
    check('App transitions from Query Console', planOrResults)

    // Wait for results (backend takes time)
    const resultsLoaded = await waitFor(client,
      `document.body.innerText.includes('Flagged Entities') || document.body.innerText.includes('Amount Distribution')`,
      90000
    )
    check('Results Dashboard appears after query', resultsLoaded)
  }

  // ── From here on, we're on Results Dashboard ─────────────────────
  // If we started on results, verify everything is present
  await sleep(1000)

  console.log('\n  Checking Results Dashboard components:')

  const hasSummaryHeader = await ev(client, `
    document.body.innerText.includes('tools invoked') ||
    document.body.innerText.includes('Plan') ||
    document.body.innerText.includes('Query')
  `)
  check('Summary header present', hasSummaryHeader)

  // Check KPI tiles — look for the actual rendered numbers, not "txns scanned" text
  const kpiText = await ev(client, `document.body.innerText`)
  const hasKpi = kpiText?.includes('txns scanned') || kpiText?.includes('entities flagged') || kpiText?.match(/\d{2,},\d{3}/)
  check('KPI tiles rendered', !!hasKpi, hasKpi ? 'KPI numbers visible' : `body includes: "${kpiText?.slice(0, 100)}"`)

  const hasTable = await ev(client, `document.body.innerText.includes('Flagged Entities')`)
  check('Flagged Entities table rendered', hasTable)

  const hasRiskSplit = await ev(client, `document.body.innerText.includes('Risk split') || document.body.innerText.includes('High') && document.body.innerText.includes('Medium') && document.body.innerText.includes('Low')`)
  check('Risk split donut area rendered', hasRiskSplit)

  // Charts — wait for lazy load
  await sleep(4000)
  const hasCharts = await ev(client, `
    document.querySelectorAll('canvas, svg.main-svg, [class*="js-plotly-plot"]').length > 0 ||
    document.querySelectorAll('[class*="recharts"]').length > 0
  `)
  check('Charts rendered (Plotly/Recharts)', hasCharts)

  const hasNetwork = await ev(client, `
    document.body.innerText.includes('Entity Risk Network') ||
    document.body.innerText.includes('nodes ·') ||
    document.body.innerText.includes('edges')
  `)
  check('Transaction Network rendered', hasNetwork)

  // Check no ErrorBoundary
  const hasErrorBoundary = await ev(client, `document.body.innerText.includes('Something went wrong')`)
  check('No ErrorBoundary shown', !hasErrorBoundary)

  // ── JSON Inspector ────────────────────────────────────────────────
  console.log('\n  Testing JSON Inspector:')

  // Find and log all button labels for diagnosis
  const buttonLabels = await ev(client, `
    JSON.stringify([...document.querySelectorAll('button')].map(b => ({
      text: b.textContent.trim().slice(0,30),
      label: b.getAttribute('aria-label')?.slice(0,40),
      disabled: b.disabled,
      pressed: b.getAttribute('aria-pressed')
    })).filter(b => b.text || b.label))
  `)
  const btns = JSON.parse(buttonLabels ?? '[]')
  const jsonBtns = btns.filter(b =>
    b.label?.toLowerCase().includes('json') ||
    b.text?.toLowerCase().includes('json')
  )
  console.log('  JSON buttons found:', JSON.stringify(jsonBtns))

  const jsonToggleClicked = await ev(client, `
    // Try aria-label first
    let btn = document.querySelector('button[aria-label*="JSON"], button[aria-label*="json"]');
    // Try by text
    if (!btn) btn = [...document.querySelectorAll('button')].find(b => b.textContent.trim() === 'JSON');
    if (!btn) btn = [...document.querySelectorAll('button')].find(b => b.textContent.includes('JSON') && !b.disabled);
    if (btn && !btn.disabled) { btn.click(); return btn.getAttribute('aria-pressed') + ' → clicked'; }
    return 'not found';
  `)
  console.log('  JSON toggle result:', jsonToggleClicked)

  await sleep(2000)

  const inspectorOpen = await ev(client, `
    document.body.innerText.includes('Raw JSON Inspector') ||
    document.body.innerText.includes('ExecutionReport') ||
    document.body.innerText.includes('execution_plan') ||
    document.body.innerText.includes('user_query')
  `)
  check('JSON Inspector opens without crash', inspectorOpen)

  if (!inspectorOpen) {
    const postClickBody = await ev(client, `document.body.innerText.slice(0, 300)`)
    console.log('  Post-click body:', postClickBody?.replace(/\n/g, ' / ').slice(0, 150))
  }

  // ── Final error check ─────────────────────────────────────────────
  console.log('\n  Error checks:')
  const storedErrors = await ev(client, `
    (() => { try { return JSON.parse(localStorage.getItem('__aml_errors') ?? '[]') } catch { return [] } })()
  `)
  const errArr = Array.isArray(storedErrors) ? storedErrors : []
  check('No ErrorBoundary errors captured', errArr.length === 0,
    errArr.length ? errArr[0]?.message?.slice(0, 100) : '')

  const noConsoleErrors = consoleErrors.filter(e => !e.includes('%o') && !e.includes('%s')).length === 0
  check('No console errors', noConsoleErrors,
    noConsoleErrors ? '' : consoleErrors.filter(e => !e.includes('%o'))[0]?.slice(0, 150))

  // Summary
  console.log('\n═══════════════════════════════════════')
  const passed = results.filter(r => r.passed).length
  const failed = results.filter(r => !r.passed)
  console.log(`  PASSED: ${passed}/${results.length}`)
  if (failed.length) {
    console.log(`  FAILED: ${failed.length}`)
    failed.forEach(f => console.log(`    ✗ ${f.name}${f.detail ? ': ' + f.detail : ''}`))
  } else {
    console.log('  ALL CHECKS PASSED ✓')
  }

  if (consoleErrors.filter(e => !e.includes('%o')).length) {
    console.log('\n  Console errors:')
    consoleErrors.filter(e => !e.includes('%o')).forEach((e, i) =>
      console.log(`    [${i+1}] ${e.slice(0, 300)}`))
  }

  console.log('═══════════════════════════════════════\n')

  client.close()
  chrome.kill()
  process.exit(failed.length > 0 ? 1 : 0)
}

main().catch(e => {
  console.error('Fatal:', e.message)
  chrome.kill()
  process.exit(1)
})
