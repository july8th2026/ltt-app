// UI-3 nghiem thu (che do A — may chu CO LAP).
//
// ⭐ VI SAO PHA NAY CAN TRINH DUYET du no chi la mot lan DI CHUYEN:
//
//    165 phep kiem vitest xanh chung minh HANH VI con nguyen, nhung chung chay
//    trong jsdom — khong layout, khong CSS. Sau khi tach 11 khu JSX ra 16 tep,
//    cach hong DAC TRUNG khong phai "mot ham sai" ma la "mot phan tu ra khoi
//    dung cha cua no": `.canvas-palette` roi ra ngoai `.canvas-body`, ngan keo
//    chay o ngoai `.canvas-toolbar`. jsdom van xanh (vai tro aria khong doi),
//    con nguoi dung thi thay mot man hinh vo.
//
//    Nen cac phep do duoi day do CAY DOM va TOA DO THAT — dung thu ma vitest
//    khong the do.
//
// Chay:
//   playwright-cli -s=ui3 run-code --filename=tests/browser/agent_ui_v2_ui3_nghiem_thu.js
//
// ⚠️ Cong 8197, KHONG 8198: che do A cua plan ghi 8198, nhung mot lan khac dang
//    giu cong ay (mot may chu UI-0 cua phien khac). Moi lan mot cong rieng —
//    ⛔ khong giet tien trinh cua lan khac de doi lay mot con so cho dep.
// ⛔ `process` KHONG ton tai trong hop cat cua `run-code`, nen base go thang.
async page => {
  const base = 'http://127.0.0.1:8197';
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
  await page.goto(base + '/login');
  if (await page.locator('#login-username').count()) {
    await page.locator('#login-username').fill(EMAIL);
    await page.locator('#login-password').fill(MATKHAU);
    await page.locator('form button[type=submit]').click();
    await page.waitForLoadState('networkidle');
  }
  check(!page.url().includes('/login'), 'dang nhap that bai');

  const nut = (id, tool, params, x = 90, y = 90) =>
    ({id, type:'tool', position:{x, y}, data:{tool, params}});

  const datDoThi = async (nodes, edges) => {
    await page.goto(base + '/agent/canvas');
    await page.locator('#agent-canvas-root').waitFor();
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
    if (nodes.length) {
      await page.locator('.react-flow__node').first().waitFor({timeout: 15000});
      await page.waitForTimeout(700);
    }
  };

  // ── Phep do 1: CAY DOM dung hinh — 11 khu ve o DUNG cha cua no ────────
  //
  // Day la phep do CHOT cua pha tach. Moi cap duoi day la mot quan he cha-con
  // ma `canvas.css` (lan UI-2 so huu) dang dua vao de dinh vi. Mot khu roi ra
  // khoi cha cua no thi vitest van xanh va man hinh thi vo.
  await datDoThi([nut('n1', 'text.chat', {prompt: 'xin chao'})], []);
  const cay = await page.evaluate(() => {
    const co = s => !!document.querySelector(s);
    return {
      shell:        co('section.canvas-shell'),
      toolbar:      co('section.canvas-shell > header.canvas-toolbar'),
      // Ngan keo chay PHAI o trong thanh cong cu (no la con cua <header>).
      drawerTrongToolbar: co('header.canvas-toolbar > nav.operation-drawer'),
      mobileTabs:   co('section.canvas-shell > nav.canvas-mobile-tabs'),
      body:         co('section.canvas-shell > div.canvas-body'),
      rail:         co('div.canvas-body > nav.canvas-rail'),
      palette:      co('div.canvas-body > aside.canvas-palette'),
      stage:        co('div.canvas-body > section.canvas-stage'),
      pageDock:     co('div.canvas-body > nav.page-dock'),
      reactFlow:    co('section.canvas-stage > div.react-flow'),
      // Ba khu con cua ngan trai.
      pagePanel:    co('aside.canvas-palette > section.page-panel'),
      organize:     co('aside.canvas-palette > section.organize-panel'),
      settings:     co('aside.canvas-palette > div.workflow-settings'),
      soNode:       document.querySelectorAll('.react-flow__node').length,
    };
  });
  soLieu.cayDOM = cay;
  for (const [k, v] of Object.entries(cay)) {
    if (k === 'soNode') continue;
    check(v === true, `cay DOM vo: thieu/sai cha o "${k}"`);
  }
  check(cay.soNode === 1, `ve ${cay.soNode} node (cho 1)`);

  // ── Phep do 2: bo cuc THAT — ba cot khong de len nhau, node nhin thay ──
  //
  // jsdom tra 0 cho moi getBoundingClientRect, nen day la phep do ma vitest
  // KHONG THE lam: ngan trai phai nam BEN TRAI khung ve, va node phai co
  // kich thuoc that.
  // ⚠️ ⛔ KHONG do bang "rail.x < stage.x". Ban dau bai nay khang dinh the va
  //    DO — nhung loi o PHEP DO, khong o ma: `canvas.css:112` dat
  //    `.canvas-rail { position:absolute; left:14px; z-index:20 }` va
  //    `.canvas-stage` trai HET be rong (x=0). Thanh doc NAM DE LEN khung ve
  //    theo dung thiet ke. Do "ben trai" la do mot quan he chua bao gio ton tai.
  //
  //    Thu DANG do la: thanh doc co NHIN THAY va co BAM DUOC — tuc no nam TREN
  //    khung ve trong thu tu z. Mot phan tu dung cha nhung bi khung ve phu len
  //    thi vitest van xanh va nguoi dung khong bam duoc nut nao.
  const boCuc = await page.evaluate(() => {
    const r = s => { const e = document.querySelector(s); return e ? e.getBoundingClientRect() : null; };
    const rail = r('nav.canvas-rail'), stage = r('section.canvas-stage'), node = r('.react-flow__node');
    // Bam thu vao GIUA nut dau tien cua thanh doc: phan tu o diem do phai la
    // chinh nut ay (hoac con cua thanh doc), khong phai khung ve.
    const nutDau = document.querySelector('nav.canvas-rail button');
    let chuDiem = null;
    if (nutDau) {
      const b = nutDau.getBoundingClientRect();
      const tren = document.elementFromPoint(b.x + b.width / 2, b.y + b.height / 2);
      chuDiem = tren ? (tren.closest('nav.canvas-rail') ? 'canvas-rail' : tren.className || tren.tagName) : null;
    }
    return {
      rail:  rail  && {x: Math.round(rail.x),  w: Math.round(rail.width),  h: Math.round(rail.height)},
      stage: stage && {x: Math.round(stage.x), w: Math.round(stage.width), h: Math.round(stage.height)},
      node:  node  && {w: Math.round(node.width), h: Math.round(node.height)},
      chuDiem,
    };
  });
  soLieu.boCuc = boCuc;
  check(!!(boCuc.rail && boCuc.stage && boCuc.node), 'khong do duoc bo cuc');
  if (boCuc.rail && boCuc.stage && boCuc.node) {
    check(boCuc.rail.w > 0 && boCuc.rail.h > 0, 'thanh doc co kich thuoc 0');
    check(boCuc.stage.w > 200 && boCuc.stage.h > 200,
          `khung ve qua nho: ${boCuc.stage.w}x${boCuc.stage.h}`);
    check(boCuc.chuDiem === 'canvas-rail',
          `nut o thanh doc bi phu len: diem giua no thuoc "${boCuc.chuDiem}"`);
    check(boCuc.node.w > 100 && boCuc.node.h > 40,
          `node ve ra kich thuoc sai: ${boCuc.node.w}x${boCuc.node.h}`);
  }

  // ── Phep do 3: Inspector mo duoc bang CA HAI duong, va sinh form ───────
  //
  // Nut "☰" o thanh doc la DUONG VAO DUY NHAT tren desktop; bam vao node la
  // duong thu hai. Ca hai di qua `chonNode`/`batNgan` moi tach ra.
  await page.locator('.react-flow__node').first().click();
  await page.waitForTimeout(400);
  const insp = await page.evaluate(() => {
    const el = document.querySelector('aside.canvas-inspector');
    if (!el) return null;
    const r = el.getBoundingClientRect();
    return {
      moRong: el.className.includes('is-open'),
      hienThi: r.width > 50 && r.height > 50,
      coOThamSo: !!el.querySelector('input, textarea, select'),
      tieuDe: el.querySelector('h2')?.textContent ?? null,
    };
  });
  soLieu.inspector = insp;
  check(!!insp, 'bam node KHONG mo inspector');
  if (insp) {
    check(insp.moRong, 'inspector khong mang lop is-open');
    check(insp.hienThi, 'inspector co lop is-open nhung KHONG nhin thay');
    check(insp.coOThamSo, 'inspector mo nhung khong sinh o tham so nao');
  }

  // ── Phep do 4: phai chuot tren node KHONG mo inspector ────────────────
  //
  // Mot trong ba cho suyt mat hanh vi luc tach: dung lai ham cua bam-trai cho
  // `onNodeContextMenu` lam ngan phai bat ra. Do o day vi no chi thay duoc
  // tren man hinh that.
  await page.goto(base + '/agent/canvas');
  await page.locator('.react-flow__node').first().waitFor({timeout: 15000});
  await page.waitForTimeout(600);
  await page.locator('.react-flow__node').first().click({button: 'right'});
  await page.waitForTimeout(400);
  const sauPhaiChuot = await page.evaluate(() => ({
    menu: !!document.querySelector('aside.canvas-context-menu'),
    inspectorMo: !!document.querySelector('aside.canvas-inspector.is-open'),
  }));
  soLieu.phaiChuot = sauPhaiChuot;
  check(sauPhaiChuot.menu, 'phai chuot tren node khong mo menu ngu canh');
  check(!sauPhaiChuot.inspectorMo,
        'HOI QUY: phai chuot tren node da mo luon inspector (ban goc khong the)');

  // ── Phep do 5: bang lenh Ctrl+K va Escape ─────────────────────────────
  await page.keyboard.press('Escape');
  await page.waitForTimeout(200);
  await page.keyboard.press('Control+k');
  await page.waitForTimeout(400);
  const bangLenh = await page.evaluate(() => {
    const el = document.querySelector('section.command-palette');
    if (!el) return null;
    return {so: el.querySelectorAll('div > button').length,
            coOTim: !!el.querySelector('input[aria-label]')};
  });
  soLieu.bangLenh = bangLenh;
  check(!!bangLenh, 'Ctrl+K khong mo bang lenh');
  check(bangLenh && bangLenh.so === 7, `bang lenh co ${bangLenh?.so} lenh (cho 7)`);
  await page.keyboard.press('Escape');
  await page.waitForTimeout(300);
  check(!(await page.locator('section.command-palette').count()),
        'Escape khong dong bang lenh');

  // ── Phep do 6: autosave THAT bay di sau ~800ms (do qua mang) ───────────
  //
  // ⭐ Day la phep do dac ta autosave tren duong THAT: vitest do mot `fetch`
  //    bi mock, o day la mot request PUT co that qua mang toi may chu co that.
  await page.locator('button[aria-label="Mở mẫu và thiết lập"]').click();
  await page.waitForTimeout(300);
  const soPut = [];
  page.on('request', r => {
    if (r.method() === 'PUT' && r.url().includes('/agent/api/v3/workflows/'))
      soPut.push(Date.now());
  });
  const oMucTieu = page.locator('textarea');
  await oMucTieu.first().fill('muc tieu do boi UI-3');
  await page.waitForTimeout(400);
  const putSau400 = soPut.length;
  await page.waitForTimeout(1400);
  const putSau1800 = soPut.length;
  soLieu.autosave = {putSau400, putSau1800};
  check(putSau400 === 0, `autosave bay QUA SOM: ${putSau400} PUT trong 400ms`);
  check(putSau1800 === 1, `sau 1,8s co ${putSau1800} PUT (cho dung 1)`);

  // ── Phep do 7: Hoan tac SONG sau khi sua (lich su khong bi xoa) ────────
  const hoanTac = await page.evaluate(() => {
    const b = document.querySelector('button[aria-label="Hoàn tác"]');
    return b ? {co: true, batDuoc: !b.disabled} : {co: false};
  });
  soLieu.hoanTac = hoanTac;
  check(hoanTac.co, 'khong thay nut Hoan tac');
  check(hoanTac.batDuoc, 'sua roi ma nut Hoan tac van chet — lich su bi xoa');

  // ── Bon so suc khoe trang ─────────────────────────────────────────────
  check(pageErrors.length === 0,     'pageerror: ' + JSON.stringify(pageErrors));
  check(consoleErrors.length === 0,  'console error: ' + JSON.stringify(consoleErrors));
  check(failedRequests.length === 0, 'request hong: ' + JSON.stringify(failedRequests));
  check(serverErrors.length === 0,   '5xx: ' + JSON.stringify(serverErrors));

  if (loi.length) return {status: 'FAIL', loi, so_lieu: soLieu};
  return {status: 'PASS', so_lieu: soLieu};
}
