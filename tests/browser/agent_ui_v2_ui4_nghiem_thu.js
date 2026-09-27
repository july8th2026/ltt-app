// UI-4 nghiem thu (che do A — may chu CO LAP cong 8201).
//
// ⛔ Khong doc ma roi tuyen bo: jsdom khong tinh layout, moi
//    `getBoundingClientRect()` tra 0, nen MOI phep do chieu cao/vi tri trong
//    vitest la XANH GIA. Bon tieu chi duoi day chi do duoc o day.
//
// Moc nen do (`01_CURRENT_UI_AUDIT.md` §4, do 27/09 tren `main` sau UI-0):
//     app.video.generate  : 456 x 525 px o muc duy nhat dang co
//     ba muc mat do       : khong co
//     core.stop           : "0 nhánh"   (no KHONG co cong ra)
//     core.switch         : "1 nhánh"   LUON LUON
//
// Chay:
//     playwright-cli -s=ui4 run-code --filename=tests/browser/agent_ui_v2_ui4_nghiem_thu.js
async page => {
  const base = 'http://127.0.0.1:8201';
  const EMAIL = 'agent-ui0@example.com';
  const MATKHAU = 'Browser-ui0-2026';
  const TRAN_CAO_NORMAL = 320;

  const pageErrors = [], consoleErrors = [], failedRequests = [], serverErrors = [];
  page.on('pageerror',     e => pageErrors.push(e.message));
  page.on('console',       m => { if (m.type() === 'error') consoleErrors.push(m.text()); });
  page.on('requestfailed', r => failedRequests.push({url: r.url(), err: r.failure()?.errorText}));
  page.on('response',      r => { if (r.status() >= 500) serverErrors.push({url: r.url(), status: r.status()}); });

  const loi = [];
  const check = (dk, msg) => { if (!dk) loi.push(msg); };
  const soLieu = {};

  // 🔴 DAT KHUNG NHIN TUONG MINH — ⛔ khong nhan trang thai sot lai. Profile
  //    trinh duyet dung chung giua cac kich ban: mot kich ban mobile truoc do
  //    de lai 390px, va o be rong do `readOnly=true` nen nut "Chay" bi
  //    `disabled` => kich ban treo roi chet voi mot thong diep khong he nhac
  //    toi khung nhin.
  await page.setViewportSize({width: 1536, height: 960});

  await page.goto(base + '/login');
  if (await page.locator('#login-username').count()) {
    await page.locator('#login-username').fill(EMAIL);
    await page.locator('#login-password').fill(MATKHAU);
    await page.locator('form button[type=submit]').click();
    await page.waitForLoadState('networkidle');
  }
  check(!page.url().includes('/login'), 'dang nhap that bai');

  // `zoom` la THAM SO: mat do doi theo zoom, nen phep do phai dat duoc zoom.
  // ⭐ Dat qua `pages[0].viewport.zoom` (React Flow nhan no qua
  //    `defaultViewport`) chu ⛔ khong bam nut zoom-out N lan: mot chuoi bam
  //    cho ra mot zoom KHONG tuong minh (1/1.2^N), va phep do se noi ve mot
  //    con so khong ai viet ra.
  const datDoThi = async (nodes, edges, zoom = 1) => {
    await page.goto(base + '/agent/canvas');
    await page.locator('#agent-canvas-root').waitFor();
    await page.waitForFunction(async () => {
      const r = await fetch('/agent/api/v3/workflows',
        {credentials: 'same-origin', headers: {Accept: 'application/json'}});
      const j = await r.json();
      return Array.isArray(j.items) && j.items.length > 0;
    }, null, {timeout: 15000});
    await page.evaluate(async ({nodes, edges, zoom}) => {
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
          pages:[{id:'p1',name:'Page 1',viewport:{x:0,y:0,zoom},
                  frames:[],notes:[],comments:[], nodes, edges}]}})});
    }, {nodes, edges, zoom});
    await page.goto(base + '/agent/canvas');
    await page.locator('#agent-canvas-root').waitFor();
    if (nodes.length) {
      await page.locator('.react-flow__node').first().waitFor({timeout: 15000});
      await page.waitForTimeout(700);
    }
  };
  const nut = (id, tool, params, x = 90, y = 90) =>
    ({id, type:'tool', position:{x, y}, data:{tool, params}});

  // ⚠️ `getBoundingClientRect()` cua mot node dang o zoom z tra ve kich thuoc
  //    MAN HINH (da nhan z), khong phai kich thuoc CSS. Chia lai cho zoom, neu
  //    khong thi "node hep di" chi la "camera lui ra xa".
  const doKhung = async (nodeId) => await page.evaluate(({nodeId}) => {
    const n = nodeId ? document.querySelector(`[data-id="${nodeId}"]`)
                     : document.querySelector('.react-flow__node');
    const k = n?.querySelector('.node-khung');
    if (!k) return null;
    const vp = document.querySelector('.react-flow__viewport');
    const m = /scale\(([\d.]+)\)/.exec(vp?.style.transform || '');
    const z = m ? Number(m[1]) : 1;
    const r = k.getBoundingClientRect();
    return {
      mucDo: k.dataset.mucDo, sucKhoe: k.dataset.sucKhoe, zoom: z,
      rongCss: Math.round(r.width / z), caoCss: Math.round(r.height / z),
      rongMan: Math.round(r.width), caoMan: Math.round(r.height),
      soHang: n.querySelectorAll('.node-cong').length,
      soKhay: n.querySelectorAll('.node-khay-o').length,
      tomTat: n.querySelector('.node-mo-ta')?.textContent ?? null,
      chuTrenMat: k.innerText.replace(/\s+/g, ' ').trim().slice(0, 160),
    };
  }, {nodeId});

  // ── Phep do 1: chieu cao o muc NORMAL ───────────────────────────────────
  await datDoThi([nut('n-vid', 'video.generate', {prompt: 'x'})], [], 1);
  const normal = await doKhung('n-vid');
  soLieu.normal = normal;
  check(normal, 'khong do duoc node o muc normal');
  if (normal) {
    check(normal.mucDo === 'normal',
      `muc do o zoom 1 phai la normal, dang la ${normal.mucDo}`);
    check(normal.rongCss === 280, `rong normal ${normal.rongCss}px (cho 280)`);
    check(normal.caoCss <= TRAN_CAO_NORMAL,
      `CAO ${normal.caoCss}px > tran ${TRAN_CAO_NORMAL}px (nen do 525px)`);
    // ⛔ `app.video.generate@1` khong duoc o tren MAT node (`09 §3.2`).
    check(!normal.chuTrenMat.includes('app.video.generate@1'),
      `chuoi type@version con tren mat node: ${normal.chuTrenMat}`);
  }

  // ── Phep do 2: ba muc mat do doi TU DONG theo zoom ───────────────────────
  // 0.5 < 0.6 => compact. ⛔ Khong bam cong tac nao: khong co cong tac (Q7).
  await datDoThi([nut('n-vid', 'video.generate', {prompt: 'x'})], [], 0.5);
  const compact = await doKhung('n-vid');
  soLieu.compact = compact;
  check(compact && compact.mucDo === 'compact',
    `zoom 0.5 phai cho compact, dang la ${compact?.mucDo}`);
  check(compact && compact.rongCss === 200,
    `rong compact ${compact?.rongCss}px (cho 200)`);

  // Chon node => expanded, o CUNG zoom 1 (chon thang zoom).
  await datDoThi([nut('n-vid', 'video.generate', {prompt: 'x'})], [], 1);
  await page.locator('[data-id="n-vid"]').click({position: {x: 60, y: 8}});
  await page.waitForTimeout(400);
  const expanded = await doKhung('n-vid');
  soLieu.expanded = expanded;
  check(expanded && expanded.mucDo === 'expanded',
    `node dang chon phai la expanded, dang la ${expanded?.mucDo}`);
  check(expanded && expanded.rongCss === 360,
    `rong expanded ${expanded?.rongCss}px (cho 360)`);
  check(new Set([compact?.rongCss, normal?.rongCss, expanded?.rongCss]).size === 3,
    'ba muc KHONG cho ra ba be rong khac nhau');

  // ── Phep do 3: HAI cau node tung noi SAI (01 §4.2) ──────────────────────
  await datDoThi([
    nut('n-stop', 'core.stop', {trang_thai: 'SUCCEEDED'}, 90, 90),
    nut('n-sw', 'core.switch', {bieu_thuc: '$.x', nhanh: ['vi', 'en', 'ja', 'ko', 'zh']}, 560, 90),
    nut('n-if', 'core.if', {dieu_kien: '$.x > 1'}, 90, 420),
  ], [], 1);
  const dieuKhien = await page.evaluate(() => {
    const doc = {};
    for (const id of ['n-stop', 'n-sw', 'n-if']) {
      const n = document.querySelector(`[data-id="${id}"]`);
      doc[id] = {
        tomTat: n?.querySelector('.node-mo-ta')?.textContent ?? null,
        chu: (n?.querySelector('.node-khung')?.innerText ?? '')
          .replace(/\s+/g, ' ').trim(),
        congRa: n?.querySelectorAll('.react-flow__handle.source').length ?? -1,
      };
    }
    return doc;
  });
  soLieu.dieuKhien = dieuKhien;
  // `core.stop` KHONG co cong ra — do la ca y nghia cua no.
  check(dieuKhien['n-stop'].congRa === 0,
    `core.stop co ${dieuKhien['n-stop'].congRa} cong ra (cho 0)`);
  check(!/nhánh/.test(dieuKhien['n-stop'].chu),
    `core.stop VAN noi ve nhanh: ${JSON.stringify(dieuKhien['n-stop'])}`);
  // `core.switch` khai DUNG MOT cong ra `nhanh`; so nhanh nam o THAM SO.
  check(dieuKhien['n-sw'].congRa === 1,
    `core.switch co ${dieuKhien['n-sw'].congRa} cong ra (cho 1 — day la ca bay)`);
  check(dieuKhien['n-sw'].tomTat === '5 nhánh',
    `core.switch noi "${dieuKhien['n-sw'].tomTat}" (cho "5 nhánh")`);
  check(!/\b1 nhánh\b/.test(dieuKhien['n-sw'].chu),
    'core.switch VAN in "1 nhánh"');
  // `core.if`: chinh cac cong ra la nhanh => in TEN.
  check(/true/.test(dieuKhien['n-if'].tomTat ?? ''),
    `core.if noi "${dieuKhien['n-if'].tomTat}" (cho ten nhanh)`);

  // ── Phep do 4: 🔴 HOI QUY UI-0 — moi cong co VI TRI RIENG ────────────────
  await datDoThi([nut('n-vid', 'video.generate', {prompt: 'x'})], [], 1);
  const cong = await page.evaluate(() => {
    const n = document.querySelector('.react-flow__node');
    const hs = [...n.querySelectorAll('.react-flow__handle.target')];
    const hop = hs.map(h => h.getBoundingClientRect());
    // 🔴 Phep do THAT la `elementFromPoint`, ⛔ khong phai
    //    `getBoundingClientRect`: 27/09 ca 15 cong da co dung vi tri ma van
    //    khong keo duoc, vi NHAN KIEU (`opacity:.6` => mot stacking context,
    //    sibling dung sau trong DOM) ve DE LEN tam cong. Moi phep do toa do
    //    deu xanh trong khi khong cong nao bam duoc.
    const saiChu = [];
    hs.forEach((h, i) => {
      const r = hop[i];
      const el = document.elementFromPoint(Math.round(r.x + r.width / 2),
                                          Math.round(r.y + r.height / 2));
      const trung = el?.closest('.react-flow__handle');
      if (trung !== h) saiChu.push({
        cong: h.dataset.handleid,
        traVe: el ? `${el.tagName}.${el.className}` : null,
        traVeCong: trung?.dataset.handleid ?? null,
      });
    });
    // Vung bam do bang lop gia `::after`, ⛔ khong bang cham tron.
    const vungBam = hs.map(h => {
      const s = getComputedStyle(h, '::after');
      return Math.round(Math.min(parseFloat(s.width) || 0,
                                 parseFloat(s.height) || 0));
    });
    return {
      so: hs.length,
      viTri: new Set(hop.map(r => Math.round(r.x) + ',' + Math.round(r.y))).size,
      saiChu,
      vungBamMin: Math.min(...vungBam),
      hangVungBam: (() => {
        const hang = [...n.querySelectorAll('.node-cong-vao')];
        return hang.length
          ? Math.round(Math.min(...hang.map(h => h.getBoundingClientRect().height)))
          : 0;
      })(),
    };
  });
  soLieu.cong = cong;
  check(cong.so === 15, `cho 15 cong vao tren video.generate, thay ${cong.so}`);
  check(cong.viTri === cong.so,
    `HOI QUY P0-2: ${cong.so} cong nhung chi ${cong.viTri} vi tri khac nhau`);
  check(cong.saiChu.length === 0,
    `HOI QUY P0-2: elementFromPoint tai tam khong tra ve chinh cong: ` +
    JSON.stringify(cong.saiChu));
  check(cong.vungBamMin >= 24,
    `vung bam ${cong.vungBamMin}px < 24px (WCAG 2.2 AA 2.5.8)`);
  check(cong.hangVungBam >= 24,
    `hang cong cao ${cong.hangVungBam}px < 24px (phep do cua UI-0)`);

  // ── Phep do 5: 🔴 HOI QUY UI-0 — keo mot day HOP LE tao DUNG 1 canh ──────
  await datDoThi([
    nut('n-img', 'image.generate', {prompt: 'x'}, 90, 90),
    nut('n-vid', 'video.generate', {prompt: 'y'}, 760, 90),
  ], [], 1);
  // ⚠️ Cap kieu phai HOP LE: `image[]->image[]` CO trong `cap_noi_duoc`,
  //    `image[]->image` thi KHONG (mot mang khong rot vao mot o don). Keo cap
  //    sai kieu roi ngac nhien vi 0 canh la do VI MOT LY DO DUNG.
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
  try { await keo(raHopLe, vaoSaiKieu); } catch { /* bo qua */ }
  const sauSaiKieu = await demCanh();
  soLieu.keoDay = {raHopLe, vaoHopLe, vaoSaiKieu, sauHopLe, sauSaiKieu, keoLoi};
  check(keoLoi === null, 'keo day nem loi: ' + keoLoi);
  check(sauHopLe === '1',
    `HOI QUY: keo cap HOP LE (image[]->image[]) tao ${sauHopLe} canh (cho 1)`);
  check(sauSaiKieu === '1',
    `cap SAI KIEU (image[]->image) da lot qua: ${sauSaiKieu} canh (cho van 1)`);
  // Cong DA CO DAY phai giu NHAN o muc normal — nguoi dung khong duoc mat dau
  // soi day cua ho.
  const congDaNoi = await page.evaluate(() => {
    const e = document.querySelector(
      '[data-id="n-vid"] .react-flow__handle.target[data-handleid="image_keys"]');
    return e?.closest('.node-cong')?.className ?? null;
  });
  soLieu.congDaNoiGiuNhan = congDaNoi;
  check(!!congDaNoi && congDaNoi.includes('node-cong-vao'),
    'cong DA NOI khong con o hang co nhan: ' + congDaNoi);

  // ── Bon so suc khoe trang ───────────────────────────────────────────────
  check(pageErrors.length === 0,     'pageerror: ' + JSON.stringify(pageErrors));
  check(consoleErrors.length === 0,  'console error: ' + JSON.stringify(consoleErrors));
  check(failedRequests.length === 0, 'request hong: ' + JSON.stringify(failedRequests));
  check(serverErrors.length === 0,   '5xx: ' + JSON.stringify(serverErrors));

  if (loi.length) return {status: 'FAIL', loi, so_lieu: soLieu};
  return {status: 'PASS', so_lieu: soLieu};
}
