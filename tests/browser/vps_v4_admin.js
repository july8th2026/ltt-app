async page => {
  const base = 'http://127.0.0.2:8100';
  const pageErrors = [], consoleErrors = [], failedRequests = [], serverErrors = [];
  page.on('pageerror', error => pageErrors.push(error.message));
  page.on('console', message => {
    if (message.type() === 'error') consoleErrors.push(message.text());
  });
  page.on('requestfailed', request => failedRequests.push({url: request.url(), error: request.failure()?.errorText}));
  page.on('response', response => {
    if (response.status() >= 500) serverErrors.push({url: response.url(), status: response.status()});
  });
  const check = (condition, message) => { if (!condition) throw new Error(message); };
  await page.context().clearCookies();
  await page.context().setExtraHTTPHeaders({'Accept-Language': 'vi'});
  await page.setViewportSize({width: 1440, height: 1000});
  await page.goto(base + '/vps/admin/cong-ha-tang');
  check(page.url().split('?')[0] === base + '/login', 'anonymous admin must redirect to login');
  await page.goto(base + '/_vps_v4_test/session/outsider');
  let response = await page.goto(base + '/vps/admin/cong-ha-tang');
  check(response.status() === 403, 'ordinary customer must not enter admin');
  response = await page.goto(base + '/vps');
  check(response.status() === 404, 'outsider must not enter owner allowlist MVP');
  await page.goto(base + '/_vps_v4_test/session/customer');
  response = await page.goto(base + '/vps');
  check(response.status() === 200, 'allowlisted test owner must see VPS');
  check(await page.locator('select[name="profile_id"], select[name="provider"]').count() === 0,
        'customer must not select provider or infrastructure profile');
  const pending = page.locator('.vps-may-the').filter({hasText: 'OVH DELIVERY — LOCAL TEST'});
  check(await pending.count() === 1, 'owner must see the pending VPS fixture');
  check((await pending.getAttribute('class')).includes('tt-warn'),
        'pending provider delivery must keep provisioning status, not an instance error');
  check(!(await pending.getAttribute('class')).includes('tt-err'),
        'pending provider delivery must not show an instance failure');
  response = await page.goto(base + '/vps/local-pending-instance');
  check(response.status() === 200, 'owner must see pending VPS details');
  check(await page.locator('.alert-warn').count() > 0, 'pending VPS must show its next-step message');
  response = await page.goto(base + '/_vps_v4_test/session/outsider');
  response = await page.goto(base + '/vps/local-pending-instance');
  check(response.status() === 404, 'outsider must not read pending VPS details');
  await page.goto(base + '/_vps_v4_test/session/admin');
  await page.goto(base + '/admin/');
  await page.getByRole('link', {name: 'VPS', exact: true}).click();
  await page.getByRole('link', {name: 'Cổng hạ tầng', exact: true}).click();
  check(await page.getByRole('heading', {name: 'Cổng hạ tầng', exact: true}).isVisible(), 'real profile admin heading missing');
  const card = page.locator('section').filter({has: page.getByRole('heading', {name: 'OVH-SGP-PROD — LOCAL TEST', exact: true})});
  check((await card.innerText()).includes('STANDBY'), 'unverified profile must remain standby');
  check((await card.innerText()).includes('Compute health:'), 'component health must be visible');
  check((await card.innerText()).includes('VM count:'), 'profile VM count must be visible');
  check((await card.innerText()).includes('Available public IPs:'), 'available IPv4 count must be visible');
  check((await card.innerText()).includes('Credentials:'), 'credential-reference state must be visible');
  await card.locator('summary').filter({hasText: 'Deploy provenance'}).click();
  check((await card.innerText()).includes('LTTSTUDIOSAPP SHA'), 'deploy provenance must be visible');
  check((await card.innerText()).includes('Machine B SHA'), 'Machine B provenance must be visible');
  check((await card.innerText()).includes('Runtime generated_at'), 'runtime generation provenance must be visible');
  check((await card.innerText()).includes('Kho IPv4'), 'read-only IPv4 inventory must be visible');
  check(await card.getByRole('button', {name: 'Nạp inventory OVH', exact: true}).isVisible(),
        'OVH inventory sync action must be visible only to admin');
  await page.screenshot({path: 'docs/VPS_V4/evidence/admin-desktop.png', fullPage: true});
  const connection = page.waitForResponse(r => r.url().endsWith('/profiles/local-ovh-profile/action') && r.request().method() === 'POST');
  await card.getByRole('button', {name: 'Test Connection', exact: true}).click();
  check((await connection).status() === 409, 'unconfigured connection probe must fail closed');
  await page.goto(base + '/vps/admin/cong-ha-tang');
  const blocked = page.waitForResponse(r => r.url().endsWith('/profiles/local-ovh-profile/action') && r.request().method() === 'POST');
  await card.getByRole('button', {name: 'Đặt default', exact: true}).click();
  check((await blocked).status() === 409, 'invalid preflight must refuse default');
  await page.goto(base + '/vps/admin/cong-ha-tang');
  await card.getByRole('button', {name: 'Preflight', exact: true}).click();
  check((await card.innerText()).includes('NOT READY'), 'failed preflight must not report healthy');
  await card.getByRole('button', {name: 'Disable', exact: true}).click();
  check((await card.innerText()).includes('DISABLED'), 'profile disable must be visible after redirect');
  await card.locator('summary').filter({hasText: 'Sửa cấu hình tham chiếu'}).click();
  const edit = card.locator('form[action="/vps/admin/profiles/save"]');
  await edit.locator('[name="compute_ref"]').fill('LTT_VPS_PROXMOX');
  await edit.locator('[name="runtime_ref"]').fill('LTT_OVH_MACHINE_B_RUNTIME');
  await edit.locator('[name="router_ref"]').fill('LTT_OVH_ROUTER');
  await edit.getByRole('button', {name: 'Lưu cấu hình', exact: true}).click();
  check((await card.innerText()).includes('DISABLED'), 'saving config must not re-enable disabled profile');
  const add = page.locator('details').filter({has: page.locator('summary').filter({hasText: 'Thêm profile hạ tầng'})});
  await add.locator('summary').click();
  await add.locator('[name="name"]').fill('VULTR — LOCAL STANDBY');
  await add.locator('[name="slug"]').fill('vultr-local-standby');
  await add.locator('[name="credential_ref"]').fill('LTT_VULTR');
  await add.locator('[name="gateway_ref"]').fill('LTT_VPS_GATEWAY');
  await add.locator('[name="runtime_ref"]').fill('LTT_VPS_MACHINE_B_RUNTIME');
  await add.locator('[name="router_ref"]').fill('LTT_VPS_ROUTER');
  await add.locator('[name="ip_backend"]').selectOption('vultr_reserved_ip');
  await add.locator('[name="mapping_strategy"]').selectOption('ltt_nft_maps');
  await add.getByRole('button', {name: 'Thêm profile', exact: true}).click();
  const vultr = page.locator('section').filter({has: page.getByRole('heading', {name: 'VULTR — LOCAL STANDBY', exact: true})});
  check((await vultr.innerText()).includes('STANDBY'), 'new profile must start standby');
  await page.setViewportSize({width: 390, height: 844});
  await page.reload();
  check(await page.getByRole('heading', {name: 'Cổng hạ tầng', exact: true}).isVisible(), 'mobile profile page missing');
  await card.locator('summary').filter({hasText: 'Sửa cấu hình tham chiếu'}).click();
  check(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), 'mobile horizontal overflow');
  await page.screenshot({path: 'docs/VPS_V4/evidence/admin-mobile.png', fullPage: true});
  check(pageErrors.length === 0, 'unexpected page JavaScript error');
  check(failedRequests.length === 0, 'unexpected failed network request');
  check(serverErrors.length === 0, 'unexpected server error');
  const unexpectedConsoleErrors = consoleErrors.filter(message => !/status of (403|404|409)/.test(message));
  check(unexpectedConsoleErrors.length === 0, 'unexpected console error: ' + unexpectedConsoleErrors.join('; '));
  return {status: 'PASS', scope: 'local fixture only; no production VM/IP',
          pageErrors, unexpectedConsoleErrors, failedRequests, serverErrors,
          expectedHttpDenials: [403, 404, 409], screenshots: ['docs/VPS_V4/evidence/admin-desktop.png', 'docs/VPS_V4/evidence/admin-mobile.png']};
}
