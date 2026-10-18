// Look at and drive the live Tauri window over the WebView2 debugging port
// (the dev launcher sets --remote-debugging-port). Node >= 22, no dependency.
//
//   node scripts/ui.mjs shot [file]        PNG of the window (default: ui.png in the OS temp dir)
//   node scripts/ui.mjs text               visible text of the page
//   node scripts/ui.mjs dom [selector]     outerHTML (default: body), trimmed to 20 kB
//   node scripts/ui.mjs eval "<js>"        evaluate an expression, print the result
//   node scripts/ui.mjs click "<selector>" click the first match
//   node scripts/ui.mjs logs [ms]          console + exceptions for a while (default 3000)
//   node scripts/ui.mjs targets            list debuggable pages
import { writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

const port = process.env.UI_DEBUG_PORT ?? '9222';
const base = `http://127.0.0.1:${port}`;

async function connect() {
  const pages = await (await fetch(`${base}/json`)).json();
  const page = pages.find((p) => p.type === 'page');
  if (!page) throw new Error(`no page on ${base}: is the dev launcher running with the debugging port?`);
  const ws = new WebSocket(page.webSocketDebuggerUrl);
  await new Promise((resolve, reject) => {
    ws.onopen = resolve;
    ws.onerror = () => reject(new Error('websocket failed'));
  });
  let id = 0;
  const pending = new Map();
  const listeners = [];
  ws.onmessage = (event) => {
    const msg = JSON.parse(event.data);
    if (msg.id && pending.has(msg.id)) {
      const { resolve, reject } = pending.get(msg.id);
      pending.delete(msg.id);
      msg.error ? reject(new Error(msg.error.message)) : resolve(msg.result);
    } else listeners.forEach((l) => l(msg));
  };
  const send = (method, params = {}) =>
    new Promise((resolve, reject) => {
      pending.set(++id, { resolve, reject });
      ws.send(JSON.stringify({ id, method, params }));
    });
  return { send, on: (l) => listeners.push(l), close: () => ws.close() };
}

async function evaluate(cdp, expression) {
  const { result, exceptionDetails } = await cdp.send('Runtime.evaluate', {
    expression,
    returnByValue: true,
    awaitPromise: true,
  });
  if (exceptionDetails) throw new Error(exceptionDetails.exception?.description ?? exceptionDetails.text);
  return result.value;
}

const [cmd, arg] = process.argv.slice(2);
if (cmd === 'targets') {
  console.log(JSON.stringify(await (await fetch(`${base}/json`)).json(), null, 2));
  process.exit(0);
}
const cdp = await connect();
try {
  if (cmd === 'shot') {
    const { data } = await cdp.send('Page.captureScreenshot', { format: 'png' });
    const file = arg ?? join(tmpdir(), 'ui.png');
    writeFileSync(file, Buffer.from(data, 'base64'));
    console.log(file);
  } else if (cmd === 'text') {
    console.log(await evaluate(cdp, 'document.body.innerText'));
  } else if (cmd === 'dom') {
    const html = await evaluate(cdp, `(document.querySelector(${JSON.stringify(arg ?? 'body')})??document.body).outerHTML`);
    console.log(html.slice(0, 20000));
  } else if (cmd === 'eval') {
    console.log(JSON.stringify(await evaluate(cdp, arg), null, 2));
  } else if (cmd === 'click') {
    const ok = await evaluate(cdp, `(()=>{const e=document.querySelector(${JSON.stringify(arg)});if(!e)return false;e.click();return true})()`);
    console.log(ok ? 'clicked' : 'no match');
  } else if (cmd === 'logs') {
    await cdp.send('Runtime.enable');
    await cdp.send('Log.enable');
    cdp.on((m) => {
      if (m.method === 'Runtime.consoleAPICalled')
        console.log(`[${m.params.type}]`, m.params.args.map((a) => a.value ?? a.description).join(' '));
      if (m.method === 'Runtime.exceptionThrown') console.log('[exception]', m.params.exceptionDetails.text, m.params.exceptionDetails.exception?.description ?? '');
      if (m.method === 'Log.entryAdded') console.log(`[${m.params.entry.level}]`, m.params.entry.text);
    });
    await new Promise((r) => setTimeout(r, Number(arg ?? 3000)));
  } else {
    console.error('usage: node scripts/ui.mjs shot|text|dom|eval|click|logs|targets [arg]');
    process.exitCode = 1;
  }
} finally {
  cdp.close();
}
