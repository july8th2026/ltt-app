// UI-6 nghiem thu (che do A — may chu CO LAP cong 8205).
//
// ⛔ Khong doc ma roi tuyen bo da sua. Ca hai menh de cot loi cua lan nay chi
//    do duoc tren trinh duyet that:
//      * tab "Dữ liệu vào" phai VE ra cay du lieu THAT (khong con la
//        `.inspector-dat-cho` — jsdom o `ChonDuLieu.test.tsx` da chung minh
//        hanh vi component, nhung KHONG chung minh no thay the dung cho o
//        thi that trong `StepInspector` da build).
//      * bam mot cong cua buoc TRUOC phai CHEN dung chuoi vao O THAM SO that
//        (autosave -> doc lai tu may chu), khong chi goi mot ham mock.
//
// Chay:
//   playwright-cli -s=ui6 run-code --filename=tests/browser/agent_ui_v2_ui6_nghiem_thu.js
async page => {
  const base = 'http://127.0.0.1:8205';
  const EMAIL = 'agent-ui6@example.com';
  const MATKHAU = 'Browser-ui6-2026';

  const pageErrors = [], consoleErrors = [], failedRequests = [], serverErrors = [];
  page.on('pageerror',     e => pageErrors.push(e.message));
  page.on('console',       m => { if (m.type() === 'error') consoleErrors.push(m.text()); });
  page.on('requestfailed', r => failedRequests.push({url: r.url(), err: r.failure()?.errorText}));
  page.on('response',      r => { if (r.status() >= 500) serverErrors.push({url: r.url(), status: r.status()}); });

  const loi = [];
  const check = (dk, msg) => { if (!dk) loi.push(msg); };
  // ⭐ `chan()`: mot dieu kien MA BUOC SAU phu thuoc. Khong dat duoc thi dung
  //   NGAY va tra FAIL co ly do, thay vi de mot TimeoutError vo nghia o buoc xa.
  const chan = (dk, msg) => { if (!dk) { loi.push('CHAN: ' + msg); return false; } return true; };
  const soLieu = {};

  // ⭐ Boc CA THAN trong try/catch: mot loi nem giua chung (vd mot `waitFor`
  //   qua han) van tra ve `so_lieu` da gom duoc toi luc do, thay vi mot
  //   TimeoutError tho khong noi duoc buoc nao truoc no da lam.
  try {
  // ── Dang nhap (CO DIEU KIEN — cookie phien truoc co the con song) ────────
  await page.goto(base + '/login');
  if (await page.locator('#login-username').count()) {
    await page.locator('#login-username').fill(EMAIL);
    await page.locator('#login-password').fill(MATKHAU);
    await Promise.all([
      page.waitForLoadState('networkidle'),
      page.locator('form button[type=submit]').click(),
    ]);
  }
  if (!chan(!page.url().includes('/login'), 'dang nhap that bai')) {
    return {status: 'FAIL', loi, so_lieu: soLieu};
  }

  // ── Dung mot workflow HAI buoc NOI DAY (n1 -> n2), de n2 co to tien ──────
  //
  // ⭐ Loai buoc lay TU MAY CHU (`/agent/api/v3/palette`), ⛔ khong go cung
  //    mot `type`: catalog doi thi kich ban bao "khong tim thay buoc" thay vi
  //    "buoc nay hong" — dung bai hoc da ghi trong `agent_ui_v2_ui5_nghiem_thu.js`.
  await page.goto(base + '/agent/canvas');
  await page.locator('#agent-canvas-root').waitFor();
  await page.waitForFunction(async () => {
    const r = await fetch('/agent/api/v3/workflows',
      {credentials: 'same-origin', headers: {Accept: 'application/json'}});
    const j = await r.json();
    return Array.isArray(j.items) && j.items.length > 0;
  }, null, {timeout: 20000});

  // ⚠️ `tham_so.required` KHONG bat het luat: `core.delay` khong co truong
  //    `required` nao ma van doi "it nhat mot trong duration_s/until"
  //    (mot rang buoc rieng trong `bien_dich`, khong ra JSON Schema). Do
  //    duoc bang cach dau — chon lieu qua LOC schema roi nem thang vao canvas
  //    dinh ngay mot doc khong bien dich duoc. ⇒ PROBE THAT bang chinh cua
  //    goi-y (da co san, ⛔ khong mo cua moi): thu tung cap cho toi khi
  //    `loi === null`, dung nhu cong publish se lam.
  const chuan = await page.evaluate(async () => {
    const csrf = document.querySelector('#agent-canvas-root').dataset.csrfToken;
    const lay = async u => await (await fetch(u, {credentials: 'same-origin',
      headers: {Accept: 'application/json'}})).json();
    const pal = await lay('/agent/api/v3/palette');
    const nut = pal.nhom.flatMap(n => n.nut);
    const coCongRa = nut.filter(n => n.kind !== 'trigger' && (n.cong_ra || []).length > 0);
    const coThamSoChu = nut.filter(n => n.kind !== 'trigger' && (n.cong_vao || []).length > 0
      && Object.values((n.tham_so || {}).properties || {})
        .some(p => p.type === 'string' && !Array.isArray(p.enum)));
    const slug = t => t.startsWith('app.') ? t.slice(4) : t;
    const docThu = (nguon, dich) => ({
      version: 3, goal: '', budget_max_credit: 0, active_page_id: 'p1',
      pages: [{id: 'p1', name: 'Page 1', viewport: {x: 0, y: 0, zoom: 1},
               frames: [], notes: [], comments: [],
               nodes: [{id: 'n1', type: 'tool', position: {x: 80, y: 80},
                        data: {tool: slug(nguon), params: {}}},
                       {id: 'n2', type: 'tool', position: {x: 420, y: 80},
                        data: {tool: slug(dich), params: {}}}],
               edges: [{id: 'e1', source_node: 'n1', target_node: 'n2',
                        source_port: 'out', target_port: 'in', kind: 'DATA'}]}],
    });
    const ds = await lay('/agent/api/v3/workflows');
    const id = ds.items[0].id;
    for (const n of coCongRa.slice(0, 8)) {
      for (const d of coThamSoChu.slice(0, 8)) {
        if (n.type === d.type) continue;
        const r = await fetch(`/agent/api/v3/workflows/${id}/bieu-thuc/goi-y`, {
          method: 'POST', credentials: 'same-origin',
          headers: {'Content-Type': 'application/json', 'X-CSRF-Token': csrf},
          body: JSON.stringify({node_id: 'n2', document: docThu(n.type, d.type), csrf_token: csrf})});
        const j = await r.json();
        if (j.loi === null && (j.muc || []).some(m => m.loai === 'cong'))
          return {buocNguon: n, buocDich: d};
      }
    }
    return {buocNguon: null, buocDich: null};
  });
  soLieu.chuan = {buocNguon: chuan.buocNguon?.type, buocDich: chuan.buocDich?.type};
  if (!chan(chuan.buocNguon && chuan.buocDich,
            'khong tim duoc cap buoc nguon/dich nao BIEN DICH DUOC trong palette')) {
    return {status: 'FAIL', loi, so_lieu: soLieu};
  }

  const slug = t => t.startsWith('app.') ? t.slice(4) : t;
  const datDoThi = async (nguon, dich) => {
    // ⚠️ Phien Playwright DUNG LAI GIUA cac lan `run-code` (⛔ khong dong tab),
    //    va app React tu AUTOSAVE 800ms sau khi nguoi (kich ban) go — mot lan
    //    chay TRUOC bi loi giua chung co the con mot autosave dang bay, va no
    //    GHI DE ban PUT "sach" cua lan nay bang mot khoa `If-Match` da LECH.
    //    ⇒ PUT phai tu KIEM TRA + THU LAI, ⛔ khong ban chi mot lan roi tin.
    const ket = await page.evaluate(async ({nguon, dich}) => {
      const csrf = document.querySelector('#agent-canvas-root').dataset.csrfToken;
      const lay = async u => await (await fetch(u, {credentials: 'same-origin',
        headers: {Accept: 'application/json'}})).json();
      const ds = await lay('/agent/api/v3/workflows');
      const id = ds.items[0].id;
      const doc = {
        version: 3, goal: '', budget_max_credit: 0, active_page_id: 'p1',
        pages: [{id: 'p1', name: 'Page 1', viewport: {x: 0, y: 0, zoom: 1},
                 frames: [], notes: [], comments: [],
                 nodes: [
                   {id: 'n1', type: 'tool', position: {x: 80, y: 80},
                    data: {tool: nguon, params: {}}},
                   {id: 'n2', type: 'tool', position: {x: 420, y: 80},
                    data: {tool: dich, params: {}}},
                 ],
                 edges: [{id: 'e1', source_node: 'n1', target_node: 'n2',
                          source_port: 'out', target_port: 'in', kind: 'DATA'}]}],
      };
      let than = '';
      for (let lan = 0; lan < 5; lan++) {
        const cur = await lay('/agent/api/v3/workflows/' + id);
        const r = await fetch('/agent/api/v3/workflows/' + id, {method: 'PUT',
          credentials: 'same-origin',
          headers: {'Content-Type': 'application/json', 'X-CSRF-Token': csrf,
                    'If-Match': '"' + cur.revision + '"'},
          body: JSON.stringify({csrf_token: csrf, document: doc})});
        if (r.ok) return {ok: true, id};
        than = await r.text();
        await new Promise(res => setTimeout(res, 300));
      }
      return {ok: false, id, than};
    }, {nguon: slug(nguon), dich: slug(dich)});
    if (!chan(ket.ok, `khong ghi duoc do thi thu (revision lech nhieu lan): ${ket.than}`)) {
      return false;
    }
    await page.goto(base + '/agent/canvas');
    await page.locator('#agent-canvas-root').waitFor();
    await page.locator('.react-flow__node[data-id="n2"]').waitFor({timeout: 20000});
    return true;
  };

  if (!await datDoThi(chuan.buocNguon.type, chuan.buocDich.type)) {
    return {status: 'FAIL', loi, so_lieu: soLieu};
  }

  // ── Chon buoc n2 (buoc DICH, co to tien n1) va mo tab "Dữ liệu vào" ─────
  // ⚠️ `[data-id=]`, ⛔ khong `nth()`: thu tu DOM cua React Flow khong bao dam
  //    trung thu tu `nodes` trong tai lieu.
  await page.locator('.react-flow__node[data-id="n2"]').click();
  await page.locator('.inspector-tabs').waitFor({timeout: 15000});
  await page.getByRole('button', {name: 'Dữ liệu vào'}).click();
  // ⚠️ `goiY` toi CHAM: `useExpressionSuggest` doi mot debounce 200ms roi moi
  //    goi may chu. `.count()` KHONG tu doi (⛔ khong nhu `.evaluate()`/`.click()`
  //    da tu doi phan tu xuat hien) — thieu wait nay se dem TRUOC khi du lieu
  //    ve, cho ket qua 0 gia (do duoc 28/09, xem bao cao lan UI-6).
  await page.locator('.chon-du-lieu-buoc, .chon-du-lieu-trong').first()
    .waitFor({timeout: 10000});

  // ── Phep do 1: tab KHONG con la dat cho — ve CAY THAT ────────────────────
  const datChoConLai = await page.locator('.inspector-dat-cho').count();
  soLieu.datChoConLai = datChoConLai;
  check(datChoConLai === 0, `tab "Dữ liệu vào" van la dat cho (${datChoConLai})`);

  const soNhomBuocTruoc = await page.locator('.chon-du-lieu-buoc').count();
  soLieu.soNhomBuocTruoc = soNhomBuocTruoc;
  check(soNhomBuocTruoc >= 1, `khong co nhom "buoc truoc" nao (${soNhomBuocTruoc})`);

  const conLaChon = await page.locator('.chon-du-lieu-buoc button').count();
  soLieu.soLaChonDuocN1 = conLaChon;
  check(conLaChon >= 1, 'buoc n1 khong lo mot la nao de chon');

  // ── Phep do "buoc dau tien": TRUOC khi chen — do thi con SACH ───────────
  //
  // ⚠️ Thu tu co y: phep do CHEN duoi day chen mot bieu thuc vao `core.stop.
  //    trang_thai`, mot tham so CHI nhan literal `SUCCEEDED`/`FAILED` (rang
  //    buoc rieng cua `bien_dich`, khong phai enum JSON Schema — xem ghi chu
  //    o tren). Sau khi chen, CA DO THI het bien dich duoc, va goi-y cua MOI
  //    node (ke ca n1) deu tra ve `loi` thay vi mot cay hay mot cau "trong".
  //    Kiem tra n1 SAU do se do dung mot do thi da HONG boi chinh kich ban,
  //    khong phai mot phep do that ve n1.
  await page.locator('.react-flow__node[data-id="n1"]').click();
  await page.locator('.inspector-tabs').waitFor({timeout: 10000});
  await page.getByRole('button', {name: 'Dữ liệu vào'}).click();
  await page.locator('.chon-du-lieu-buoc, .chon-du-lieu-trong').first()
    .waitFor({timeout: 10000});
  const nhomRongTrenBuocDau = await page.locator('.chon-du-lieu-buoc').count();
  const coCauNoiRo = await page.locator('.chon-du-lieu-trong').count();
  soLieu.buocDauTien = {nhomBuocTruoc: nhomRongTrenBuocDau, coCauNoiRo};
  check(nhomRongTrenBuocDau === 0,
        `buoc dau tien (khong to tien) van hien ${nhomRongTrenBuocDau} nhom buoc truoc`);
  check(coCauNoiRo === 1, 'buoc dau tien khong noi ro "chua co gi de chon"');

  // Quay lai n2 de tiep tuc phep do chen.
  await page.locator('.react-flow__node[data-id="n2"]').click();
  await page.locator('.inspector-tabs').waitFor({timeout: 10000});
  await page.getByRole('button', {name: 'Dữ liệu vào'}).click();
  await page.locator('.chon-du-lieu-buoc, .chon-du-lieu-trong').first()
    .waitFor({timeout: 10000});

  // ── Phep do 2: chon O DICH, bam mot la ⇒ chen dung chuoi ─────────────────
  const oDich = page.locator('label.chon-du-lieu-dich select');
  await oDich.waitFor({timeout: 10000});
  const tenODich = await oDich.evaluate(el => el.value);
  soLieu.tenODich = tenODich;
  check(Boolean(tenODich), 'khong co o dich nao duoc chon san');

  const laDauTien = page.locator('.chon-du-lieu-buoc button').first();
  const duongDuocChen = await laDauTien.evaluate(el => el.title);
  soLieu.duongDuocChen = duongDuocChen;
  await laDauTien.click();

  // Quay lai tab Cấu hình, doc GIA TRI THAT cua o dich tu DOM.
  // ⚠️ `tenODich` la ten tham so (vd "prompt") — ⛔ khong `CSS.escape`: do la
  //    API cua TRINH DUYET, kich ban ngoai nay chay trong Node.
  await page.getByRole('button', {name: 'Cấu hình'}).click();
  const giaODich = await page.locator('#' + tenODich).inputValue();
  soLieu.giaODichSauKhiChen = giaODich;
  check(giaODich.includes(`{{ ${duongDuocChen} }}`),
        `o dich khong chua bieu thuc vua chen: ${JSON.stringify(giaODich)}`);

  // ── Phep do 3: doc lai TU MAY CHU (autosave) — khong chi tin DOM ────────
  await page.waitForTimeout(2500);
  const luuTru = await page.evaluate(async () => {
    const lay = async u => await (await fetch(u, {credentials: 'same-origin',
      headers: {Accept: 'application/json'}})).json();
    const ds = await lay('/agent/api/v3/workflows');
    const wf = await lay('/agent/api/v3/workflows/' + ds.items[0].id);
    const n2 = wf.document.pages[0].nodes.find(n => n.id === 'n2');
    return (n2 && n2.data && n2.data.params) || {};
  });
  soLieu.luuTruSauKhiChen = luuTru;
  check(Object.values(luuTru).some(v => typeof v === 'string' && v.includes(duongDuocChen)),
        `may chu KHONG luu bieu thuc da chen: ${JSON.stringify(luuTru)}`);

  // ── Bon so suc khoe trang ────────────────────────────────────────────────
  check(pageErrors.length === 0,     'pageerror: ' + JSON.stringify(pageErrors));
  check(consoleErrors.length === 0,  'console error: ' + JSON.stringify(consoleErrors));
  check(failedRequests.length === 0, 'request hong: ' + JSON.stringify(failedRequests));
  check(serverErrors.length === 0,   '5xx: ' + JSON.stringify(serverErrors));

  if (loi.length) return {status: 'FAIL', loi, so_lieu: soLieu};
  return {status: 'PASS', so_lieu: soLieu};
  } catch (e) {
    return {status: 'FAIL', loi: [...loi, 'EXCEPTION: ' + (e && e.message)], so_lieu: soLieu};
  }
}
