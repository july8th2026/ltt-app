// UI-0 + UI-N chot tren WEB THAT (che do B).
//
// CLAUDE.md luat 7: chot tren `https://app.lttstudios.com`, ⛔ KHONG chot tren
// loopback — loopback bo qua Cloudflare, va Cloudflare da tung la thu pham that
// (asset thu thach chi co AAAA, may khong IPv6).
//
// Dang nhap bang COOKIE tu `tools/tai_khoan_thu.py --cookie`, ⛔ khong go mat
// khau vao form. Tai khoan duoi `.local`, ⛔ khong phai khach that.
//
// ## Vi sao can kich ban NAY khi da co kich ban 8198
//
// `agent_ui_v2_ui0_nghiem_thu.js` (che do A) chung minh MA MOI dung. No ⛔ KHONG
// chung minh BAN DEPLOY dung: bundle co duoc build lai khong, Cloudflare co
// phuc vu dung tep khong. Hai cau hoi khac nhau, can hai phep do.
//
// ⚠️ Neu phep do o day DO ma che do A da XANH => ⛔ khong phai loi ma, ma la loi
//    DUONG DEPLOY. Kiem theo DUNG thu tu: (1) bundle da build lai chua,
//    (2) `git archive` co mang dung SHA khong, (3) Cloudflare con phuc vu ban cu.
//
// ## Chay
//     # Buoc 1 — lay cookie (can Administrator de doc app.env):
//     python tools\nang_quyen.py --lenh "C:\LTTPlatform\venv\Scripts\python.exe ^
//       tools\tai_khoan_thu.py --app-env C:\LTTPlatform\secrets\app.env ^
//       --cookie khach1.thu@lttstudios.local"
//     # -> session=<gia tri>   ==> dat vao bien moi truong LTT_COOKIE_THU
//     # Buoc 2:
//     playwright-cli -s=ui0 run-code --filename=tests/browser/agent_ui_v2_ui0_web_that.js
async page => {
  // ⚠️ `process.env` KHONG dung duoc o day: playwright-cli chay ham nay trong
  //    mot hop cat, khong phai tien trinh node — `process is not defined`.
  //    Nen cookie di vao bang DAU THAY THE, do `tools/chay_web_that.py` dien
  //    vao mot BAN SAO trong scratchpad ngay truoc khi chay.
  // ⛔ Tep NAY (trong kho) khong bao gio chua cookie that.
  const COOKIE = '__LTT_COOKIE__';
  if (!COOKIE || COOKIE.startsWith('__LTT_'))
    throw new Error('chua dien cookie — chay qua `python tools/chay_web_that.py`');

  const pageErrors = [], consoleErrors = [], failedRequests = [], serverErrors = [];
  page.on('pageerror',     e => pageErrors.push(e.message));
  page.on('console',       m => { if (m.type() === 'error') consoleErrors.push(m.text()); });
  page.on('requestfailed', r => failedRequests.push({url: r.url(), err: r.failure()?.errorText}));
  page.on('response',      r => { if (r.status() >= 500) serverErrors.push({url: r.url(), status: r.status()}); });

  await page.context().addCookies([{ name: 'session', value: COOKIE,
    domain: 'app.lttstudios.com', path: '/', secure: true, httpOnly: true }]);

  const loi = [];
  const check = (dk, msg) => { if (!dk) loi.push(msg); };
  const soLieu = {};

  await page.goto('https://app.lttstudios.com/agent/canvas');
  check(!page.url().includes('/login'),
        'cookie het hieu luc — lay lai bang tai_khoan_thu.py --cookie');
  await page.locator('#agent-canvas-root').waitFor({timeout: 20000});

  // ── Phep do 1 (UI-N): nhan node LTT_APPS ĐOC DUOC, khong bi cat ────────
  // Doc thang tu palette — day la thu KHACH THAT nhin thay.
  const nhan = await page.evaluate(async () => {
    const r = await fetch('/agent/api/v3/palette',
      {credentials: 'same-origin', headers: {Accept: 'application/json'}});
    const j = await r.json();
    const app = (j.nhom.find(n => n.category === 'LTT_APPS') || {}).nut || [];
    return {
      tong: app.length,
      qua40: app.filter(x => x.title.length > 40).map(x => x.type),
      catGiuaTu: app.filter(x => x.title.length === 60).map(x => x.type),
      vaiTen: app.slice(0, 4).map(x => `${x.title} (${x.title.length})`),
    };
  });
  soLieu.nhan = nhan;
  check(nhan.tong > 0, 'palette khong tra node LTT_APPS nao');
  check(nhan.qua40.length === 0,
        `UI-N chua len production: ${nhan.qua40.length} nhan > 40 ky tu — ${nhan.qua40}`);
  check(nhan.catGiuaTu.length === 0,
        `van con nhan cat cung o 60 ky tu: ${nhan.catGiuaTu}`);

  // ── Phep do 2 (UI-0): cong noi co vi tri RIENG, va BAM duoc ────────────
  // ⚠️ `getBoundingClientRect` MOT MINH khong du: ban dau 15 cong / 15 vi tri
  //    van XANH trong khi KHONG keo duoc, vi nhan kieu de len cong. Phep do
  //    that la `elementFromPoint` tai TAM cong.
  const csrf = await page.evaluate(() =>
    document.querySelector('#agent-canvas-root').dataset.csrfToken);
  await page.evaluate(async (csrf) => {
    const ds = await (await fetch('/agent/api/v3/workflows',
      {credentials:'same-origin',headers:{Accept:'application/json'}})).json();
    if (!ds.items || !ds.items.length) return;
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
                frames:[],notes:[],comments:[],
                nodes:[{id:'n-vid',type:'tool',position:{x:90,y:90},
                        data:{tool:'video.generate',params:{prompt:'kiem UI-0'}}}],
                edges:[]}]}})});
  }, csrf);
  await page.goto('https://app.lttstudios.com/agent/canvas');
  await page.locator('.react-flow__node').first().waitFor({timeout: 20000});
  await page.waitForTimeout(900);

  const cong = await page.evaluate(() => {
    const n = document.querySelector('.react-flow__node');
    if (!n) return null;
    const hs = [...n.querySelectorAll('.react-flow__handle.target')];
    const viTri = new Set(hs.map(h => {
      const r = h.getBoundingClientRect();
      return Math.round(r.x) + ',' + Math.round(r.y);
    }));
    // Phep do THAT: tai tam moi cong, elementFromPoint co tra ve CHINH no khong.
    let dungCong = 0;
    for (const h of hs) {
      const r = h.getBoundingClientRect();
      const e = document.elementFromPoint(r.x + r.width / 2, r.y + r.height / 2);
      if (e && e.getAttribute('data-handleid') === h.getAttribute('data-handleid'))
        dungCong += 1;
    }
    const hang = [...n.querySelectorAll('.node-cong-vao')];
    return {so: hs.length, viTri: viTri.size, bamDuoc: dungCong,
            vungBam: hang.length
              ? Math.round(Math.min(...hang.map(x => x.getBoundingClientRect().height)))
              : 0};
  });
  soLieu.cong = cong;
  check(cong && cong.so > 1, 'khong lay duoc node nhieu cong de do');
  if (cong && cong.so > 1) {
    check(cong.viTri === cong.so,
      `ban DEPLOY chua mang ban va cong: ${cong.so} cong / ${cong.viTri} vi tri`);
    check(cong.bamDuoc === cong.so,
      `${cong.so - cong.bamDuoc}/${cong.so} cong bi che (elementFromPoint tra thu khac)`);
    check(cong.vungBam >= 24, `vung bam ${cong.vungBam}px < 24px (WCAG 2.2 AA)`);
  }

  // ── Phep do 3 (UI-0): khong con nut '+' chet ───────────────────────────
  soLieu.nutChenChet = await page.evaluate(() =>
    document.querySelectorAll('.edge-insert').length);
  check(soLieu.nutChenChet === 0, `nut '+' chet van con: ${soLieu.nutChenChet}`);

  // ── Bon so suc khoe trang ─────────────────────────────────────────────
  check(pageErrors.length === 0,     'pageerror: ' + JSON.stringify(pageErrors));
  check(consoleErrors.length === 0,  'console error: ' + JSON.stringify(consoleErrors));
  check(failedRequests.length === 0, 'request hong: ' + JSON.stringify(failedRequests));
  check(serverErrors.length === 0,   '5xx: ' + JSON.stringify(serverErrors));

  if (loi.length) return {status: 'FAIL', loi, so_lieu: soLieu};
  return {status: 'PASS', so_lieu: soLieu};
}
