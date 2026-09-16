// Use only with the isolated dev_portal_harness.py server after signing in.
async page => {
  const base = page.url().split('/').slice(0, 3).join('/');
  if (base !== 'http://127.0.0.1:8136') throw new Error('Local preview required');
  const errors = [];
  const failed = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('console', message => { if (message.type() === 'error') errors.push(message.text()); });
  page.on('requestfailed', request => failed.push(request.url()));
  page.on('response', response => { if (response.status() >= 400) failed.push(response.status()); });
  const results = [];
  for (const path of ['/developers/keys', '/en/developers/keys']) {
    for (const [width, height] of [[1440, 1000], [390, 844]]) {
      await page.setViewportSize({width, height});
      await page.goto(base + path, {waitUntil: 'networkidle'});
      const unrestricted = page.locator('.dev-gioi-han').filter({hasText: /Mọi công cụ công khai đang mở|All currently exposed public tools/});
      if (!await unrestricted.count()) {
        throw new Error('Unrestricted tools state missing');
      }
      await page.locator('#tao-khoa summary').click();
      const options = page.locator('input[name=allowed_tools]');
      if (!await options.count()) throw new Error('Public tools checkboxes missing');
      for (const option of await options.all()) {
        if (await option.isChecked()) throw new Error('Tool restriction unexpectedly enabled');
      }
      const lang = path.startsWith('/en/') ? 'en' : 'vi';
      await page.screenshot({path: `tmp/kiem_cli_van_hanh/manual-keys-${lang}-${width}.png`, fullPage: true});
      results.push({lang, width, all_tools_state: true, optional_tools_visible: true});
    }
  }
  const keyName = `Browser test unrestricted ${Date.now()}`;
  await page.locator('#key-name').fill(keyName);
  await page.locator('input[name=mode][value=test]').check();
  await page.locator('input[name=scopes][value="jobs:create"]').check();
  await page.locator('#tao-khoa button[type=submit]').click();
  if (!await page.locator('.dev-mat').isVisible()) throw new Error('Key creation failed');
  // Do not read, log, copy or screenshot the revealed credential.
  // Navigate to GET: reload of a POST can resubmit the form and issue a NEW key.
  await page.goto(base + '/developers/keys', {waitUntil: 'networkidle'});
  if (await page.locator('.dev-mat').count()) throw new Error('Secret reappeared after refresh');
  const newRow = page.locator('tr').filter({hasText: keyName});
  if (!await newRow.locator('code').filter({hasText: 'jobs:create'}).count()) {
    throw new Error('Write scope did not persist');
  }
  if (!await newRow.locator('.dev-gioi-han').filter({hasText: /Mọi công cụ công khai đang mở|All currently exposed public tools/}).count()) {
    throw new Error('Empty tool selection did not remain unrestricted');
  }
  if (errors.length || failed.length) throw new Error(JSON.stringify({errors, failed}));
  return {passed: true, results, created_test_key: true, secret_hidden_after_refresh: true,
          console_errors: errors, failed_requests: failed};
}
