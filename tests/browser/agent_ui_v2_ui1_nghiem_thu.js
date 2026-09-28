// UI-1 nghiem thu (che do A — may chu CO LAP cong 8198).
//
// ⛔ Khong doc ma roi tuyen bo xong. Menh de chinh cua lan nay —
//    *"mo workflow THU HAI thi duoc dung no, khong nhay ve items[0]"* — chi
//    chung minh duoc bang mot lan nap THAT: quyet dinh nam trong mot effect
//    chay sau khi ba cua (`/palette`, workflow, `/preferences`) tra ve.
//
// Moc nen do 27/09/2026 (`01_CURRENT_UI_AUDIT.md` §1, §1.1):
//     so trang HTML cua app        = 2  (`/agent`, `/agent/canvas`)
//     danh sach workflow           = KHONG CO
//     nut "Workflow moi"           = KHONG CO
//     duong mo mot workflow khac   = KHONG CO
//
// Chay:
//     set AGENT_UI0_FIXTURE_ROOT=<thu muc NGOAI kho>
//     python -m uvicorn tests.browser.agent_ui_v2_ui0_may_chu:app ^
//            --host 127.0.0.1 --port 8198
//     playwright-cli -s=ui1 run-code --filename=tests/browser/agent_ui_v2_ui1_nghiem_thu.js
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

  // 🔴 Dat khung nhin tuong minh — profile trinh duyet dung chung giua cac
  //    kich ban, va `agent_ui_v2_ui3_mobile.js` de lai 390x844 (o be rong do
  //    trinh soan vao che do chi-xem). Mot phep kiem phu thuoc thu tu chay la
  //    mot phep kiem se do vi ly do sai.
  await page.setViewportSize({width: 1536, height: 960});

  // ── Dang nhap (tai khoan FIXTURE cua chinh may chu 8198) ─────────────────
  await page.goto(base + '/login');
  if (await page.locator('#login-username').count()) {
    await page.locator('#login-username').fill(EMAIL);
    await page.locator('#login-password').fill(MATKHAU);
    await page.locator('form button[type=submit]').click();
    await page.waitForLoadState('networkidle');
  }
  check(!page.url().includes('/login'), 'dang nhap that bai');

  // ── Don sach: xoa moi workflow cu bang cach LUU TRU o tang CSDL thi khong
  //    co cua nao, nen thay vao do ta chi DEM va lam viec voi so hien co.
  //    (Chay lai kich ban nhieu lan van dung: moi phep do duoi day so sanh
  //    theo id cu the, khong theo so tuyet doi.)
  await page.goto(base + '/agent/workflows');
  await page.locator('h1').first().waitFor();

  // ── 1. Trang danh sach TON TAI va dem dung so cua tai khoan ─────────────
  const demTrang = async () => (await page.locator('[data-wf-id]').count());
  const demApi = async () => await page.evaluate(async () => {
    const r = await fetch('/agent/api/v3/workflows',
      {credentials: 'same-origin', headers: {Accept: 'application/json'}});
    return (await r.json()).items.length;
  });
  soLieu.truoc_danh_sach = await demTrang();
  check(soLieu.truoc_danh_sach === await demApi(),
        'danh sach tren trang lech voi cua v3');

  // ── 2. Tao workflow moi TU GIAO DIEN -> mo duoc NGAY ────────────────────
  const truoc = await demTrang();
  await page.locator('#wfl-tao, #wfl-tao-trong').first().click();
  await page.waitForURL(/\/agent\/workflows\/[0-9a-f-]{8,}/, {timeout: 20000});
  const idMoi = page.url().split('/').pop();
  soLieu.id_moi = idMoi;
  await page.locator('#agent-canvas-root').waitFor();
  check(await page.getAttribute('#agent-canvas-root', 'data-workflow-id') === idMoi,
        'trang trinh soan khong mang dung id vua tao');
  // Trinh soan phai NAP XONG (khong dung o mang loi) — do bang chinh lop trang
  // thai cua no, khong bang mot `waitForTimeout` may man.
  await page.locator('.canvas-shell').waitFor({timeout: 20000});
  check(await page.locator('.canvas-state.error').count() === 0,
        'trinh soan bao loi khi mo workflow vua tao');

  // Tao mot cai thu hai, de chac chan co >= 2.
  await page.goto(base + '/agent/workflows');
  await page.locator('#wfl-tao, #wfl-tao-trong').first().click();
  await page.waitForURL(/\/agent\/workflows\/[0-9a-f-]{8,}/, {timeout: 20000});
  const idMoiNhat = page.url().split('/').pop();
  soLieu.id_moi_nhat = idMoiNhat;
  check(idMoiNhat !== idMoi, 'hai lan bam "Workflow moi" ra cung mot id');

  await page.goto(base + '/agent/workflows');
  soLieu.sau_danh_sach = await demTrang();
  check(soLieu.sau_danh_sach === truoc + 2,
        `danh sach phai tang 2 (${truoc} -> ${soLieu.sau_danh_sach})`);

  // ── 3. 🔴 MENH DE CHOT: mo cai KHONG-moi-nhat van dung no ───────────────
  //    `idMoi` khong con la `items[0]` (idMoiNhat moi la). Mot trinh soan con
  //    lay `items[0]` se mo `idMoiNhat` o day.
  const dauTien = await page.evaluate(async () => {
    const r = await fetch('/agent/api/v3/workflows',
      {credentials: 'same-origin', headers: {Accept: 'application/json'}});
    return (await r.json()).items[0].id;
  });
  soLieu.items_0 = dauTien;
  check(dauTien !== idMoi, 'moc phep do sai: `items[0]` dang la chinh cai ta mo');

  // Bam dung dong cua `idMoi` tren GIAO DIEN, ⛔ khong goto thang.
  await page.locator(`[data-wf-id="${idMoi}"] a`).first().click();
  await page.waitForURL(new RegExp(idMoi));
  await page.locator('.canvas-shell').waitFor({timeout: 20000});
  const idDaNap = await page.evaluate(() => {
    const el = document.querySelector('#agent-canvas-root');
    return el ? el.dataset.workflowId : '';
  });
  soLieu.id_da_nap = idDaNap;
  check(idDaNap === idMoi, `mo cai thu hai ra cai khac: ${idDaNap} != ${idMoi}`);
  // Va cua ma trinh soan THAT SU goi phai la cua cua dung id do.
  const daGoi = await page.evaluate(() => performance.getEntriesByType('resource')
    .map(e => e.name).filter(n => n.includes('/api/v3/workflows')));
  soLieu.so_loi_goi_workflow = daGoi.length;
  check(daGoi.some(n => n.includes('/api/v3/workflows/' + idMoi)),
        'trinh soan khong he GET workflow duoc yeu cau');
  check(!daGoi.some(n => n.includes('/api/v3/workflows/' + dauTien)),
        'trinh soan VAN nap `items[0]` — quyet dinh con nam o cho cu');

  // ── 4. Tai lai trang van dung workflow do ───────────────────────────────
  await page.reload();
  await page.locator('.canvas-shell').waitFor({timeout: 20000});
  check(await page.getAttribute('#agent-canvas-root', 'data-workflow-id') === idMoi,
        'tai lai trang doi workflow');

  // ── 4b. Nhan ban: ra mot workflow MOI, ⛔ khong sua cai goc ─────────────
  //    Di qua dung hai cua da co (GET roi POST). Phep do manh o cho no doi
  //    chieu NOI DUNG: mot ban sao rong la mot nut "Nhan ban" noi doi.
  await page.goto(base + '/agent/workflows');
  const truocNhan = await demTrang();
  await page.locator(`[data-wf-id="${idMoi}"] [data-wfl-nhan-ban]`).click();
  await page.waitForURL(/\/agent\/workflows\/[0-9a-f-]{8,}/, {timeout: 20000});
  const idBanSao = page.url().split('/').pop();
  soLieu.id_ban_sao = idBanSao;
  check(idBanSao !== idMoi, 'nhan ban mo lai chinh workflow goc');
  await page.goto(base + '/agent/workflows');
  soLieu.sau_nhan_ban = await demTrang();
  check(soLieu.sau_nhan_ban === truocNhan + 1,
        `nhan ban phai tang 1 (${truocNhan} -> ${soLieu.sau_nhan_ban})`);
  const doi = await page.evaluate(async ([a, b]) => {
    const lay = async id => (await (await fetch('/agent/api/v3/workflows/' + id,
      {credentials: 'same-origin', headers: {Accept: 'application/json'}})).json());
    const [goc, sao] = [await lay(a), await lay(b)];
    return {ten_goc: goc.name, ten_sao: sao.name,
            cung_tai_lieu: JSON.stringify(goc.document) === JSON.stringify(sao.document)};
  }, [idMoi, idBanSao]);
  soLieu.nhan_ban = doi;
  check(doi.cung_tai_lieu, 'ban sao KHONG mang tai lieu cua ban goc');
  check(doi.ten_sao !== doi.ten_goc, 'ban sao trung ten y het ban goc');

  // ── 5. Tim theo ten loc dung ────────────────────────────────────────────
  await page.goto(base + '/agent/workflows?q=khong-he-co-ten-nay');
  soLieu.tim_khong_khop = await demTrang();
  check(soLieu.tim_khong_khop === 0, 'o tim khong loc gi');
  await page.goto(base + '/agent/workflows');
  check(await demTrang() === soLieu.sau_nhan_ban, 'xoa bo loc khong ve day du');

  // ── 6. Nam trang dat cho: 200 + NOI RO dang xay ─────────────────────────
  const DAT_CHO = ['/agent/runs', '/agent/templates', '/agent/connections',
                   '/agent/agents', '/agent/settings'];
  soLieu.dat_cho = {};
  // 🔴 Moc la `[data-dang-xay]`, ⛔ KHONG phai `text=Đang xây` — va ly do that
  //    su khac voi ly do de doan. Lan chay dau tien bai nay DO voi ca nam
  //    duong, trong khi `test_6200` xanh tren cung mot HTML. Thu phai: trinh
  //    duyet gui `Accept-Language: en-US`, nen may chu tra ban **tieng Anh** —
  //    `chu` duoi day ghi lai "In progress", khong phai "Đang xây".
  //
  //    ⇒ Mot bo chon theo CHU tieng Viet do vi ngon ngu, khong vi trang hong.
  //      Moc ASCII khong phu thuoc ngon ngu; con chinh CHU thi `test_6200`
  //      chot tren HTML (moi truong tieng Viet). Hai lop, hai cau hoi.
  //
  //    ⭐ Va day cung la bang chung PHU cho ban dich EN: neu mot chuoi moi con
  //      thieu `msgstr`, no se ra tieng Viet **ngay tren trang nay**.
  for (const duong of DAT_CHO) {
    const r = await page.goto(base + duong);
    const huy = page.locator('[data-dang-xay]');
    const co = await huy.count() > 0 && await huy.first().isVisible();
    const chu = co ? (await huy.first().innerText()).trim() : '';
    soLieu.dat_cho[duong] = {status: r.status(), noi_ro: co, chu};
    check(r.status() === 200, `${duong} tra ${r.status()}`);
    check(co, `${duong} KHONG noi ro dang xay — mot trang trong nhu that`);
  }

  // ── 7. Thanh muc cua app co du sau muc, va moi link song ────────────────
  await page.goto(base + '/agent/workflows');
  const tab = await page.locator('nav.apptabs a').evaluateAll(
    as => as.map(a => a.getAttribute('href')));
  soLieu.thanh_muc = tab;
  check(tab.length === 7, `thanh muc co ${tab.length} muc, cho doi 7`);
  for (const href of tab) {
    const r = await page.goto(base + href);
    check(r.status() === 200, `muc nav ${href} tra ${r.status()}`);
  }

  // ── 8. Loi vao KHONG id van chay (`test_1726` chot no) ──────────────────
  await page.goto(base + '/agent/canvas');
  await page.locator('.canvas-shell').waitFor({timeout: 20000});
  soLieu.canvas_khong_id = await page.getAttribute('#agent-canvas-root',
                                                   'data-workflow-id');
  check(soLieu.canvas_khong_id === '', '/agent/canvas mang san mot id');
  check(await page.locator('.canvas-state.error').count() === 0,
        '/agent/canvas bao loi');

  // ── Bon thu phai thu moi pha ────────────────────────────────────────────
  // ⚠️ `favicon.ico` thieu tren may chu fixture khong phai loi cua pha nay.
  const boQua = u => u.includes('favicon');
  const req = failedRequests.filter(r => !boQua(r.url));
  soLieu.pageErrors = pageErrors;
  soLieu.consoleErrors = consoleErrors;
  soLieu.failedRequests = req;
  soLieu.serverErrors = serverErrors;
  check(pageErrors.length === 0, `pageerror: ${JSON.stringify(pageErrors)}`);
  check(consoleErrors.length === 0, `console error: ${JSON.stringify(consoleErrors)}`);
  check(req.length === 0, `request hong: ${JSON.stringify(req)}`);
  check(serverErrors.length === 0, `5xx: ${JSON.stringify(serverErrors)}`);

  return {status: loi.length ? 'FAIL' : 'PASS', loi, so_lieu: soLieu};
}
