// Chup bang chung cho lan UI-5 (§3b.4). ⛔ Khong phai phep do — phep do nam o
// `agent_ui_v2_ui5_nghiem_thu.js`; tep nay chi dat man hinh vao dung trang
// thai roi de nguoi chup.
//
// Chay:
//   playwright-cli -s=ui5 run-code --filename=tests/browser/agent_ui_v2_ui5_anh_chup.js
async page => {
  const base = 'http://127.0.0.1:8204';
  await page.goto(base + '/agent/canvas');
  await page.locator('#agent-canvas-root').waitFor();
  await page.waitForFunction(async () => {
    const r = await fetch('/agent/api/v3/workflows',
      {credentials: 'same-origin', headers: {Accept: 'application/json'}});
    return (await r.json()).items?.length > 0;
  }, null, {timeout: 20000});

  const type = await page.evaluate(async () => {
    const pal = await (await fetch('/agent/api/v3/palette',
      {credentials: 'same-origin', headers: {Accept: 'application/json'}})).json();
    const ds = pal.nhom.flatMap(n => n.nut)
      .filter(n => (n.credential || []).includes('api_key'));
    return (ds.find(n => !n.type.startsWith('core.')) || ds[0]).type;
  });

  await page.evaluate(async (type) => {
    const csrf = document.querySelector('#agent-canvas-root').dataset.csrfToken;
    const lay = async u => await (await fetch(u, {credentials: 'same-origin',
      headers: {Accept: 'application/json'}})).json();
    const ds = await lay('/agent/api/v3/workflows');
    const id = ds.items[0].id;
    const cur = await lay('/agent/api/v3/workflows/' + id);
    await fetch('/agent/api/v3/workflows/' + id, {method: 'PUT',
      credentials: 'same-origin',
      headers: {'Content-Type': 'application/json', 'X-CSRF-Token': csrf,
                'If-Match': '"' + cur.revision + '"'},
      body: JSON.stringify({csrf_token: csrf, document: {
        version: 3, goal: '', budget_max_credit: 0, active_page_id: 'p1',
        pages: [{id: 'p1', name: 'Page 1', viewport: {x: 0, y: 0, zoom: 1},
                 frames: [], notes: [], comments: [],
                 nodes: [{id: 'n1', type: 'tool', position: {x: 120, y: 120},
                          data: {tool: type, params: {}}}],
                 edges: []}]}})});
  }, type);

  await page.goto(base + '/agent/canvas');
  await page.locator('.react-flow__node').first().waitFor({timeout: 20000});
  await page.locator('.react-flow__node').first().click();
  await page.locator('#o-ket-noi-chon').waitFor({timeout: 15000});
  // Mo form tao ket noi — trang thai dat gia nhat de chup: o chon + form TAI
  // CHO trong cung mot panel.
  await page.selectOption('#o-ket-noi-chon', '\u0000tao-ket-noi');
  await page.locator('form[aria-label="Tạo kết nối mới"]').waitFor({timeout: 10000});
  await page.waitForTimeout(400);
  return {status: 'PASS', so_lieu: {type}};
}
