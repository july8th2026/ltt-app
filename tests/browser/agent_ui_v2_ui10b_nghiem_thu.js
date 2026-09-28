// UI-10b nghiem thu (Tro nang + mobile — may chu CO LAP cong 8209).
//
// ⛔ Do bang DUNG CU, khong bang mat: tuong phan tinh tu getComputedStyle +
//    cong thuc luminance WCAG; vung bam do bang elementFromPoint TAI TAM
//    (toa do dung khong co nghia bam duoc — mot nhan z-index cao hon co the
//    che cong, bai hoc 27/09); thu tu tab do bang Tab lien tiep + doc
//    document.activeElement; aria-pressed doc lai SAU khi doi trang thai that.
//
// Chay:
//     playwright-cli -s=ui10b run-code --filename=tests/browser/agent_ui_v2_ui10b_nghiem_thu.js
async page => {
  const base = 'http://127.0.0.1:8209';
  const EMAIL = 'agent-ui10b@example.com';
  const MATKHAU = 'Browser-ui10b-2026';

  const pageErrors = [], consoleErrors = [], failedRequests = [], serverErrors = [];
  page.on('pageerror',     e => pageErrors.push(e.message));
  page.on('console',       m => { if (m.type() === 'error') consoleErrors.push(m.text()); });
  page.on('requestfailed', r => failedRequests.push({url: r.url(), err: r.failure()?.errorText}));
  page.on('response',      r => { if (r.status() >= 500) serverErrors.push({url: r.url(), status: r.status()}); });

  const loi = [];
  const check = (dk, msg) => { if (!dk) loi.push(msg); };
  const soLieu = {};

  await page.setViewportSize({width: 1536, height: 960});

  // ── Dang nhap (fixture cua CHINH may chu nay) ─────────────────────────
  await page.goto(base + '/login');
  if (await page.locator('#login-username').count()) {
    await page.locator('#login-username').fill(EMAIL);
    await page.locator('#login-password').fill(MATKHAU);
    await page.locator('form button[type=submit]').click();
    await page.waitForLoadState('networkidle');
  }
  check(!page.url().includes('/login'), 'dang nhap that bai');

  // Dat do thi co MOT node so hoc (co truong `count`) de do o cong tac
  // bieu thuc + it nhat mot node de Controls/MiniMap co gi de hien.
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
  const nut = (id, tool, params, x = 240, y = 160) =>
    ({id, type:'tool', position:{x, y}, data:{tool, params}});

  await datDoThi([nut('n-vid', 'video.generate', {prompt: 'x'})], []);

  // ══ Hang muc 91 — aria-pressed KHONG con dong cung ════════════════════
  // Mo inspector cua node, tim nut "Dung bieu thuc" tren mot truong SO, doi
  // trang thai THAT roi doc lai thuoc tinh — gia tri PHAI doi theo.
  // ⚠️ Bam vao NODE da tu mo inspector (`chonNode` trong EditorShell.tsx dat
  //    `desktopPanel('inspector')`) — bam THEM vao nut ray se TOGGLE nó tro
  //    lai dong, vi `batNgan` la ham DAO trang thai. ⛔ Dung bam nut ray o day.
  await page.locator('.react-flow__node').first().click();
  await page.locator('button.o-cong-tac-bieu-thuc').first().waitFor({timeout: 10000});
  const nutBieuThuc = page.locator('button.o-cong-tac-bieu-thuc').first();
  const truoc = await nutBieuThuc.getAttribute('aria-pressed');
  await nutBieuThuc.click();
  await page.waitForTimeout(100);
  const sau = await nutBieuThuc.getAttribute('aria-pressed');
  soLieu.ariaPressedToggle = {truoc, sau};
  check(truoc !== null && sau !== null && truoc !== sau,
    `aria-pressed KHONG doi khi bam: truoc=${truoc} sau=${sau}`);

  // ══ Hang muc 92 — tuong phan Controls/MiniMap CA HAI THEME ════════════
  const contrastCong = `(function(){
    function lin(c){c=c/255;return c<=0.03928?c/12.92:Math.pow((c+0.055)/1.055,2.4)}
    function lum(rgb){const m=rgb.match(/\\d+/g).map(Number);
      return 0.2126*lin(m[0])+0.7152*lin(m[1])+0.0722*lin(m[2])}
    function contrast(a,b){let la=lum(a),lb=lum(b);if(la<lb)[la,lb]=[lb,la];return (la+0.05)/(lb+0.05)}
    const canvasBg = getComputedStyle(document.querySelector('.canvas-stage')).backgroundColor;
    const ctlBtn = document.querySelector('.react-flow__controls button');
    const mmap = document.querySelector('.react-flow__minimap');
    const out = {canvasBg};
    if (ctlBtn) { const s=getComputedStyle(ctlBtn);
      out.controlsBorder = s.borderTopColor; out.controlsBg = s.backgroundColor;
      out.controlsBorderVsCanvas = contrast(s.borderTopColor, canvasBg); }
    if (mmap) { const s=getComputedStyle(mmap);
      out.minimapBorder = s.borderTopColor; out.minimapBg = s.backgroundColor;
      out.minimapBorderVsCanvas = contrast(s.borderTopColor, canvasBg);
      out.minimapBgVsCanvas = contrast(s.backgroundColor, canvasBg); }
    return out;
  })()`;
  const doTuongPhan = async (nhan) => {
    const r = await page.evaluate(contrastCong);
    soLieu['tuongPhan_' + nhan] = r;
    if (r.controlsBorderVsCanvas !== undefined)
      check(r.controlsBorderVsCanvas >= 3,
        `[${nhan}] vien Controls vs canvas = ${r.controlsBorderVsCanvas.toFixed(2)}:1 < 3:1 (WCAG 1.4.11)`);
    if (r.minimapBorderVsCanvas !== undefined)
      check(r.minimapBorderVsCanvas >= 3,
        `[${nhan}] vien MiniMap vs canvas = ${r.minimapBorderVsCanvas.toFixed(2)}:1 < 3:1`);
  };
  await doTuongPhan('dark');
  const nutTheme = page.locator('button[aria-label="Chuyển sang nền sáng"]');
  if (await nutTheme.count()) { await nutTheme.click(); await page.waitForTimeout(300); }
  await doTuongPhan('light');

  // ══ Hang muc 93 — vung bam DUNG CU elementFromPoint TAI TAM ═══════════
  // ⚠️ Cham tron `.react-flow__handle` chi 12x12px (`--handle-size`) — vung
  //    BAM that su la mot `::after` phong to 24x24 (`--handle-hit`, xem
  //    `canvas.css` dong ~271). `getBoundingClientRect()` tren chinh handle
  //    KHONG thay pseudo-element ⇒ phai doc `getComputedStyle(h, '::after')`.
  const congBam = await page.evaluate(() => {
    const handles = [...document.querySelectorAll('.react-flow__handle')];
    return handles.slice(0, 6).map(h => {
      const r = h.getBoundingClientRect();
      const sauCham = getComputedStyle(h, '::after');
      const cx = r.x + r.width / 2, cy = r.y + r.height / 2;
      const trung = document.elementFromPoint(cx, cy);
      return {
        chamRong: Math.round(r.width), chamCao: Math.round(r.height),
        vungBamRong: Math.round(parseFloat(sauCham.width) || 0),
        vungBamCao: Math.round(parseFloat(sauCham.height) || 0),
        bamDuoc: !!(trung && (trung === h || h.contains(trung))),
      };
    });
  });
  soLieu.congBam = congBam;
  congBam.forEach((c, i) => {
    check(c.vungBamRong >= 24 && c.vungBamCao >= 24,
      `cong #${i} vung bam (::after) ${c.vungBamRong}x${c.vungBamCao}px < 24x24 (WCAG 2.2 AA 2.5.8)`);
    check(c.bamDuoc, `cong #${i} toa do dung nhung elementFromPoint KHONG tra ve chinh no (bi che)`);
  });

  // Tro ve theme toi truoc khi do cac phan con lai (giu trang thai nhat quan).
  const nutThemeToi = page.locator('button[aria-label="Chuyển sang nền tối"]');
  if (await nutThemeToi.count()) { await nutThemeToi.click(); await page.waitForTimeout(200); }

  // ══ Hang muc 90 — BAY FOCUS trong CommandPalette (Ctrl/Cmd+K) ═════════
  // 🔴 CHO panel NAP TRE (lan UI-10a, gop 28/09). `waitForTimeout(150)` la mot
  //    tien de ngam: *panel co mat NGAY sau khi bam*. UI-10a doi ba panel nay
  //    sang `React.lazy` + `import()`, nen giua cu bam va cai panel con mot
  //    nhip MANG — va ba muc o day do OAN.
  //
  // ⭐ Do tach doi de biet do la loi gi: `ngay=0` + `sau>0` ⇒ **phep do hoi qua
  //    som**, tinh nang con song (`agent_ui_v2_nap_tre_van_mo_duoc.js`).
  //    Neu `sau` cung `0` thi moi la tinh nang hong.
  // ⚠️ `waitForSelector` chu ⛔ KHONG phai `waitForTimeout` dai hon: mot moc thoi
  //    gian co dinh se lai do oan ngay khi may cham hon, va no ⛔ khong bao gio
  //    noi ly do.
  const choPanel = async (chon) => {
    try { await page.waitForSelector(chon, { timeout: 5000, state: 'attached' }) }
    catch { /* de phep kiem duoi bao, ⛔ dung nem o day */ }
  };

  await page.keyboard.press('Control+k');
  await choPanel('.command-palette');
  const coBangLenh = await page.locator('.command-palette').count();
  soLieu.coBangLenh = coBangLenh;
  if (coBangLenh) {
    // Shift+Tab tu phan tu DAU phai vong ve phan tu CUOI trong hop thoai.
    const dauTien = await page.evaluate(() => document.activeElement?.tagName + ':' + (document.activeElement?.getAttribute('aria-label')||document.activeElement?.placeholder||''));
    await page.keyboard.press('Shift+Tab');
    const sauShiftTab = await page.evaluate(() => {
      const el = document.activeElement;
      const hop = document.querySelector('.command-palette');
      return {trongHop: !!(hop && hop.contains(el)), nhan: el?.tagName};
    });
    soLieu.bayFocusCommandPalette = {dauTien, sauShiftTab};
    check(sauShiftTab.trongHop, 'Shift+Tab tu dau CommandPalette THOAT ra ngoai hop thoai — khong co bay focus');
    await page.keyboard.press('Escape');
    await page.waitForTimeout(150);
  } else {
    loi.push('CommandPalette khong mo duoc bang Ctrl+K de do bay focus');
  }

  // ══ Hang muc 90 — BAY FOCUS trong ngan "Lop" (LayersDrawer) ═══════════
  const nutLop = page.locator('button[aria-label="Mở danh sách lớp"]');
  if (await nutLop.count()) {
    await nutLop.click();
    await choPanel('.layers-drawer');          // nap tre — xem chu thich tren
    const coNganLop = await page.locator('.layers-drawer').count();
    if (coNganLop) {
      await page.locator('.layers-drawer button').first().focus();
      await page.keyboard.press('Shift+Tab');
      const sau2 = await page.evaluate(() => {
        const hop = document.querySelector('.layers-drawer');
        return hop ? hop.contains(document.activeElement) : null;
      });
      soLieu.bayFocusLayersDrawer = sau2;
      check(sau2 === true, 'Shift+Tab tu dau ngan Lop THOAT ra ngoai — khong co bay focus');
      await page.locator('button[aria-label="Đóng danh sách lớp"]').click();
    } else loi.push('Ngan Lop khong mo duoc de do bay focus');
  }

  // ══ Hang muc 89 — bang phim tat co tai lieu, mo duoc bang phim "?" ════
  await page.keyboard.press('?');
  await choPanel('.shortcuts-help-list');    // co the nam trong chunk nap tre
  const coBangPhimTat = await page.locator('.shortcuts-help-list').count();
  soLieu.coBangPhimTat = coBangPhimTat;
  check(coBangPhimTat > 0, 'Phim "?" khong mo duoc bang phim tat (hang muc 89: chua tai lieu)');
  if (coBangPhimTat) {
    const soDong = await page.locator('.shortcuts-help-list > div').count();
    soLieu.soDongPhimTat = soDong;
    check(soDong >= 8, `bang phim tat chi liet ke ${soDong} dong`);
    await page.keyboard.press('Escape');
    await page.waitForTimeout(100);
  }

  // ══ Hang muc 94 — Mobile: doi kich thuoc + RELOAD + kiem tab ══════════
  await page.setViewportSize({width: 390, height: 844});
  await page.reload();
  await page.locator('#agent-canvas-root').waitFor();
  await page.waitForTimeout(500);
  const tabs = await page.locator('.canvas-mobile-tabs button').count();
  soLieu.soTabMobile = tabs;
  check(tabs === 3, `canvas-mobile-tabs co ${tabs} nut, cho 3 (Canvas/Cong cu/Chi tiet)`);
  if (tabs === 3) {
    // Mac dinh phai o tab Canvas — Inspector KHONG duoc dinh tren man hinh.
    const inspectorDinh = await page.evaluate(() => {
      const el = document.querySelector('.canvas-inspector');
      if (!el) return false;
      const cs = getComputedStyle(el);
      return cs.display !== 'none' && el.getBoundingClientRect().width > 0;
    });
    soLieu.inspectorDinhTrenManHinhMacDinh = inspectorDinh;
    check(!inspectorDinh, 'Vao mobile mac dinh da thay Inspector — tung la loi UI-3, dang duoc UI-10a sua o EditorShell');
    await page.locator('.canvas-mobile-tabs button', {hasText: 'Chi tiết'}).click();
    await page.waitForTimeout(200);
    const inspectorSauKhiBam = await page.evaluate(() => {
      const el = document.querySelector('.canvas-inspector');
      return !!(el && getComputedStyle(el).display !== 'none');
    });
    soLieu.inspectorHienSauKhiBamTab = inspectorSauKhiBam;
    check(inspectorSauKhiBam, 'Bam tab "Chi tiết" nhung Inspector khong hien');
  }
  await page.setViewportSize({width: 1536, height: 960});

  // ── Bon so suc khoe trang ─────────────────────────────────────────────
  check(pageErrors.length === 0,     'pageerror: ' + JSON.stringify(pageErrors));
  check(consoleErrors.length === 0,  'console error: ' + JSON.stringify(consoleErrors));
  check(failedRequests.length === 0, 'request hong: ' + JSON.stringify(failedRequests));
  check(serverErrors.length === 0,   '5xx: ' + JSON.stringify(serverErrors));

  if (loi.length) return {status: 'FAIL', loi, so_lieu: soLieu};
  return {status: 'PASS', so_lieu: soLieu};
}
