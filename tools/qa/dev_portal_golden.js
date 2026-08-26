// BON HANH TRINH VANG cua cong lap trinh vien, chay tren trinh duyet that.
//
//   playwright-cli -s=devui open "http://127.0.0.1:8101/"
//   playwright-cli -s=devui --raw run-code --filename=tools/qa/dev_portal_golden.js
//
// ⛔ KHONG TIEU TIEN THAT. Duong goi duy nhat cham `/api/v1` o day dung mot
//    khoa CHE DO TEST (`ltt_tk_…`) va tuyen `GET /tools` — khong nha cung cap
//    nao duoc goi, khong but toan credit nao duoc ghi. Do la ly do buoc "goi
//    that" nam duoc trong mot phep kiem tu dong.
//
// ⚠️ Chay tren `tools/dev_portal_harness.py` (CSDL tam), KHONG chay tren
//    production: no TAO KHOA va THU HOI KHOA, va thu hoi thi khong dao nguoc.
async page => {
  const B = 'http://127.0.0.1:8101';
  const EMAIL = 'dev-ui-qa@example.com', PASS = 'a-good-password-12';
  const ra = [];
  const ok = (ten, dieu, chi) => ra.push(`${dieu ? 'PASS' : 'FAIL'}  ${ten}${chi ? '  — ' + chi : ''}`);

  // ⚠️ Dat MOT LAN o day, truoc moi cu bam. Dang ky no ngay truoc mot
  //    `page.click` la mot cuoc dua: `confirm()` co the bat len truoc khi
  //    trinh xu ly kip gan, va luc do cu bam treo cho toi khi het gio.
  // ⚠️ `playwright-cli` GIU trang giua cac luot chay, nen `page.on` cong don:
  //    chay lai lan thu ba thi ba trinh xu ly cung tranh nhau mot hop thoai va
  //    hai cai sau nem "Cannot accept dialog which is already handled".
  //    Go het truoc khi gan.
  page.removeAllListeners('dialog');
  page.on('dialog', d => d.accept());

  const bam = async (chon) => {
    if (!(await page.$(chon))) return false;
    await page.click(chon);
    await page.waitForLoadState('networkidle');
    return true;
  };
  const goi = (duong, khoa) => page.evaluate(async ([d, k]) => {
    const r = await fetch(d, { headers: { Authorization: 'Bearer ' + k } });
    return { st: r.status, rid: r.headers.get('x-request-id') || '', body: (await r.text()).slice(0, 200) };
  }, [duong, khoa]);

  // ── Dang nhap ─────────────────────────────────────────────────────────────
  // ⚠️ Phien trinh duyet cua `playwright-cli` GIU COOKIE giua cac luot chay,
  //    nen `/login` co the chuyen huong di ngay va o nhap khong bao gio xuat
  //    hien — mot `page.fill` treo 30 giay roi bao "khong tim thay o nhap",
  //    mot trieu chung khong lien quan gi toi nguyen nhan. Kiem truoc, dung
  //    doan.
  await page.setViewportSize({ width: 1600, height: 1000 });
  await page.goto(B + '/login', { waitUntil: 'networkidle' });
  if (await page.$('input[name=username]')) {
    await page.fill('input[name=username]', EMAIL);
    await page.fill('input[name=password]', PASS);
    await page.click('button[type=submit]');
    await page.waitForLoadState('networkidle');
  }
  await page.goto(B + '/developers', { waitUntil: 'networkidle' });
  if (page.url().includes('/login')) throw new Error('dang nhap that bai: ' + page.url());

  // ══════════════════════════════════════════════ GJ-A — TICH HOP DAU TIEN ══
  ra.push('== GJ-A  TICH HOP DAU TIEN ==');
  await page.goto(B + '/developers', { waitUntil: 'networkidle' });
  const dau = await page.evaluate(() => ({
    buoc: document.querySelectorAll('.dev-buoc>li, .dev-tat a').length,
    toiKhoa: !!document.querySelector('a[href="/developers/keys"]'),
    toiCam: !!document.querySelector('a[href^="/developers/cli"], a[href^="/developers/quickstart"]'),
  }));
  ok('trang dau chi duong toi khoa', dau.toiKhoa);
  ok('trang dau chi duong toi "cam vao cong cu"', dau.toiCam);

  // Tao project
  await page.goto(B + '/developers/projects', { waitUntil: 'networkidle' });
  await page.fill('#project-name', 'hanh-trinh-vang');
  await page.click('form[action="/developers/projects"] button[type=submit]');
  await page.waitForLoadState('networkidle');
  ok('tao duoc project', (await page.content()).includes('hanh-trinh-vang'));

  // Tao khoa CHE DO TEST — khong cham nha cung cap, khong cham so credit
  await page.goto(B + '/developers/keys', { waitUntil: 'networkidle' });
  await page.fill('#key-name', 'golden-journey');
  await page.check('input[name=mode][value=test]');
  await page.check('input[name=scopes][value="tools:read"]');
  await page.click('#tao-khoa button[type=submit]');
  await page.waitForLoadState('networkidle');

  const mat = await page.evaluate(() => {
    const el = document.querySelector('.dev-mat code');
    return el ? el.textContent.trim() : '';
  });
  ok('bi mat hien MOT LAN, trong .dev-mat', /^ltt_tk_/.test(mat), mat.slice(0, 14) + '…');
  const khoaCanhBao = await page.evaluate(() =>
    !!document.querySelector('.dev-mat[role=alert]'));
  ok('khoi bi mat mang role=alert', khoaCanhBao);

  // Cam vao cong cu: trang phai dua duoc mot lenh CHAY DUOC va mot cho de chep
  await page.goto(B + '/developers/cli', { waitUntil: 'networkidle' });
  const cam = await page.evaluate(() => ({
    goc: document.body.innerText.includes('/api/v1'),
    nutChep: document.querySelectorAll('.khoi-ma .nut-chep').length,
    // ⛔ Khong mot vi du nao duoc chua khoa that.
    loKhoa: /ltt_(sk|tk)_[A-Za-z0-9_-]{10}/.test(document.body.innerText),
  }));
  ok('trang cam noi base URL', cam.goc);
  ok('moi khoi ma co nut chep', cam.nutChep > 0, cam.nutChep + ' nut');
  ok('KHONG vi du nao chua khoa that', !cam.loKhoa);

  // Loi goi that dau tien — re nhat, khong tinh tien
  const r1 = await goi('/api/v1/tools', mat);
  ok('lot goi API dau tien tra 200', r1.st === 200, 'HTTP ' + r1.st);

  // ══════════════════════════════════════════════════ GJ-B — HIEU VE API ══
  ra.push('', '== GJ-B  HIEU VE API + BAO GIA ==');
  await page.goto(B + '/developers/tools', { waitUntil: 'networkidle' });
  const dm = await page.evaluate(() => ({
    so: document.querySelectorAll('.tool-the').length,
    coCheDo: /SYNC|ASYNC|STREAM/i.test(document.body.innerText),
  }));
  ok('danh muc liet ke cong cu', dm.so > 0, dm.so + ' the');
  ok('danh muc noi che do chay', dm.coCheDo);

  const duTruoc = await page.evaluate(async () => {
    const r = await fetch('/developers', { headers: { 'X-Requested-With': 'qa' } });
    const t = await r.text();
    const m = t.match(/chi-so-nhan">[^<]*<\/span>\s*<strong class="chi-so-gt">([\d.,]+)</);
    return m ? m[1] : '';
  });
  await page.goto(B + '/developers/pricing', { waitUntil: 'networkidle' });
  const gia = await page.evaluate(() => ({
    coSo: /\d/.test(document.body.innerText),
    noiLaMoPhong: /mô phỏng|simulat|không.*trừ|no credit|not charged/i.test(document.body.innerText),
  }));
  ok('trang gia dua ra mot con so', gia.coSo);
  ok('trang gia noi RO day la mo phong / khong tru credit', gia.noiLaMoPhong);
  const duSau = await page.evaluate(async () => {
    const r = await fetch('/developers');
    const t = await r.text();
    const m = t.match(/chi-so-nhan">[^<]*<\/span>\s*<strong class="chi-so-gt">([\d.,]+)</);
    return m ? m[1] : '';
  });
  ok('bao gia KHONG lam doi so du', duTruoc === duSau, `${duTruoc} -> ${duSau}`);

  // ═══════════════════════════════════════ GJ-C — VONG DOI CUA MOT KHOA ══
  ra.push('', '== GJ-C  VONG DOI KHOA ==');
  await page.goto(B + '/developers/keys', { waitUntil: 'networkidle' });
  const conHien = (await page.content()).includes(mat);
  ok('tai lai trang thi bi mat BIEN MAT', !conHien);

  const maCong = mat.split('_')[2];
  ok('nua cong khai cua khoa van con', (await page.content()).includes(maCong));

  // Xoay: chuoi cu phai chet ngay
  const hang = await page.evaluate((id) => {
    const tr = [...document.querySelectorAll('.dev-bang tbody tr')]
      .find(r => r.textContent.includes(id));
    return tr ? tr.querySelector('form[action*="/rotate"]')?.getAttribute('action') || '' : '';
  }, maCong);
  ok('tim thay nut doi bi mat cua dung khoa do', !!hang, hang);

  // ⚠️ `form.submit()` ben trong `page.evaluate` lam DIEU HUONG, va dieu huong
  //    huy ngu canh dang chay cua chinh loi goi do — Playwright nem "Execution
  //    context was destroyed". Bam nut that roi doi tai trang.
  ok('bam duoc nut doi bi mat',
     await bam(`form[action="${hang}"] button[type=submit]`));
  const matMoi = await page.evaluate(() => {
    const el = document.querySelector('.dev-mat code');
    return el ? el.textContent.trim() : '';
  });
  ok('doi bi mat cho ra chuoi MOI', /^ltt_tk_/.test(matMoi) && matMoi !== mat);

  const cu = await goi('/api/v1/tools', mat);
  ok('chuoi CU bi tu choi sau khi doi', cu.st === 401, 'HTTP ' + cu.st);
  const moi = await goi('/api/v1/tools', matMoi);
  ok('chuoi MOI dung duoc', moi.st === 200, 'HTTP ' + moi.st);

  // ⚠️ `rotate` DOI LUON `key_id` cong khai, khong chi doi chuoi bi mat
  //    (`platform_core/public_api/keys.py::rotate` — doi tai cho de pham vi,
  //    ten va lich su o nguyen mot hang). Nen tim hang bang ma CU sau khi doi
  //    la tim mot thu khong con ton tai. Do la mot hanh vi san pham that va
  //    dang biet: mot ticket ho tro trich ma khoa CU se khong con khop.
  const maMoi = matMoi.split('_')[2];
  ok('doi bi mat cung doi luon ma khoa cong khai', maMoi !== maCong,
     `${maCong.slice(0, 10)}… -> ${maMoi.slice(0, 10)}…`);
  ok('ma khoa MOI hien ngay tren trang', (await page.content()).includes(maMoi));

  // Thu hoi: khong dao nguoc
  const hangTh = await page.evaluate((id) => {
    const tr = [...document.querySelectorAll('.dev-bang tbody tr')]
      .find(r => r.textContent.includes(id));
    return tr ? tr.querySelector('form[action*="/revoke"]')?.getAttribute('action') || '' : '';
  }, maMoi);
  ok('tim thay nut thu hoi cua dung khoa do', !!hangTh, hangTh || '(khong thay)');
  ok('bam duoc nut thu hoi',
     await bam(`form[action="${hangTh}"] button[type=submit]`));
  const sauTh = await goi('/api/v1/tools', matMoi);
  ok('khoa da thu hoi bi tu choi', sauTh.st === 401, 'HTTP ' + sauTh.st);
  const trangThai = await page.evaluate((id) => {
    const tr = [...document.querySelectorAll('.dev-bang tbody tr')]
      .find(r => r.textContent.includes(id));
    const el = tr && tr.querySelector('.dev-tt');
    return el ? el.textContent.trim() + '|' + el.className : '';
  }, maMoi);
  ok('bang noi khoa da thu hoi, bang CHU chu khong chi bang mau',
     trangThai.includes('revoked'), trangThai);

  // ══════════════════════════════════════════════ GJ-D — GO LOI TICH HOP ══
  ra.push('', '== GJ-D  GO LOI ==');
  await page.goto(B + '/developers/logs', { waitUntil: 'networkidle' });
  const nk = await page.evaluate(() => {
    const hang = [...document.querySelectorAll('.dev-bang tbody tr')];
    const dau = hang[0];
    return {
      so: hang.length,
      coTt: !!document.querySelector('.dev-tt'),
      // Mau NGU NGHIA: 2xx phai khac 4xx/5xx.
      lop: [...document.querySelectorAll('.dev-tt')].map(e => e.className.replace('dev-tt ', '')),
      coMaLoi: !!document.querySelector('.dev-ma-loi'),
      coRid: dau ? !!dau.querySelector('a[href^="/developers/logs/"]') : false,
      // ⛔ Khong duoc lo body cua request/response — chinh sach chi luu bo xuong.
      coBody: /"prompt"|"messages"|request_body|response_body/i.test(document.body.innerText),
      dai: dau ? [...dau.children].map(c => c.textContent.trim().slice(0, 22)) : [],
    };
  });
  ok('nhat ky co dong', nk.so > 0, nk.so + ' dong');
  ok('trang thai la mot nhan co mau ngu nghia', nk.coTt);
  ok('2xx va 4xx/5xx KHAC lop mau', new Set(nk.lop).size > 1, [...new Set(nk.lop)].join(','));
  ok('ma loi hien ra khi co', nk.coMaLoi);
  ok('moi dong mo duoc chi tiet theo request_id', nk.coRid);
  ok('KHONG lo noi dung request/response', !nk.coBody);
  ra.push('  cot dong dau: ' + JSON.stringify(nk.dai));

  // Loc theo request_id — duong mot nguoi dan tu ticket ho tro se di
  const rid = await page.evaluate(() => {
    const a = document.querySelector('.dev-bang tbody a[href^="/developers/logs/"]');
    return a ? a.getAttribute('href').split('/').pop() : '';
  });
  await page.goto(B + '/developers/logs?request_id=' + rid, { waitUntil: 'networkidle' });
  const locXong = await page.evaluate(() => document.querySelectorAll('.dev-bang tbody tr').length);
  ok('loc theo request_id thu hep duoc', locXong >= 1 && locXong < nk.so, `${nk.so} -> ${locXong}`);

  await page.goto(B + '/developers/logs/' + rid, { waitUntil: 'networkidle' });
  const ct = await page.evaluate(() => ({
    st: !!document.body.innerText.match(/\b(200|4\d\d|5\d\d)\b/),
    treo: /ms\b/.test(document.body.innerText),
    coBody: /"prompt"|"messages"|request_body|response_body/i.test(document.body.innerText),
  }));
  ok('trang chi tiet co trang thai', ct.st);
  ok('trang chi tiet co do tre', ct.treo);
  ok('trang chi tiet KHONG lo body', !ct.coBody);

  // ── Trang thai rong: co tra loi duoc BUOC TIEP khong? ────────────────────
  await page.goto(B + '/developers/logs?request_id=khong-ton-tai-dau', { waitUntil: 'networkidle' });
  const rong = await page.evaluate(() => {
    const e = document.querySelector('.dev-trong');
    return e ? { co: true, nut: !!e.querySelector('a.btn, .btn'), chu: e.innerText.length } : { co: false };
  });
  ok('trang thai rong dung khuon .dev-trong', rong.co);
  ok('trang thai rong co BUOC TIEP', !!rong.nut);

  const hong = ra.filter(l => l.startsWith('FAIL')).length;
  ra.push('', `TONG: ${ra.filter(l => l.startsWith('PASS')).length} PASS, ${hong} FAIL`);
  return ra.join('\n');
}
