/**
 * Captures all console.log output from the browser while running
 * the query "Show all high risk customers".
 */

import { spawn } from 'child_process'

const CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
const APP_URL = 'http://localhost:5173'
const DEBUG_PORT = 9226
const sleep = (ms) => new Promise(r => setTimeout(r, ms))

const chrome = spawn(CHROME, [
  `--remote-debugging-port=${DEBUG_PORT}`,
  '--headless=new',
  '--no-sandbox',
  '--disable-gpu',
  `--user-data-dir=/tmp/chrome-logs`,
  '--window-size=1280,900',
], { stdio: 'pipe' })
chrome.stderr.on('data', () => {})

async function waitForChrome() {
  for (let i = 0; i < 40; i++) {
    try { if ((await fetch(`http://localhost:${DEBUG_PORT}/json/version`)).ok) return } catch {}
    await sleep(250)
  }
  throw new Error('Chrome not ready')
}

async function getWsUrl() {
  for (let i = 0; i < 10; i++) {
    try {
      const tabs = await (await fetch(`http://localhost:${DEBUG_PORT}/json`)).json()
      const pg = tabs.find(t => t.type === 'page')
      if (pg?.webSocketDebuggerUrl) return pg.webSocketDebuggerUrl
    } catch {}
    await sleep(200)
  }
  throw new Error('No tab')
}

function makeCdp(wsUrl) {
  return new Promise(res => {
    let id = 0; const pending = new Map(); const listeners = new Map()
    const ws = new WebSocket(wsUrl)
    ws.addEventListener('message', ({ data }) => {
      const m = JSON.parse(data)
      if (m.id !== undefined && pending.has(m.id)) {
        const { res, rej } = pending.get(m.id); pending.delete(m.id)
        m.error ? rej(new Error(m.error.message)) : res(m.result)
      } else if (m.method) { (listeners.get(m.method) ?? []).forEach(cb => cb(m.params)) }
    })
    const client = {
      send: (method, params = {}) => new Promise((res, rej) => {
        const i = ++id; pending.set(i, { res, rej }); ws.send(JSON.stringify({ id: i, method, params }))
      }),
      on: (event, fn) => { const c = listeners.get(event) ?? []; c.push(fn); listeners.set(event, c) },
      close: () => ws.close(),
    }
    ws.addEventListener('open', () => res(client))
  })
}

const allLogs = []

async function main() {
  await waitForChrome()
  const client = await makeCdp(await getWsUrl())
  await client.send('Runtime.enable')
  await client.send('Console.enable')
  await client.send('Page.enable')

  // Capture all console output — log, warn, error
  client.on('Console.messageAdded', ({ message }) => {
    // Only capture our debug logs (SUMMARY METRICS, KPI VALUE, COUNTUP)
    if (message.text && (
      message.text.includes('SUMMARY METRICS') ||
      message.text.includes('KPI VALUE') ||
      message.text.includes('COUNTUP')
    )) {
      allLogs.push({ level: message.level, text: message.text })
    }
  })

  // Also capture via Runtime.consoleAPICalled for structured objects
  client.on('Runtime.consoleAPICalled', ({ type, args }) => {
    if (!args || args.length === 0) return
    const firstArg = args[0]?.value ?? args[0]?.description ?? ''
    if (
      String(firstArg).includes('SUMMARY METRICS') ||
      String(firstArg).includes('KPI VALUE') ||
      String(firstArg).includes('COUNTUP')
    ) {
      // Collect all arg values
      const values = args.map(a => {
        if (a.value !== undefined) return JSON.stringify(a.value)
        if (a.type === 'object' && a.preview) {
          // Format object preview
          const props = a.preview.properties?.map(p => `${p.name}: ${p.value}`).join(', ')
          return `{${props}}`
        }
        return a.description ?? a.value ?? '(object)'
      })
      allLogs.push({ level: type, text: values.join(' ') })
    }
  })

  await client.send('Runtime.enable')

  // Navigate
  await client.send('Page.navigate', { url: APP_URL })
  await sleep(3000)

  // Submit query via the chip
  await client.send('Runtime.evaluate', {
    expression: `
      const ta = document.querySelector('textarea');
      if (ta) {
        const s = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, 'value')?.set;
        s?.call(ta, 'Show all high risk customers');
        ta.dispatchEvent(new Event('input', { bubbles: true }));
      }
    `,
    returnByValue: true,
    awaitPromise: false,
  })
  await sleep(200)

  // Click Run Query button
  await client.send('Runtime.evaluate', {
    expression: `
      const btn = [...document.querySelectorAll('button')].find(b =>
        /run query/i.test(b.textContent) && !b.disabled
      );
      if (btn) btn.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, view: window }));
      !!btn
    `,
    returnByValue: true,
    awaitPromise: false,
  })

  console.log('Query submitted, waiting for Results Dashboard (up to 60s)...')

  // Wait for results to appear
  const start = Date.now()
  let resultsVisible = false
  while (Date.now() - start < 60000) {
    const r = await client.send('Runtime.evaluate', {
      expression: `document.body.innerText.includes('Flagged Entities') || document.body.innerText.includes('txns scanned')`,
      returnByValue: true,
      awaitPromise: false,
    })
    if (r?.result?.value) { resultsVisible = true; break }
    await sleep(500)
  }

  if (resultsVisible) {
    console.log('Results Dashboard visible. Waiting 3s for all renders to settle...')
    await sleep(3000)
  } else {
    console.log('WARNING: Results Dashboard did not appear within 60s')
  }

  // Print all captured debug logs
  console.log('\n═══════════════════════════════════════════════')
  console.log('  CAPTURED DEBUG LOGS')
  console.log('═══════════════════════════════════════════════\n')

  if (allLogs.length === 0) {
    console.log('  (no debug logs captured)\n')
  } else {
    allLogs.forEach((entry, i) => {
      console.log(`[${String(i+1).padStart(3)}] ${entry.level.toUpperCase()}: ${entry.text}`)
    })
  }

  console.log('\n═══════════════════════════════════════════════')
  console.log(`  Total debug log entries: ${allLogs.length}`)
  console.log('═══════════════════════════════════════════════\n')

  client.close()
  chrome.kill()
}

main().catch(e => { console.error('Fatal:', e.message); chrome.kill(); process.exit(1) })
