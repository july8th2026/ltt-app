// UI-8b nghiem thu (che do A — may chu CO LAP cong 8211).
//
// Vá B7 (`02_SCORECARD.md`): "Soạn bằng AI" phải hiện XEM TRƯỚC (diff) trước
// khi ghi đè canvas. ⛔ Không đọc source code rồi tuyên bố xong — ba mệnh đề
// dưới đây CHỈ đo được trên trình duyệt thật, không phải jsdom:
//   * dialog thật sự MỞ trên layout thật (Suspense + React.lazy load xong);
//   * TÊN BƯỚC hiển thị là chữ người đọc được (lấy từ palette thật của máy
//     chủ), ⛔ không phải id kỹ thuật do máy chủ sinh;
//   * bấm "Huỷ" qua một vòng round-trip mạng THẬT rồi để nguyên canvas —
//     vitest (`UseWorkflowRunSoanXemTruoc.test.tsx`) đã canh việc này ở tầng
//     hook với fetch giả; bài này canh lại đúng mệnh đề đó qua mạng THẬT.
//
// Máy chủ thử mock `planner.goi_model` (tests/browser/agent_ui_v2_ui8b_may_chu.py)
// để khỏi tốn quota LLM nội bộ thật — xem "KHAC MOT" trong tệp đó.
//
// Chạy:
//   set AGENT_UI8B_FIXTURE_ROOT=<thu muc ngoai kho>
//   python -m uvicorn tests.browser.agent_ui_v2_ui8b_may_chu:app --host 127.0.0.1 --port 8211
//   playwright-cli -s=ui8b run-code --filename=tests/browser/agent_ui_v2_ui8b_nghiem_thu.js
async page => {
  const base = 'http://127.0.0.1:8211';
  const EMAIL = 'agent-ui8b@example.com';
  const MATKHAU = 'Browser-ui8b-2026';

  const pageErrors = [], consoleErrors = [], failedRequests = [], serverErrors = [];
  page.on('pageerror',     e => pageErrors.push(e.message));
  page.on('console',       m => { if (m.type() === 'error') consoleErrors.push(m.text()); });
  page.on('requestfailed', r => failedRequests.push({url: r.url(), err: r.failure()?.errorText}));
  page.on('response',      r => { if (r.status() >= 500) serverErrors.push({url: r.url(), status: r.status()}); });

  const loi = [];
  const check = (dk, msg) => { if (!dk) loi.push(msg); };
  const soLieu = {};
  const soNode = () => page.locator('.react-flow__node').count();

  // ── Dang nhap (tai khoan fixture cua CHINH may chu thu nay) ───────────
  await page.goto(base + '/login');
  if (await page.locator('#login-username').count()) {
    await page.locator('#login-username').fill(EMAIL);
    await page.locator('#login-password').fill(MATKHAU);
    await page.locator('form button[type=submit]').click();
    await page.waitForLoadState('networkidle');
  }
  check(!page.url().includes('/login'), 'dang nhap that bai');

  // ── Ten buoc THAT tu palette (⛔ khong go cung — xem bai hoc UI-5) ─────
  const tenBuoc = await page.evaluate(async () => {
    const pal = await (await fetch('/agent/api/v3/palette',
      {credentials: 'same-origin', headers: {Accept: 'application/json'}})).json();
    const nut = pal.nhom.flatMap(n => n.nut);
    const tim = t => nut.find(n => n.type === t)?.title || '';
    return {chat: tim('app.text.chat'), anh: tim('app.image.generate')};
  });
  soLieu.tenBuoc = tenBuoc;
  check(tenBuoc.chat && tenBuoc.anh, `palette thieu app.text.chat/app.image.generate: ${JSON.stringify(tenBuoc)}`);

  // ── Dung mot canvas CO SAN mot node THU CONG (id khac AI) qua PUT thang,
  //    giong ky thuat cua agent_ui_v2_ui5_nghiem_thu.js — de diff co CA "them"
  //    LAN "xoa" khi so voi do thi AI (dinh sinh, xem may_chu.py).
  const datLaiCanvas = () => page.evaluate(async () => {
    const token = document.querySelector('#agent-canvas-root').dataset.csrfToken;
    const lay = async u => await (await fetch(u, {credentials: 'same-origin',
      headers: {Accept: 'application/json'}})).json();
    const ds = await lay('/agent/api/v3/workflows');
    const id = ds.items[0].id;
    const cur = await lay('/agent/api/v3/workflows/' + id);
    await fetch('/agent/api/v3/workflows/' + id, {method: 'PUT',
      credentials: 'same-origin',
      headers: {'Content-Type': 'application/json', 'X-CSRF-Token': token,
                'If-Match': '"' + cur.revision + '"'},
      body: JSON.stringify({csrf_token: token, document: {
        version: 3, goal: 'tạo video giới thiệu', budget_max_credit: 0,
        active_page_id: 'p1',
        pages: [{id: 'p1', name: 'Page 1', viewport: {x: 0, y: 0, zoom: 1},
                 frames: [], notes: [], comments: [],
                 nodes: [{id: 'user_n1', type: 'tool', position: {x: 40, y: 40},
                          data: {tool: 'text.chat', params: {prompt: 'ban dau'}}}],
                 edges: []}]}})});
    return id;
  });

  await page.goto(base + '/agent/canvas');
  await page.locator('#agent-canvas-root').waitFor();
  await page.waitForFunction(async () => {
    const r = await fetch('/agent/api/v3/workflows',
      {credentials: 'same-origin', headers: {Accept: 'application/json'}});
    const j = await r.json();
    return Array.isArray(j.items) && j.items.length > 0;
  }, null, {timeout: 20000});
  await datLaiCanvas();
  await page.goto(base + '/agent/canvas');
  await page.locator('#agent-canvas-root').waitFor();
  await page.locator('.react-flow__node').first().waitFor({timeout: 20000});
  check(await soNode() === 1, `canvas ban dau phai co 1 node, co ${await soNode()}`);

  const moSoan = async () => {
    // ⚠️ Nut nay la mot TOGGLE (`batNgan`) — bam khi panel DANG mo se DONG no
    // lai. moSoan() goi nhieu lan trong cung mot lan tai trang (khong reload
    // giua Huy/Escape va lan soan tiep theo), nen phai KIEM truoc khi bam.
    const nutMoNgan = page.getByRole('button', {name: 'Mở mẫu và thiết lập'});
    if ((await nutMoNgan.getAttribute('aria-pressed')) !== 'true') await nutMoNgan.click();
    const nutSoan = page.getByRole('button', {name: 'Soạn bằng AI'});
    await nutSoan.waitFor({timeout: 10000});
    check(await nutSoan.isEnabled(), 'nut "Soan bang AI" bi khoa dù đã có mục tiêu');
    const cho = page.waitForResponse(r => /\/agent\/api\/v3\/workflows\/.+\/soan$/.test(r.url())
      && r.request().method() === 'POST', {timeout: 20000});
    await nutSoan.click();
    const res = await cho;
    check(res.status() === 200, `POST .../soan: HTTP bat thuong ${res.status()}`);
    const dialog = page.getByRole('dialog', {name: 'Xem trước thay đổi từ AI'});
    await dialog.waitFor({timeout: 10000});
    return dialog;
  };

  // ── Phep do 1: XEM TRUOC hien dung dem + TEN BUOC doc duoc, KHONG id tho ─
  const dialog1 = await moSoan();
  const chuNoiDung = await dialog1.innerText();
  soLieu.textDialog1 = chuNoiDung;
  check(/\+2 bước, −1 bước/.test(chuNoiDung), `tom tat dem sai: "${chuNoiDung.split('\n')[1] || ''}"`);
  check(chuNoiDung.includes(tenBuoc.chat), `khong thay ten buoc "${tenBuoc.chat}" trong lop xem truoc`);
  check(chuNoiDung.includes(tenBuoc.anh), `khong thay ten buoc "${tenBuoc.anh}" trong lop xem truoc`);
  check(!/ai_n1|ai_n2|user_n1/.test(chuNoiDung), `id ky thuat lo ra ngoai: "${chuNoiDung}"`);
  // Dialog dang mo — canvas CHUA doi.
  check(await soNode() === 1, `Soan bang AI ghi de truoc khi Ap dung — con ${await soNode()} node`);

  // ── Phep do 2: bam "Ap dung" -> canvas doi thanh 2 node ────────────────
  await dialog1.getByRole('button', {name: 'Áp dụng'}).click();
  await page.locator('[role=dialog]').first().waitFor({state: 'detached', timeout: 10000}).catch(() => {});
  await page.waitForFunction(() => document.querySelectorAll('.react-flow__node').length === 2,
    null, {timeout: 10000}).catch(() => {});
  check(await soNode() === 2, `Ap dung khong nap document moi — con ${await soNode()} node`);

  // ── Phep do 3: dat lai canvas ve 1 node, soan lai, bam "Huỷ" ───────────
  await datLaiCanvas();
  await page.goto(base + '/agent/canvas');
  await page.locator('.react-flow__node').first().waitFor({timeout: 20000});
  const dialog2 = await moSoan();
  await dialog2.getByRole('button', {name: 'Huỷ'}).click();
  await page.waitForTimeout(300); // ⚠️ Huy la dong bo (khong mang) — cho DU de bat mot ghi de tre neu co loi.
  check(await page.locator('[role=dialog]').count() === 0, 'dialog van con sau khi Huỷ');
  check(await soNode() === 1, `🔴 Huỷ đã GHI ĐÈ canvas — còn ${await soNode()} node (đúng phải là 1)`);

  // ── Phep do 4: soan lai, nhan Escape thay vi bam nut ───────────────────
  const dialog3 = await moSoan();
  await page.keyboard.press('Escape');
  await page.waitForTimeout(300);
  check(await page.locator('[role=dialog]').count() === 0, 'dialog van con sau khi Escape');
  check(await soNode() === 1, `🔴 Escape đã GHI ĐÈ canvas — còn ${await soNode()} node (đúng phải là 1)`);
  void dialog3;

  // ── Bon so suc khoe trang ────────────────────────────────────────────
  check(pageErrors.length === 0,     'pageerror: ' + JSON.stringify(pageErrors));
  check(consoleErrors.length === 0,  'console error: ' + JSON.stringify(consoleErrors));
  check(failedRequests.length === 0, 'request hong: ' + JSON.stringify(failedRequests));
  check(serverErrors.length === 0,   '5xx: ' + JSON.stringify(serverErrors));

  if (loi.length) return {status: 'FAIL', loi, so_lieu: soLieu};
  return {status: 'PASS', so_lieu: soLieu};
}
