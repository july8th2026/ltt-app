// UI-0 nghiem thu (che do A — may chu CO LAP cong 8198).
//
// ⛔ Khong doc ma roi tuyen bo da sua: BA trong BON loi cua pha nay chi lo ra
//    tren LAYOUT THAT. jsdom khong tinh layout, moi getBoundingClientRect() tra
//    0, nen mot phep so toa do trong vitest se XANH GIA.
//
// Moc nen do 27/09/2026 (truoc ban va):
//     bam MOT the core.set -> Chay  => "node_khong_ton_tai: core.set"
//     app.video.generate            => 15 cong / 1 vi tri, moi cong 6x6px
//     keo day image_keys->image_key => 0 canh, im lang
//     nut '+' chen buoc             => 2 nut, bam khong lam gi
//
// Chay:
//     playwright-cli -s=ui0 run-code --filename=tests/browser/agent_ui_v2_ui0_nghiem_thu.js
async page => {
  const base = 'http://127.0.0.1:8198';
  const EMAIL = 'agent-ui0@example.com';
  const MATKHAU = 'Browser-ui0-2026';

  const pageErrors = [], consoleErrors = [], failedRequests = [], serverErrors = [];
  page.on('pageerror',     e => pageErrors.push(e.message));
  page.on('console',       m => { if (m.type() === 'error') consoleErrors.push(m.text()); });
  page.on('requestfailed', r => failedRequests.push({url: r.url(), err: r.failure()?.errorText}));
  page.on('response',      r => { if (r.status() >= 500) serverErrors.push({url: r.url(), status: r.status()}); });

  const loi = [];
  const check = (dk, msg) => { if (!dk) loi.push(msg); };
  const soLieu = {};

  // ── Dang nhap (tai khoan fixture cua CHINH may chu thu nay) ───────────
  // ⚠️ Chay lai kich ban tren CUNG mot profile trinh duyet thi cookie phien
  //    truoc con song, va `/login` chuyen huong ngay => khong co `#login-username`.
  //    Nen dang nhap CO DIEU KIEN, ⛔ khong gia dinh luon thay form.
  await page.goto(base + '/login');
  if (await page.locator('#login-username').count()) {
    await page.locator('#login-username').fill(EMAIL);
    await page.locator('#login-password').fill(MATKHAU);
    await page.locator('form button[type=submit]').click();
    await page.waitForLoadState('networkidle');
  }
  check(!page.url().includes('/login'), 'dang nhap that bai');

  // Dat lai do thi ve RONG truoc moi phep do => chay lai script bao nhieu lan
  // cung bat dau tu cung mot trang thai.
  const datDoThi = async (nodes, edges) => {
    await page.goto(base + '/agent/canvas');
    await page.locator('#agent-canvas-root').waitFor();
    // ⚠️ Canvas tao workflow dau tien BAT DONG BO sau khi nap
    //    (`loadOrCreateWorkflowV3`: liet ke truoc, POST neu rong). Doc
    //    `items[0]` ngay sau `waitFor()` la doc mot mang RONG.
    await page.waitForFunction(async () => {
      const r = await fetch('/agent/api/v3/workflows',
        {credentials: 'same-origin', headers: {Accept: 'application/json'}});
      const j = await r.json();
      return Array.isArray(j.items) && j.items.length > 0;
    }, null, {timeout: 15000});
    await page.evaluate(async ({nodes, edges}) => {
      const csrf = document.querySelector('#agent-canvas-root').dataset.csrfToken;
      const ds = await (await fetch('/agent/api/v3/workflows',
        {credentials:'same-origin',headers:{Accept:'application/json'}})).json();
      const id = ds.items[0].id;
      const cur = await (await fetch('/agent/api/v3/workflows/' + id,
        {credentials:'same-origin',headers:{Accept:'application/json'}})).json();
      await fetch('/agent/api/v3/workflows/' + id, {method:'PUT',
        credentials:'same-origin',
        headers:{'Content-Type':'application/json','X-CSRF-Token':csrf,
                 'If-Match':'"' + cur.revision + '"'},
        body: JSON.stringify({csrf_token: csrf, document:{
          version:3, goal:'', budget_max_credit:0, active_page_id:'p1',
          pages:[{id:'p1',name:'Page 1',viewport:{x:0,y:0,zoom:1},
                  frames:[],notes:[],comments:[], nodes, edges}]}})});
    }, {nodes, edges});
    await page.goto(base + '/agent/canvas');
    await page.locator('#agent-canvas-root').waitFor();
    // ⚠️ `#agent-canvas-root` co MAT truoc khi React ve xong node. Do ngay sau
    //    no la do mot canvas RONG — bang chung cua ban dau: `cong: null`.
    if (nodes.length) {
      await page.locator('.react-flow__node').first().waitFor({timeout: 15000});
      await page.waitForTimeout(700);   // de React Flow do xong kich thuoc
    }
  };
  const nut = (id, tool, params, x = 90, y = 90) =>
    ({id, type:'tool', position:{x, y}, data:{tool, params}});

  // ── Phep do 1: node core.* tu palette BIEN DICH duoc ──────────────────
  await datDoThi([nut('n-set', 'core.set', {bien: {}})], []);
  await page.locator('button.run-primary').click();
  await page.locator('button.run-confirm').click();
  await page.waitForTimeout(2500);
  const loiChay = await page.evaluate(() =>
    document.querySelector('.run-error')?.textContent ?? null);
  soLieu.loiChayCoreSet = loiChay;
  check(!(loiChay || '').includes('node_khong_ton_tai'),
        'P0-1 CHUA SUA (core.set): ' + loiChay);

  // ── Phep do 2: cong noi co vi tri KHAC NHAU + vung bam >= 24px ────────
  await datDoThi([nut('n-vid', 'video.generate', {prompt: 'x'})], []);
  const cong = await page.evaluate(() => {
    const n = document.querySelector('.react-flow__node');
    if (!n) return null;
    const hs = [...n.querySelectorAll('.react-flow__handle.target')];
    const hop = hs.map(h => h.getBoundingClientRect());
    const hang = [...n.querySelectorAll('.node-cong-vao')];
    return {
      so: hs.length,
      viTri: new Set(hop.map(r => Math.round(r.x) + ',' + Math.round(r.y))).size,
      // Vung BAM do bang lop gia `::after`, khong bang chinh cham tron.
      vungBam: hang.length
        ? Math.round(Math.min(...hang.map(h => h.getBoundingClientRect().height)))
        : 0,
    };
  });
  soLieu.cong = cong;
  check(cong && cong.so > 1, 'khong lay duoc node nhieu cong de do');
  if (cong && cong.so > 1) {
    check(cong.viTri === cong.so,
      `P0-2 CHUA SUA: ${cong.so} cong nhung chi ${cong.viTri} vi tri khac nhau`);
    check(cong.vungBam >= 24,
      `vung bam ${cong.vungBam}px < 24px (WCAG 2.2 AA 2.5.8)`);
  }

  // ── Phep do 3: KEO DAY tao ra mot canh THAT ───────────────────────────
  await datDoThi([
    nut('n-img', 'image.generate', {prompt: 'x'}, 90, 90),
    nut('n-vid', 'video.generate', {prompt: 'y'}, 760, 90),
  ], []);
  // ⚠️ Cap kieu phai HOP LE, neu khong phep do nay do vi mot ly do DUNG.
  //    Do tu `/agent/api/v3/palette`: `image[]->image` KHONG co trong
  //    `cap_noi_duoc` (mot mang khong rot vao mot o don), `image[]->image[]`
  //    thi CO. Ban dau kich ban keo `image_keys -> image_key` va nhan 0 canh —
  //    do la he thong tu choi ĐÚNG, khong phai mot con bo.
  const tam = async (nid, hid, loai) => await page.evaluate(
    ({nid, hid, loai}) => {
      const e = document.querySelector(
        `[data-id="${nid}"] .react-flow__handle.${loai}[data-handleid="${hid}"]`);
      if (!e) return null;
      const r = e.getBoundingClientRect();
      return {x: Math.round(r.x + r.width / 2), y: Math.round(r.y + r.height / 2)};
    }, {nid, hid, loai});

  const keo = async (tu, den) => {
    await page.mouse.move(tu.x, tu.y);
    await page.mouse.down();
    await page.mouse.move(tu.x + 40, tu.y + 10, {steps: 6});
    await page.mouse.move(den.x, den.y, {steps: 14});
    await page.mouse.move(den.x, den.y, {steps: 3});
    await page.mouse.up();
    await page.waitForTimeout(800);
  };
  const demCanh = async () => await page.evaluate(() =>
    document.querySelector('.canvas-stage')?.getAttribute('data-edge-count'));

  const raHopLe = await tam('n-img', 'image_keys', 'source');
  const vaoHopLe = await tam('n-vid', 'image_keys', 'target');
  const vaoSaiKieu = await tam('n-vid', 'image_key', 'target');
  check(raHopLe && vaoHopLe && vaoSaiKieu, 'khong dinh vi duoc ba cong can do');

  let keoLoi = null;
  try { await keo(raHopLe, vaoHopLe); } catch (e) { keoLoi = String(e).slice(0, 400); }
  const sauHopLe = await demCanh();

  // Cap SAI KIEU phai bi tu choi — kiem tra ta khong lam thung he kieu.
  try { await keo(raHopLe, vaoSaiKieu); } catch { /* bo qua */ }
  const sauSaiKieu = await demCanh();

  soLieu.keoDay = {sauHopLe, sauSaiKieu, keoLoi};
  check(keoLoi === null, 'keo day nem loi: ' + keoLoi);
  check(sauHopLe === '1',
        `P0-2 keo cap HOP LE (image[]->image[]) tao ${sauHopLe} canh (cho 1)`);
  check(sauSaiKieu === '1',
        `cap SAI KIEU (image[]->image) da lot qua: ${sauSaiKieu} canh (cho van 1)`);

  // ── Phep do 4: khong con nut '+' chet tren canh ───────────────────────
  const nutChet = await page.evaluate(() =>
    document.querySelectorAll('.edge-insert').length);
  soLieu.nutChenChet = nutChet;
  check(nutChet === 0, `nut '+' chet van con: ${nutChet}`);

  // ── Bon so suc khoe trang ─────────────────────────────────────────────
  check(pageErrors.length === 0,     'pageerror: ' + JSON.stringify(pageErrors));
  check(consoleErrors.length === 0,  'console error: ' + JSON.stringify(consoleErrors));
  check(failedRequests.length === 0, 'request hong: ' + JSON.stringify(failedRequests));
  check(serverErrors.length === 0,   '5xx: ' + JSON.stringify(serverErrors));

  if (loi.length) return {status: 'FAIL', loi, so_lieu: soLieu};
  return {status: 'PASS', so_lieu: soLieu};
}
