// UI-2 nghiem thu (che do A -- may chu CO LAP cong 8198, dung chung khuon voi
// UI-0: tests/browser/agent_ui_v2_ui0_may_chu.py).
//
// Kiem BON viec cua lan UI-2 tren layout THAT:
//   1. Luoi hoi quy UI-0: cong app.video.generate van 15 cong / 15 vi tri KHAC
//      NHAU, va elementFromPoint tai TAM cong tra ve CHINH cong (khong phai nhan).
//   2. theme-light: 0/11 o form con giu nen TOI.
//   3. minimap + controls: do tuong phan be mat thuc te (khong tuyen bo suong).
//   4. Bon so suc khoe trang (pageerror/console/request hong/5xx).
//
// Chay: playwright-cli -s=ui2 run-code --filename=tests/browser/agent_ui_v2_ui2_nghiem_thu.js
async page => {
  const base = 'http://127.0.0.1:8198';
  const EMAIL = 'agent-ui0@example.com';
  const MATKHAU = 'Browser-ui0-2026';

  await page.setViewportSize({ width: 1600, height: 1300 });

  const pageErrors = [], consoleErrors = [], failedRequests = [], serverErrors = [];
  page.on('pageerror',     e => pageErrors.push(e.message));
  page.on('console',       m => { if (m.type() === 'error') consoleErrors.push(m.text()); });
  page.on('requestfailed', r => failedRequests.push({url: r.url(), err: r.failure()?.errorText}));
  page.on('response',      r => { if (r.status() >= 500) serverErrors.push({url: r.url(), status: r.status()}); });

  const loi = [];
  const check = (dk, msg) => { if (!dk) loi.push(msg); };
  const soLieu = {};

  await page.goto(base + '/login');
  if (await page.locator('#login-username').count()) {
    await page.locator('#login-username').fill(EMAIL);
    await page.locator('#login-password').fill(MATKHAU);
    await page.locator('form button[type=submit]').click();
    await page.waitForLoadState('networkidle');
  }
  check(!page.url().includes('/login'), 'dang nhap that bai');

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
  const nut = (id, tool, params, x = 300, y = 200) =>
    ({id, type:'tool', position:{x, y}, data:{tool, params}});

  // ── Phep do 1: luoi hoi quy UI-0 (mot minh app.video.generate, 15 cong) ──
  await datDoThi([nut('n-vid', 'video.generate', {prompt: 'x'})], []);
  // Cuon TUNG cong vao giua man hinh truoc khi do — node co the cao hon
  // viewport (video.generate co 16 cong hom nay, khong con dung 15 nhu
  // 27/09), nen cong o day node se ngoai man hinh neu khong cuon toi.
  const congInfo = await page.evaluate(async () => {
    const n = document.querySelector('.react-flow__node');
    if (!n) return null;
    const handles = [...n.querySelectorAll('.react-flow__handle')];
    const tamDiem = [];
    for (const h of handles) {
      h.scrollIntoView({ block: 'center', inline: 'center' });
      const r = h.getBoundingClientRect();
      const cx = Math.round(r.x + r.width / 2), cy = Math.round(r.y + r.height / 2);
      const el = document.elementFromPoint(cx, cy);
      const trungCong = !!(el && el.closest && el.closest('.react-flow__handle') === h);
      tamDiem.push({ handleid: h.getAttribute('data-handleid'), x: r.x, y: r.y,
                     trungCong, elClass: el ? (el.className?.baseVal ?? el.className) : null });
    }
    const viTri = new Set(tamDiem.map(t => Math.round(t.x) + ',' + Math.round(t.y)));
    return { soCong: handles.length, soViTri: viTri.size, tamDiem };
  });
  soLieu.congInfo = congInfo;
  check(!!congInfo, 'khong tim thay node video.generate de do');
  if (congInfo) {
    check(congInfo.soCong >= 10, `app.video.generate co qua it cong: ${congInfo.soCong}`);
    check(congInfo.soViTri === congInfo.soCong,
      `P0-2 hoi quy: ${congInfo.soCong} cong nhung chi ${congInfo.soViTri} vi tri khac nhau`);
    const saiTam = congInfo.tamDiem.filter(t => !t.trungCong);
    check(saiTam.length === 0,
      `z-index hoi quy: elementFromPoint tai tam cong tra ve NHAN thay vi CONG o: ` +
      JSON.stringify(saiTam));
  }

  // ── Phep do 2: theme sang -- dem o form con giu nen TOI ──────────────────
  // ⚠️ Theme la mot preference LUU O SERVER (savePreferences) — tai khoan
  //    fixture nay co the da o theme-light tu lan chay truoc. Bam MU MOT
  //    lan la sai huong mot nua so lan. Doc truoc, chi bam khi con o dark.
  const toggle = page.locator('button[title="Đổi giao diện"]');
  let themeClass = await page.evaluate(() => document.querySelector('.canvas-shell')?.className);
  if (!(themeClass || '').includes('theme-light')) {
    await toggle.click();
    await page.waitForTimeout(300);
    themeClass = await page.evaluate(() => document.querySelector('.canvas-shell')?.className);
  }
  soLieu.themeClass = themeClass;
  check((themeClass || '').includes('theme-light'), 'khong chuyen sang theme-light duoc: ' + themeClass);

  // Mo palette + inspector de co du 11 o can do (giong audit 27/09).
  await page.locator('button[title="Thêm node"]').click();
  await page.waitForTimeout(150);
  await page.locator('.react-flow__node').first().click();
  await page.locator('button[title="Chi tiết node"]').click();
  await page.waitForTimeout(150);

  const formInfo = await page.evaluate(() => {
    const toLuma = (rgb) => {
      const m = /rgba?\(([\d.]+),\s*([\d.]+),\s*([\d.]+)/.exec(rgb || '');
      if (!m) return null;
      const [r, g, b] = [m[1], m[2], m[3]].map(Number);
      return 0.2126 * r + 0.7152 * g + 0.0722 * b; // 0..255, tho nhung du dung
    };
    const els = [...document.querySelectorAll(
      '.canvas-palette input, .canvas-palette select, .canvas-palette textarea,' +
      '.canvas-inspector input, .canvas-inspector select, .canvas-inspector textarea,' +
      '.workflow-identity input')];
    const rows = els.map(el => {
      const bg = getComputedStyle(el).backgroundColor;
      const luma = toLuma(bg);
      return { tag: el.tagName, name: el.name || el.id || el.placeholder ||
                 el.getAttribute('aria-label') || '(?)', bg, luma,
               toi: luma !== null && luma < 128 };
    });
    return { tong: rows.length, giuNenToi: rows.filter(r => r.toi).length, rows };
  });
  soLieu.formInfo = formInfo;
  check(formInfo.giuNenToi === 0,
    `theme-light: ${formInfo.giuNenToi}/${formInfo.tong} o form van giu nen TOI: ` +
    JSON.stringify(formInfo.rows.filter(r => r.toi)));

  // ── Phep do 3: tuong phan be mat minimap/controls (do THAT, khong doan) ──
  const contrastInfo = await page.evaluate(() => {
    const rel = (rgb) => {
      const m = /rgba?\(([\d.]+),\s*([\d.]+),\s*([\d.]+)/.exec(rgb || '');
      if (!m) return null;
      const chan = [m[1], m[2], m[3]].map(Number).map(c => {
        c = c / 255;
        return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
      });
      return 0.2126 * chan[0] + 0.7152 * chan[1] + 0.0722 * chan[2];
    };
    const ratio = (a, b) => {
      const [L1, L2] = [rel(a), rel(b)].sort((x, y) => y - x);
      return (L1 + 0.05) / (L2 + 0.05);
    };
    const stage = document.querySelector('.canvas-stage');
    const minimap = document.querySelector('.react-flow__minimap');
    const controlsBtn = document.querySelector('.react-flow__controls button');
    const stageBg = stage ? getComputedStyle(stage).backgroundColor : null;
    const minimapBg = minimap ? getComputedStyle(minimap).backgroundColor : null;
    const minimapBorder = minimap ? getComputedStyle(minimap).borderColor : null;
    const controlsBg = controlsBtn ? getComputedStyle(controlsBtn).backgroundColor : null;
    return {
      stageBg, minimapBg, minimapBorder, controlsBg,
      minimapPresent: !!minimap, controlsPresent: !!controlsBtn,
      minimapFillContraste: (stageBg && minimapBg) ? ratio(stageBg, minimapBg) : null,
      minimapBorderContraste: (stageBg && minimapBorder) ? ratio(stageBg, minimapBorder) : null,
      controlsFillContraste: (stageBg && controlsBg) ? ratio(stageBg, controlsBg) : null,
    };
  });
  soLieu.contrastInfo = contrastInfo;
  check(contrastInfo.minimapPresent, 'khong tim thay .react-flow__minimap');
  check(contrastInfo.controlsPresent, 'khong tim thay .react-flow__controls button');

  // ── Bon so suc khoe trang ─────────────────────────────────────────────
  check(pageErrors.length === 0,     'pageerror: ' + JSON.stringify(pageErrors));
  check(consoleErrors.length === 0,  'console error: ' + JSON.stringify(consoleErrors));
  check(failedRequests.length === 0, 'request hong: ' + JSON.stringify(failedRequests));
  check(serverErrors.length === 0,   '5xx: ' + JSON.stringify(serverErrors));

  if (loi.length) return {status: 'FAIL', loi, so_lieu: soLieu};
  return {status: 'PASS', so_lieu: soLieu};
}
