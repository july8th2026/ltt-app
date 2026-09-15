/**
 * Operational acceptance for the LTT connector and Claude Desktop.
 *
 * The production orchestrator supplies a temporary key in process memory:
 *   node tools/kiem_cli_van_hanh.mjs --api-only \
 *     --url https://app.lttstudios.com
 *
 * The harness never accepts a password and never writes the API secret. It
 * creates a short-lived key in the visible developer portal, keeps its secret
 * in process memory, revokes it in finally, and always runs connector `go`.
 */
import { execFile, execFileSync, execSync } from 'node:child_process';
import { existsSync, mkdirSync, writeFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { pathToFileURL } from 'node:url';
import { promisify } from 'node:util';

const execFileAsync = promisify(execFile);
const argv = process.argv.slice(2);
const option = (name, fallback = '') => {
  const at = argv.indexOf(name);
  return at >= 0 && argv[at + 1] ? argv[at + 1] : fallback;
};
const has = (name) => argv.includes(name);
const rootUrl = option('--url', 'https://app.lttstudios.com').replace(/\/$/, '');
const cdp = option('--cdp');
const expectedUser = option('--user', process.env.LTT_SMOKE_USER || 'akakenly.design@gmail.com');
const connector = option('--connector', resolve('tools/cam_cli.py'));
const reportPath = option('--report', resolve('tmp/kiem_cli_van_hanh/bao_cao.json'));
const apiOnly = has('--api-only');
const waitCapacity = has('--wait-capacity');
const capacityDeadline = Date.now() + 12 * 60 * 1000;
const suppliedKey = process.env.LTT_API_KEY || '';
const models = [
  { route: 'ltt-llm-claude-compat', suffix: '38',
    reasoningEffort: 'xhigh',
    question: 'Calculate 8 * 7. Reply with only the number.', expected: '56' },
  { route: 'ltt-llm-claude-compat-35', suffix: '35',
    reasoningEffort: null,
    question: 'Calculate 12 * 12. Reply with only the number.', expected: '144' },
];
const report = {
  account: { expected: expectedUser, matched: false },
  key: { created: false, revoked: false },
  api: [],
  transient_capacity: [],
  desktop: [],
  cleanup: { connector_go: false },
  console_errors: [],
  failed_requests: [],
  passed: false,
};

function saveReport() {
  mkdirSync(dirname(reportPath), { recursive: true });
  writeFileSync(reportPath, `${JSON.stringify(report, null, 2)}\n`, { encoding: 'utf8' });
}

async function loadChromium() {
  const candidates = [];
  try {
    const globalRoot = execSync('npm root -g', { encoding: 'utf8' }).trim();
    candidates.push(join(globalRoot, '@playwright', 'cli', 'node_modules', 'playwright', 'index.mjs'));
    candidates.push(join(globalRoot, 'playwright', 'index.mjs'));
  } catch { /* try module resolution below */ }
  candidates.push('playwright');
  for (const candidate of candidates) {
    try {
      const imported = await import(candidate.endsWith('.mjs') && existsSync(candidate)
        ? pathToFileURL(candidate).href : candidate);
      if (imported.chromium) return imported.chromium;
    } catch { /* next candidate */ }
  }
  throw new Error('Playwright is unavailable; install @playwright/cli globally.');
}

async function apiCall(key, label, path, init = {}) {
  let attempt = 0;
  while (true) {
    attempt += 1;
    const headers = {
      Authorization: `Bearer ${key}`,
      ...(init.body ? { 'Content-Type': 'application/json' } : {}),
      ...(init.headers || {}),
    };
    const response = await fetch(`${rootUrl}${path}`, { ...init, headers });
    const text = await response.text();
    if (!response.ok && waitCapacity && [429, 500].includes(response.status)
        && Date.now() < capacityDeadline) {
      report.transient_capacity.push({ label, status: response.status, attempt });
      const retryAfter = Number(response.headers.get('retry-after') || 2);
      await new Promise((done) => setTimeout(done, Math.min(10, Math.max(2, retryAfter)) * 1000));
      continue;
    }
    const item = { label, status: response.status, passed: response.ok, attempts: attempt };
    report.api.push(item);
    if (!response.ok) throw new Error(`${label} returned HTTP ${response.status}`);
    return { response, text };
  }
}

async function exerciseApi(key) {
  await apiCall(key, 'tools', '/api/v1/tools');
  await apiCall(key, 'credits', '/api/v1/credits/balance');
  for (const modelCase of models) {
    const { route: model, question, expected, reasoningEffort } = modelCase;
    // Qwen3.8 has native low/medium/xhigh. Qwen3.5 publishes thinking on/off,
    // so omitting this optional API field tests its server-side thinking-on
    // default instead of inventing a `low` tier that the model does not have.
    const reasoning = reasoningEffort ? { reasoning_effort: reasoningEffort } : {};
    const message = await apiCall(key, `messages:${model}`, '/api/v1/messages', {
      method: 'POST',
      body: JSON.stringify({
        model,
        max_tokens: 1024,
        ...reasoning,
        stream: false,
        messages: [{ role: 'user', content: question }],
      }),
    });
    const parsed = JSON.parse(message.text);
    const answer = (parsed.content || []).filter((x) => x.type === 'text').map((x) => x.text).join('');
    if (!answer.includes(expected)) throw new Error(`messages:${model} returned the wrong answer`);

    const streamed = await apiCall(key, `responses:${model}`, '/api/v1/responses', {
      method: 'POST',
      body: JSON.stringify({ model, stream: true, input: question,
        max_output_tokens: 1024, ...reasoning }),
    });
    if (!streamed.text.includes('response.created') || !streamed.text.includes('response.completed')) {
      throw new Error(`responses:${model} did not complete its SSE lifecycle`);
    }

    const tools = [{
      name: 'report_marker',
      description: 'Return the supplied integer marker.',
      input_schema: {
        type: 'object', properties: { value: { type: 'integer' } }, required: ['value'],
      },
    }];
    const firstBody = {
      model, max_tokens: 1024, ...reasoning, stream: false, tools,
      messages: [{ role: 'user', content: 'Use report_marker with value 42.' }],
    };
    const first = await apiCall(key, `tool-call:${model}`, '/api/v1/messages', {
      method: 'POST', body: JSON.stringify(firstBody),
    });
    const firstJson = JSON.parse(first.text);
    const toolUse = (firstJson.content || []).find((x) => x.type === 'tool_use');
    if (!toolUse || toolUse.name !== 'report_marker' || Number(toolUse.input?.value) !== 42) {
      throw new Error(`tool-call:${model} did not return the requested tool invocation`);
    }
    const second = await apiCall(key, `tool-result:${model}`, '/api/v1/messages', {
      method: 'POST',
      body: JSON.stringify({
        model, max_tokens: 1024, ...reasoning, stream: false, tools,
        messages: [
          firstBody.messages[0],
          { role: 'assistant', content: firstJson.content },
          { role: 'user', content: [{
            type: 'tool_result', tool_use_id: toolUse.id,
            content: 'The tool returned 42. State the integer returned by the tool.',
          }] },
        ],
      }),
    });
    const secondJson = JSON.parse(second.text);
    const finalText = (secondJson.content || []).filter((x) => x.type === 'text')
      .map((x) => x.text).join('');
    if (!finalText.includes('42')) {
      throw new Error(`tool-result:${model} did not survive the second turn`);
    }
  }
}

function connectorCommand(subcommand) {
  if (connector.toLowerCase().endsWith('.py')) {
    return { file: 'python', args: [connector, subcommand] };
  }
  return { file: connector, args: [subcommand] };
}

async function runConnector(subcommand, extraArgs = [], env = process.env) {
  const command = connectorCommand(subcommand);
  const result = await execFileAsync(command.file, [...command.args, ...extraArgs], {
    cwd: resolve('.'), env, windowsHide: true, maxBuffer: 1024 * 1024,
  });
  return result.stdout;
}

async function runDesktop(model) {
  const suffix = model === 'ltt-llm-claude-compat' ? '38' : '35';
  const question = suffix === '38'
    ? 'Calculate 8 * 7. Reply with only the number.'
    : 'Calculate 12 * 12. Reply with only the number.';
  const expected = suffix === '38' ? '56' : '144';
  const psReport = resolve(dirname(reportPath), `desktop_${suffix}.json`);
  const args = [
    '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', resolve('tools/kiem_claude_desktop.ps1'),
    '-Model', model, '-Prompt', question, '-Expected', expected,
    '-ReportPath', psReport,
  ];
  const result = await execFileAsync('powershell.exe', args, {
    cwd: resolve('.'), windowsHide: false, maxBuffer: 1024 * 1024,
  });
  const lines = result.stdout.trim().split(/\r?\n/);
  const start = lines.findIndex((line) => line.trim().startsWith('{'));
  const item = JSON.parse(lines.slice(start).join('\n'));
  report.desktop.push(item);
  if (!item.answered || !item.selected || item.models_visible.length !== 2) {
    throw new Error(`Claude Desktop acceptance failed for ${model}`);
  }
}

async function createKey(page) {
  await page.goto(`${rootUrl}/developers/keys`, { waitUntil: 'domcontentloaded' });
  const details = page.locator('#tao-khoa');
  if (!(await details.getAttribute('open'))) await details.locator('summary').click();
  await page.locator('#key-name').fill(`h46-desktop-${Date.now()}`);
  await page.locator('input[name="mode"][value="live"]').check();
  for (const scope of ['tools:read', 'jobs:create', 'credits:read']) {
    const box = page.locator(`input[name="scopes"][value="${scope}"]`);
    if (!(await box.isChecked())) await box.check();
  }
  await page.locator('#key-expiry').fill('1');
  await Promise.all([
    page.waitForLoadState('domcontentloaded'),
    details.locator('button[type="submit"]').click(),
  ]);
  const secret = (await page.locator('pre.chuoi code').textContent() || '').trim();
  const keyId = (await page.locator('.dev-mat .dev-id').textContent() || '').trim();
  if (!secret.startsWith('ltt_sk_') || !keyId) throw new Error('Portal did not reveal the new live key once.');
  report.key.created = true;
  return { secret, keyId };
}

async function revokeKey(page, keyId) {
  await page.goto(`${rootUrl}/developers/keys`, { waitUntil: 'domcontentloaded' });
  const form = page.locator(`form[action="/developers/keys/${keyId}/revoke"]`);
  if ((await form.count()) !== 1) throw new Error('The temporary key revoke form was not found.');
  page.once('dialog', (dialog) => dialog.accept());
  await Promise.all([page.waitForLoadState('domcontentloaded'), form.locator('button').click()]);
  report.key.revoked = true;
}

let browser;
let page;
let keyId = '';
let key = suppliedKey;
let primaryError;
try {
  if (!apiOnly) {
    if (!cdp) throw new Error('Production acceptance requires --cdp to an already authenticated browser.');
    const chromium = await loadChromium();
    browser = await chromium.connectOverCDP(cdp);
    const context = browser.contexts()[0];
    if (!context) throw new Error('The CDP browser has no context.');
    page = await context.newPage();
    page.on('console', (message) => {
      if (message.type() === 'error') report.console_errors.push(message.text().slice(0, 300));
    });
    page.on('requestfailed', (request) => {
      report.failed_requests.push(`${request.method()} ${request.url()} ${request.failure()?.errorText || ''}`.slice(0, 400));
    });
    await page.goto(`${rootUrl}/developers/privacy/export`, { waitUntil: 'domcontentloaded' });
    const exported = JSON.parse(await page.locator('body').innerText());
    report.account.matched = String(exported.account?.email || '').toLowerCase() === expectedUser.toLowerCase();
    if (!report.account.matched) throw new Error('The browser is not signed in as the configured ordinary test account.');
    ({ secret: key, keyId } = await createKey(page));
  } else if (!key) {
    throw new Error('--api-only requires LTT_API_KEY in the process environment.');
  }

  await exerciseApi(key);
  if (!apiOnly) {
    await runConnector('cam', ['--goc', rootUrl, '--model', 'ltt-3.8', '--muc', 'claude-desktop'], {
      ...process.env, LTT_API_KEY: key,
    });
    for (const modelCase of models) await runDesktop(modelCase.route);
  }
  report.passed = true;
} catch (error) {
  primaryError = error;
  report.error = String(error.message || error).slice(0, 500);
} finally {
  if (!apiOnly) {
    try {
      await runConnector('go');
      report.cleanup.connector_go = true;
    } catch (error) {
      report.cleanup.connector_error = String(error.message || error).slice(0, 300);
    }
    if (page && keyId) {
      try { await revokeKey(page, keyId); }
      catch (error) { report.key.revoke_error = String(error.message || error).slice(0, 300); }
    }
    if (page) await page.close().catch(() => {});
    if (browser) await browser.close().catch(() => {});
  }
  if (report.console_errors.length || report.failed_requests.length || !report.key.revoked && !apiOnly) {
    report.passed = false;
  }
  saveReport();
}

if (!report.passed) {
  console.error(`Operational acceptance failed. See ${reportPath}`);
  if (primaryError) console.error(primaryError.message);
  process.exit(1);
}
console.log(`Operational acceptance passed. Report: ${reportPath}`);
