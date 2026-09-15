// Run with playwright-cli run-code --filename=tests/fixtures/check_manual_guide.js
async page => {
  const errors = [];
  const failed = [];
  const results = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('console', message => {
    if (message.type() === 'error') errors.push(message.text());
  });
  page.on('requestfailed', request => failed.push(request.url()));
  page.on('response', response => {
    if (response.status() >= 400) failed.push(`${response.status()} ${response.url()}`);
  });
  const base = page.url().split('/').slice(0, 3).join('/');
  await page.context().addCookies([
    {name: 'ltt_lang', value: 'vi', url: base},
  ]);
  for (const path of ['/huong-dan', '/en/huong-dan']) {
    for (const [width, height] of [[1440, 1000], [390, 844]]) {
      await page.setViewportSize({width, height});
      await page.goto(base + path, {waitUntil: 'networkidle'});
      await page.locator('#tab-desktop').click();
      const panel = page.locator('#khu-desktop');
      if (!await panel.isVisible()) throw new Error('Desktop panel is hidden');
      // Table headers are rendered uppercase by CSS; compare visible words.
      const text = (await panel.innerText()).replace(/\s+/g, ' ').toLowerCase();
      for (const expected of [
        '1.52386.6', 'Gateway base URL', `${base}/api`, 'Static API key',
        'Bearer', 'Model discovery', 'Display name', 'Allow Chat',
        'Disable Claude.ai sign-in', 'Apply Changes', 'New configuration',
        'ltt-llm-claude-compat', 'ltt-llm-claude-compat-35',
        'LTT 3.8 (Mạnh)', 'LTT 3.5 (Nhanh)',
        'Calculate 8 * 7', 'Calculate 12 * 12', '56', '144',
        'CLAUDE_CODE_MAX_CONTEXT_TOKENS=171458',
        'CLAUDE_CODE_AUTO_COMPACT_WINDOW=138690',
        'CLAUDE_CODE_MAX_OUTPUT_TOKENS=32768',
        'MAX_MCP_OUTPUT_TOKENS=16384',
        'CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS=1',
        'CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH=1',
        'CLAUDE_CODE_SUBAGENT_MODEL_FORCE=1',
        'CLAUDE_CODE_MAX_RETRIES=1',
        'CLAUDE_CODE_DISABLE_NONSTREAMING_FALLBACK=1',
        'ENABLE_TOOL_SEARCH=false',
        'Tier alias', 'opus', 'haiku',
        '138.7k', '176.4k', 'Bypass permissions',
        "Permission mode couldn't be changed", '131 tool',
      ]) {
        if (!text.includes(expected.toLowerCase())) throw new Error(`Missing ${expected}`);
      }
      if (text.includes('windows registry editor') || text.includes('hkcu')) {
        throw new Error('Registry instructions leaked into the manual form guide');
      }
      if (path.startsWith('/en/') && !text.includes('if the environment dropdown is absent')) {
        throw new Error('New-session environment instructions were not translated');
      }
      const overflow = await page.evaluate(() =>
        document.documentElement.scrollWidth > innerWidth + 1);
      if (overflow) throw new Error(`Horizontal page overflow at ${width}`);
      await page.locator('#tab-codex').click();
      if (await panel.isVisible()) throw new Error('Surface switching did not hide Desktop');
      const codex = page.locator('#khu-codex');
      const codexText = await codex.innerText();
      for (const expected of ['0.145.0', 'ltt-fast.config.toml', 'codex --profile ltt-fast',
                              'YOUR_WINDOWS_USER', '171458', '209141', '138690', '176373']) {
        if (!codexText.includes(expected)) throw new Error(`Codex missing ${expected}`);
      }
      const catalog = codex.locator('details').first();
      await catalog.locator('summary').click();
      const json = JSON.parse(await catalog.locator('code').innerText());
      if (json.models.map(model => model.slug).join(',') !== 'ltt-3.8,ltt-3.5') {
        throw new Error('Copyable catalog has wrong model IDs');
      }
      await catalog.locator('summary').click();
      if (await page.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1)) {
        throw new Error(`Codex page overflow at ${width}`);
      }
      await page.locator('#tab-desktop').click();
      if (await page.locator('.cam-khu:visible').count() !== 1) {
        throw new Error('More than one surface is shown');
      }
      const language = path.startsWith('/en/') ? 'en' : 'vi';
      await panel.screenshot({path: `tmp/kiem_cli_van_hanh/manual-guide-${language}-${width}.png`});
      results.push({language, width, fields: true, switching: true, overflow: false});
    }
  }
  if (errors.length || failed.length) {
    throw new Error(JSON.stringify({errors, failed}));
  }
  return {passed: true, results, console_errors: errors, failed_requests: failed};
}
