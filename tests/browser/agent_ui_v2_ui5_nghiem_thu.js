// UI-5 nghiem thu (che do A — may chu CO LAP cong 8204).
//
// ⛔ Khong doc ma roi tuyen bo da sua. Hai trong bon menh de cua lan nay chi
//    do duoc tren trinh duyet that:
//      * "+ Tạo kết nối" phai la DONG DAU cua chinh dropdown, va form phai mo
//        NGAY TRONG panel — jsdom khong noi duoc "nguoi dung co roi trang
//        khong", chi mot lan dieu huong that moi noi duoc.
//      * Truong phu thuoc AN: loi goc la BA dropdown chet cung luc tren layout
//        that.
//
// Moc nen do 28/09/2026 (tren cong publish that, tham so day du):
//     72 node · 34 doi credential · 27 publish duoc · 60 sau khi co ref
//     frontend: `grep credential_ref` trong src/ => KHONG CO DONG NAO
//     may chu : khong mot cua nao cho khach tao mot ket noi
//
// Chay:
//   playwright-cli -s=ui5 run-code --filename=tests/browser/agent_ui_v2_ui5_nghiem_thu.js
async page => {
  const base = 'http://127.0.0.1:8204';
  const EMAIL = 'agent-ui5@example.com';
  const MATKHAU = 'Browser-ui5-2026';

  const pageErrors = [], consoleErrors = [], failedRequests = [], serverErrors = [];
  page.on('pageerror',     e => pageErrors.push(e.message));
  page.on('console',       m => { if (m.type() === 'error') consoleErrors.push(m.text()); });
  page.on('requestfailed', r => failedRequests.push({url: r.url(), err: r.failure()?.errorText}));
  page.on('response',      r => { if (r.status() >= 500) serverErrors.push({url: r.url(), status: r.status()}); });

  const loi = [];
  const check = (dk, msg) => { if (!dk) loi.push(msg); };
  const soLieu = {};

  // ── Dang nhap (tai khoan fixture cua CHINH may chu thu nay) ───────────
  // ⚠️ Chay lai kich ban tren CUNG profile thi cookie phien truoc con song va
  //    `/login` chuyen huong ngay => khong co `#login-username`. Dang nhap CO
  //    DIEU KIEN, ⛔ khong gia dinh luon thay form.
  await page.goto(base + '/login');
  if (await page.locator('#login-username').count()) {
    await page.locator('#login-username').fill(EMAIL);
    await page.locator('#login-password').fill(MATKHAU);
    await page.locator('form button[type=submit]').click();
    await page.waitForLoadState('networkidle');
  }
  check(!page.url().includes('/login'), 'dang nhap that bai');

  // ── Dat MOT buoc doi `api_key` len do thi, roi mo Inspector ───────────
  //
  // ⭐ Loai buoc lay TU MAY CHU (`/agent/api/v3/palette`), ⛔ khong go cung mot
  //    `type` vao kich ban: mot ten go cung la mot hang chet ngay khi catalog
  //    doi, va no se bao "khong tim thay buoc" thay vi "buoc nay hong".
  await page.goto(base + '/agent/canvas');
  await page.locator('#agent-canvas-root').waitFor();
  await page.waitForFunction(async () => {
    const r = await fetch('/agent/api/v3/workflows',
      {credentials: 'same-origin', headers: {Accept: 'application/json'}});
    const j = await r.json();
    return Array.isArray(j.items) && j.items.length > 0;
  }, null, {timeout: 20000});

  const chuan = await page.evaluate(async () => {
    const lay = async u => await (await fetch(u, {credentials: 'same-origin',
      headers: {Accept: 'application/json'}})).json();
    const pal = await lay('/agent/api/v3/palette');
    const nut = pal.nhom.flatMap(n => n.nut);
    // Buoc doi `api_key`.
    //
    // ⚠️ ⛔ KHONG lay cai dau tien: `core.http` nhan `api_key` nhung
    //    `dinh_nghia._kiem_credential` **khong** chan no khi thieu ref
    //    (`job_type` ngoai `JOB_TYPE_KHONG_TOOLSPEC`). Dung no thi phep do
    //    "publish duoc sau khi gan" xanh ma khong chung minh gi — node do
    //    publish duoc ca khi chua gan.
    //
    //    Palette khong phoi `job_type` ra ngoai (`sang_json` co y khong), nen
    //    phep chon o day dung dieu palette CO noi: node `core.*` do nen tang
    //    thi hanh, node piece/connector do runner ngoai — va dung nhom thu hai
    //    la nhom bi chan.
    const doiApiKey = nut.filter(n => (n.credential || []).includes('api_key'));
    const buoc = doiApiKey.find(n => !n.type.startsWith('core.')) || doiApiKey[0];
    // Buoc co >= 2 truong PHU THUOC cung mot tham so cha (loi ba dropdown).
    const phuThuoc = nut.find(n => {
      const p = (n.tham_so || {}).properties || {};
      const cha = {};
      for (const k of Object.keys(p)) {
        const d = p[k]['x-ltt-dong'];
        if (d) cha[d.prop] = (cha[d.prop] || 0) + 1;
      }
      return Object.values(cha).some(v => v >= 2);
    });
    const chaCua = n => {
      const p = (n.tham_so || {}).properties || {};
      const cha = {};
      for (const k of Object.keys(p)) {
        const d = p[k]['x-ltt-dong'];
        if (d) cha[d.prop] = (cha[d.prop] || 0) + 1;
      }
      return Object.entries(cha).sort((a, b) => b[1] - a[1])[0];
    };
    return {
      soNut: nut.length,
      soDoiCredential: nut.filter(n => (n.credential || []).length).length,
      buoc: buoc ? {type: buoc.type, credential: buoc.credential,
                    bat_buoc: (buoc.tham_so.required || [])} : null,
      phuThuoc: phuThuoc ? {type: phuThuoc.type, cha: chaCua(phuThuoc)} : null,
    };
  });
  soLieu.palette = chuan;
  check(chuan.buoc, 'palette khong co buoc nao doi `api_key`');
  if (!chuan.buoc) return {status: 'FAIL', loi, so_lieu: soLieu};

  // ⚠️ HINH DANG NODE la hinh dang CUA PALETTE: `type:'tool'` + `data.tool` =
  //    slug. ⛔ Ghi `type:'core.http'` truc tiep lam trinh soan no
  //    `Cannot read properties of undefined (reading 'tool')` va ve mot canvas
  //    RONG — do duoc 28/09 khi viet kich ban nay. `bien_dich._node` nhan ca
  //    hai hinh dang, nen mot kich ban ghi hinh dang "may chu" van publish
  //    duoc trong khi giao dien khong ve gi: mot phep do do sai be mat.
  const nodePalette = (type) => ({
    id: 'n1', type: 'tool', position: {x: 120, y: 120},
    data: {tool: type.startsWith('app.') ? type.slice(4) : type, params: {}},
  });

  const datBuoc = async (type) => {
    await page.evaluate(async (node) => {
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
                   nodes: [node], edges: []}]}})});
    }, nodePalette(type));
    await page.goto(base + '/agent/canvas');
    await page.locator('#agent-canvas-root').waitFor();
    // ⚠️ `#agent-canvas-root` co MAT truoc khi React ve xong node.
    await page.locator('.react-flow__node').first().waitFor({timeout: 20000});
    // Bam vao node ⇒ Inspector MO. Tren mot trang vua nap lai, Inspector
    // KHONG mo san (chi mo san ngay sau khi keo mot node moi).
    await page.locator('.react-flow__node').first().click();
    await page.locator('.inspector-tabs').waitFor({timeout: 15000});
  };

  await datBuoc(chuan.buoc.type);

  // ── Phep do 1: nam tab, va o KET NOI nam ngay trong tab Cấu hình ──────
  const soTab = await page.locator('.inspector-tabs button').count();
  soLieu.soTab = soTab;
  check(soTab === 5, `Inspector co ${soTab} tab (cho 5)`);

  const oKetNoi = page.locator('#o-ket-noi-chon');
  await oKetNoi.waitFor({timeout: 15000});
  const dongDau = await page.evaluate(() =>
    document.querySelector('#o-ket-noi-chon')?.options[0]?.textContent);
  soLieu.dongDauDropdown = dongDau;
  // 🔴 DONG DAU cua chinh dropdown (Activepieces), ⛔ khong phai mot nut o
  //    trang khac.
  check(dongDau === '+ Tạo kết nối',
        `dong dau dropdown ket noi la ${JSON.stringify(dongDau)}`);

  // ── Phep do 2: tao ket noi TAI CHO, KHONG roi trang ──────────────────
  const urlTruoc = page.url();
  await page.selectOption('#o-ket-noi-chon', '\u0000tao-ket-noi');
  await page.locator('form[aria-label="Tạo kết nối mới"]').waitFor({timeout: 10000});
  // ⚠️ Mot buoc piece nhan NHIEU `kieu` (vd `oauth2`/`piece_custom`/`api_key`),
  //    va o "Cách xác thực" mac dinh theo THU TU buoc khai. Tieu chi cua pha
  //    nay la mot ket noi `api_key`, nen chon tuong minh — ⛔ khong dua vao
  //    mac dinh, va cung ⛔ khong doi mac dinh cua san pham cho vua phep do.
  if (await page.locator('#o-ket-noi-kieu').count()) {
    await page.selectOption('#o-ket-noi-kieu', 'api_key');
  }
  await page.locator('#o-ket-noi-ten').fill('Khoa cua toi');
  // Moi o bi mat co id `o-bi-mat-<ten khoa>` — sinh TU danh sach may chu tra
  // ve, nen kich ban khong go cung ten khoa nao.
  const oBiMat = page.locator('form[aria-label="Tạo kết nối mới"] [id^="o-bi-mat-"]');
  const soO = await oBiMat.count();
  soLieu.soOBiMat = soO;
  check(soO >= 1, 'form tao ket noi khong co o bi mat nao');
  const oChe = await page.locator(
    'form[aria-label="Tạo kết nối mới"] input[type=password]').count();
  soLieu.soOChe = oChe;
  // ⛔ Bi mat ⇒ o CHE, khong phai o chu thuong: nguoi ben canh doc duoc man hinh.
  check(oChe >= 1, 'khong o bi mat nao duoc che');
  for (let i = 0; i < soO; i++) {
    await oBiMat.nth(i).fill('sk-ui5-browser-4242');
  }
  await page.locator('form[aria-label="Tạo kết nối mới"] button[type=submit]').click();

  // Ket noi moi phai duoc CHON LUON (o chon mang id that).
  await page.waitForFunction(() => {
    const o = document.querySelector('#o-ket-noi-chon');
    return o && o.value && o.value.length > 20;
  }, null, {timeout: 15000});
  const refDaChon = await page.evaluate(() =>
    document.querySelector('#o-ket-noi-chon').value);
  const urlSau = page.url();
  soLieu.taoTaiCho = {refDaChon: refDaChon.slice(0, 8) + '…',
                      urlKhongDoi: urlTruoc === urlSau};
  // ⭐ KHONG ROI TRANG — day la ca diem cua luong nay.
  check(urlTruoc === urlSau, `URL doi khi tao ket noi: ${urlTruoc} -> ${urlSau}`);
  check(refDaChon.length > 20, 'ket noi moi khong duoc chon tu dong');

  // Panel van con mo va van dung buoc do (⛔ khong mat trang thai dang cau hinh)
  check(await page.locator('.inspector-tabs').count() === 1,
        'Inspector dong sau khi tao ket noi — nguoi dung mat ngu canh');

  // ── Phep do 3: ref ghi o MUC TREN CUNG, va publish DUOC ──────────────
  // ⚠️ Doc TU MAY CHU chu khong tu state trinh duyet: cau hoi that la "thu da
  //    LUU co mang ref o dung cho khong".
  await page.waitForTimeout(2500);   // cho autosave
  const daLuu = await page.evaluate(async () => {
    const lay = async u => await (await fetch(u, {credentials: 'same-origin',
      headers: {Accept: 'application/json'}})).json();
    const ds = await lay('/agent/api/v3/workflows');
    const wf = await lay('/agent/api/v3/workflows/' + ds.items[0].id);
    const n = wf.document.pages[0].nodes[0];
    return {id: ds.items[0].id,
            refTopLevel: n.credential_ref || '',
            refTrongData: (n.data || {}).credential_ref || ''};
  });
  soLieu.daLuu = {refTopLevel: Boolean(daLuu.refTopLevel),
                  refTrongData: Boolean(daLuu.refTrongData)};
  // ⛔ Ghi duoi `data` thi `bien_dich._node_tu_dinh_nghia` khong thay no, va
  //    publish bao "chua gan ket noi" trong khi giao dien hien mot ket noi da
  //    chon — mot bat dong IM LANG.
  check(daLuu.refTopLevel === refDaChon,
        `ref khong o MUC TREN CUNG cua buoc: ${JSON.stringify(daLuu)}`);

  // Dien tham so bat buoc roi publish.
  const pub = await page.evaluate(async ({id, batBuoc}) => {
    const csrf = document.querySelector('#agent-canvas-root').dataset.csrfToken;
    const lay = async u => await (await fetch(u, {credentials: 'same-origin',
      headers: {Accept: 'application/json'}})).json();
    const cur = await lay('/agent/api/v3/workflows/' + id);
    const doc = cur.document;
    const n = doc.pages[0].nodes[0];
    // ⚠️ Tham so cua mot node palette nam o `data.params` (xem `nodePalette`).
    n.data = n.data || {};
    n.data.params = n.data.params || {};
    for (const k of batBuoc) if (!(k in n.data.params)) n.data.params[k] = 'x';
    await fetch('/agent/api/v3/workflows/' + id, {method: 'PUT',
      credentials: 'same-origin',
      headers: {'Content-Type': 'application/json', 'X-CSRF-Token': csrf,
                'If-Match': '"' + cur.revision + '"'},
      body: JSON.stringify({csrf_token: csrf, document: doc})});
    const r = await fetch('/agent/api/v3/workflows/' + id + '/publish',
      {method: 'POST', credentials: 'same-origin',
       headers: {'Content-Type': 'application/json', 'X-CSRF-Token': csrf,
                 Accept: 'application/json'},
       body: JSON.stringify({csrf_token: csrf})});
    return {status: r.status, than: (await r.text()).slice(0, 300)};
  }, {id: daLuu.id, batBuoc: chuan.buoc.bat_buoc});
  soLieu.publish = pub;
  check(pub.status === 200,
        `publish tra ${pub.status} sau khi gan ket noi: ${pub.than}`);

  // ── Phep do 4: buoc KHONG doi ket noi thi ⛔ KHONG hien o ket noi ─────
  const buocKhongCan = await page.evaluate(async () => {
    const pal = await (await fetch('/agent/api/v3/palette',
      {credentials: 'same-origin', headers: {Accept: 'application/json'}})).json();
    const n = pal.nhom.flatMap(x => x.nut)
      .find(x => !(x.credential || []).length && x.publish_duoc);
    return n ? n.type : '';
  });
  check(Boolean(buocKhongCan), 'palette khong co buoc nao khong doi ket noi');
  if (buocKhongCan) {
    await datBuoc(buocKhongCan);
    const co = await page.locator('#o-ket-noi-chon').count();
    soLieu.oKetNoiTrenBuocKhongCan = co;
    check(co === 0, `buoc khong doi ket noi VAN hien o ket noi (${co})`);
  }

  // ── Phep do 5: truong phu thuoc AN khi cha chua co gia tri ───────────
  if (chuan.phuThuoc) {
    await datBuoc(chuan.phuThuoc.type);
    const chet = await page.evaluate(() =>
      [...document.querySelectorAll('.canvas-inspector select')]
        .filter(o => o.options.length === 1
                  && o.options[0].textContent.includes('chưa có lựa chọn nào'))
        .length);
    const dongCho = await page.locator('.o-cho-phu-thuoc').count();
    soLieu.phuThuoc = {type: chuan.phuThuoc.type, cha: chuan.phuThuoc.cha,
                       dropdownChet: chet, dongCho};
    // 🔴 Loi goc: BA dropdown "— chưa có lựa chọn nào —" cung luc.
    check(chet === 0, `van con ${chet} dropdown chet tren buoc vua tha`);
    check(dongCho >= 1, 'khong mot dong nao noi ro dieu kien cua o bi an');
  }

  // ── Bon so suc khoe trang ────────────────────────────────────────────
  check(pageErrors.length === 0,     'pageerror: ' + JSON.stringify(pageErrors));
  check(consoleErrors.length === 0,  'console error: ' + JSON.stringify(consoleErrors));
  check(failedRequests.length === 0, 'request hong: ' + JSON.stringify(failedRequests));
  check(serverErrors.length === 0,   '5xx: ' + JSON.stringify(serverErrors));

  if (loi.length) return {status: 'FAIL', loi, so_lieu: soLieu};
  return {status: 'PASS', so_lieu: soLieu};
}
